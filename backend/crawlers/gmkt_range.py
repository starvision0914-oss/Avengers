"""지마켓 광고비 — 기간(날짜범위) 재수집. 엑셀 1회로 범위 전체 수집.
실행: python -u -c "import crawlers.gmkt_range" YYYY-MM-DD YYYY-MM-DD [로그인계정...]
안전: 파싱 행이 있을 때만 (행에 등장한 use_date)들을 트랜잭션 내 삭제→삽입(멱등, 데이터손실 방지).
로그: /tmp/gmkt_range.log
"""
import os, re, time, glob, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from datetime import datetime
from collections import defaultdict
import pytz
from django.db import transaction
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver, stop_display
from apps.cpc.models import CrawlerAccount, GmarketCostHistory
from crawlers.gmarket_cost_crawler import _esm_login

KST = pytz.timezone('Asia/Seoul')
DL = '/tmp/gmkt_range_xl'
AD = ('CPC', 'AI매출업', '서버비용')
LOG = open('/tmp/gmkt_range.log', 'a')

args = sys.argv[1:]
if len(args) < 2 or not all(re.match(r'\d{4}-\d{2}-\d{2}', a) for a in args[:2]):
    print('인자: START_DATE END_DATE [logins...]'); sys.exit(1)
START = datetime.strptime(args[0], '%Y-%m-%d').date()
END = datetime.strptime(args[1], '%Y-%m-%d').date()
LOGINS = args[2:]


def p(*a):
    m = ' '.join(str(x) for x in a); LOG.write(m+'\n'); LOG.flush()
    try: print(m, flush=True)
    except Exception: pass

def drain(d):
    try:
        a=d.switch_to.alert; t=a.text; a.accept(); return t
    except Exception: return None

def wait_overlay(d):
    for _ in range(12):
        ov=d.find_elements(By.CSS_SELECTOR,'.layer_overlay')
        if not ov or all(not o.is_displayed() for o in ov): return
        time.sleep(0.5)

def jc(d, xp):
    els=d.find_elements(By.XPATH, xp)
    if els: d.execute_script('arguments[0].click();', els[0]); return True
    return False

def cls(cm):
    if 'AI매출업' in cm: return 'AI매출업'
    if '서버' in cm: return '서버비용'
    if 'CPC' in cm or 'cpc' in cm: return 'CPC'
    return '기타'

def _grid_fallback(d):
    """엑셀 실패 시 화면 그리드에서 범위내 행 수집(페이지 순회)."""
    seen_keys=set(); rows=[]; page=1
    while page<=30:
        time.sleep(1.0)
        trs=d.find_elements(By.CSS_SELECTOR, '#grid_sortingData tr')
        new=0
        for tr in trs:
            tds=[td.text.strip() for td in tr.find_elements(By.TAG_NAME,'td')]
            if len(tds)<12 or not re.match(r'20\d\d-\d\d-\d\d', tds[1] or ''):
                continue
            try: ta=KST.localize(datetime.strptime(tds[1][:19] if len(tds[1])>=19 else tds[1][:10],
                     '%Y-%m-%d %H:%M:%S' if len(tds[1])>=19 else '%Y-%m-%d')); dd=ta.date()
            except Exception: continue
            if dd<START or dd>END: continue
            key=(tds[1],tds[3],tds[11])
            if key in seen_keys: continue
            seen_keys.add(key); new+=1
            amt=int(re.sub(r'[^\d-]','',tds[11]) or 0)
            rows.append((dd,ta,cls(tds[3]),tds[3][:255],amt,''))
        # 다음 페이지(숫자버튼) — 새 행 없으면 종료
        page+=1
        nxt=[e for e in d.find_elements(By.XPATH, f"//a[normalize-space(text())='{page}'] | //button[normalize-space(text())='{page}']") if e.is_displayed()]
        if not nxt or new==0: break
        d.execute_script('arguments[0].click();', nxt[0]); wait_overlay(d)
    return rows

def dl_range(d, sid):
    for f in glob.glob(DL+'/*'):
        try: os.remove(f)
        except Exception: pass
    try: Select(d.find_element(By.ID,'sellerId')).select_by_value(sid)
    except Exception: pass
    time.sleep(0.3)
    for fid,val in [('searchSDT',START.isoformat()),('searchEDT',END.isoformat())]:
        d.execute_script("var e=document.getElementById('%s');if(e){e.value='%s';e.dispatchEvent(new Event('change'));}"%(fid,val))
    wait_overlay(d)
    jc(d,'//*[@id="btnSearch"]/img') or jc(d,'//*[@id="btnSearch"]')
    drain(d); time.sleep(1.8); wait_overlay(d)
    jc(d,'//*[@id="excelDown"]'); drain(d)
    for _ in range(24):
        files=[f for f in glob.glob(DL+'/*') if not f.endswith('.crdownload')]
        if files: break
        time.sleep(0.5)
    files=[f for f in glob.glob(DL+'/*') if not f.endswith('.crdownload')]
    if not files:
        # 엑셀 실패(옥션 엑셀 고장) → 그리드 폴백(날짜범위 필터 + 페이지순회)
        return _grid_fallback(d)
    import xlrd
    try: sh=xlrd.open_workbook(files[-1]).sheet_by_index(0)
    except Exception: return []
    hdr=[str(x) for x in sh.row_values(0)]; ci={h:i for i,h in enumerate(hdr)}
    if '판매예치금 발생액' not in ci: return []
    rows=[]
    for r in range(1, sh.nrows):
        row=sh.row_values(r)
        cm=str(row[ci.get('거래내역',5)])
        amt=int(re.sub(r'[^\d-]','',str(row[ci['판매예치금 발생액']])) or 0)
        dts=str(row[ci.get('거래일시',1)]).strip()
        try: ta=KST.localize(datetime.strptime(dts[:19],'%Y-%m-%d %H:%M:%S')); dd=ta.date()
        except Exception: continue
        if dd<START or dd>END: continue
        rows.append((dd,ta,cls(cm),cm[:255],amt,str(row[ci.get('관련번호',6)])[:50]))
    return rows

def save_range(sid, market, rows):
    if not rows:
        return 0,0,0   # 행 없으면 아무것도 삭제 안 함(안전)
    dates=sorted(set(r[0] for r in rows))
    with transaction.atomic():
        GmarketCostHistory.objects.filter(seller_id=sid, market=market, use_date__in=dates).delete()
        objs=[]; seq=defaultdict(int)
        for (dd,ta,tc,cm,amt,rn) in rows:
            s=seq[dd]; seq[dd]+=1
            objs.append(GmarketCostHistory(seller_id=sid,market=market,use_date=dd,traded_at=ta,
                  seq=s, use_type='차감' if amt<0 else '적립', transaction_type=tc,comment=cm,amount=amt,related_no=rn))
        GmarketCostHistory.objects.bulk_create(objs, batch_size=1000)
    ad=[r for r in rows if r[2] in AD]
    return abs(sum(r[4] for r in ad)), len(ad), len(dates)

def collect(login_id):
    acc=CrawlerAccount.objects.get(platform='gmarket', login_id=login_id)
    prof='/tmp/gmkt_range_chrome_%d'%os.getpid()
    d=create_driver(download_dir=DL, kill_existing=False, user_data_dir=prof)
    try:
        d.execute_cdp_cmd('Page.setDownloadBehavior',{'behavior':'allow','downloadPath':DL})
        if not _esm_login(d, login_id, acc.password_enc):
            p('  [%s] 로그인 실패'%login_id); return False
        for market,url in [('gmarket','https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'),
                           ('auction','https://www.esmplus.com/Member/Settle/IacSellBalanceManagement')]:
            d.get(url); time.sleep(4); wait_overlay(d)
            try:
                sel=WebDriverWait(d,8).until(EC.presence_of_element_located((By.ID,'sellerId')))
                subs=[o.get_attribute('value') for o in sel.find_elements(By.TAG_NAME,'option') if o.get_attribute('value')]
            except Exception: subs=[login_id]
            for sid in subs:
                rows=dl_range(d, sid); amt,adn,nd=save_range(sid,market,rows)
                p('  [%s|%s] %s~%s 광고 %d건/%s원 (%d일)'%(sid,market,START,END,adn,format(amt,','),nd))
        return True
    finally:
        try: d.quit()
        except Exception: pass
        try:
            import shutil; shutil.rmtree(prof, ignore_errors=True)
        except Exception: pass

os.makedirs(DL, exist_ok=True)
logins=LOGINS or [a.login_id for a in CrawlerAccount.objects.filter(platform='gmarket',is_active=True)]
p('=== %s~%s 지마켓 광고비 기간수집: %d계정 ==='%(START,END,len(logins)))
ok=fail=0
for i,lid in enumerate(logins,1):
    p('[%d/%d] %s'%(i,len(logins),lid))
    try:
        if collect(lid): ok+=1
        else: fail+=1
    except Exception as e:
        fail+=1; p('  ! 오류: %s'%str(e)[:120])
    time.sleep(2)
try: stop_display()
except Exception: pass
p('=== 완료: 성공 %d / 실패 %d ==='%(ok,fail))
LOG.close()

"""지마켓 광고비 — 특정 날짜 재수집(gmkt_today의 날짜지정판).
실행: python -u -c "import crawlers.gmkt_date" YYYY-MM-DD 로그인계정...
멱등: (seller_id, market, use_date=대상일) 삭제 후 삽입.
로그: /tmp/gmkt_date.log
"""
import os, re, time, glob, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from datetime import date, datetime
import pytz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver, stop_display
from apps.cpc.models import CrawlerAccount, GmarketCostHistory
from crawlers.gmarket_cost_crawler import _esm_login

KST = pytz.timezone('Asia/Seoul')
DL = '/tmp/gmkt_date_xl'
AD = ('CPC', 'AI매출업', '서버비용')
LOG = open('/tmp/gmkt_date.log', 'a')

# 첫 인자=날짜
args = sys.argv[1:]
TARGET = datetime.strptime(args[0], '%Y-%m-%d').date() if args and re.match(r'\d{4}-\d{2}-\d{2}', args[0]) else None
if not TARGET:
    print('날짜 인자 필요: YYYY-MM-DD'); sys.exit(1)
LOGINS = args[1:]


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

def dl_date(d, sid):
    for f in glob.glob(DL+'/*'):
        try: os.remove(f)
        except Exception: pass
    try: Select(d.find_element(By.ID,'sellerId')).select_by_value(sid)
    except Exception: pass
    time.sleep(0.3)
    iso=TARGET.isoformat()
    for fid,val in [('searchSDT',iso),('searchEDT',iso)]:
        d.execute_script("var e=document.getElementById('%s');if(e){e.value='%s';e.dispatchEvent(new Event('change'));}"%(fid,val))
    wait_overlay(d)
    jc(d,'//*[@id="btnSearch"]/img') or jc(d,'//*[@id="btnSearch"]')
    drain(d); time.sleep(1.5); wait_overlay(d)
    jc(d,'//*[@id="excelDown"]'); drain(d)
    for _ in range(16):
        files=[f for f in glob.glob(DL+'/*') if not f.endswith('.crdownload')]
        if files: break
        time.sleep(0.5)
    files=[f for f in glob.glob(DL+'/*') if not f.endswith('.crdownload')]
    if not files: return []
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
        if dd!=TARGET: continue
        rows.append((dd,ta,cls(cm),cm[:255],amt,str(row[ci.get('관련번호',6)])[:50]))
    return rows

def save(sid, market, rows):
    GmarketCostHistory.objects.filter(seller_id=sid, market=market, use_date=TARGET).delete()
    objs=[]; seq={}
    for (dd,ta,tc,cm,amt,rn) in rows:
        s=seq.get(dd,0); seq[dd]=s+1
        objs.append(GmarketCostHistory(seller_id=sid,market=market,use_date=dd,traded_at=ta,
              seq=s, use_type='차감' if amt<0 else '적립', transaction_type=tc,comment=cm,amount=amt,related_no=rn))
    if objs: GmarketCostHistory.objects.bulk_create(objs, batch_size=1000)
    ad=[r for r in rows if r[2] in AD]
    return abs(sum(r[4] for r in ad)), len(ad)

def collect(login_id):
    acc=CrawlerAccount.objects.get(platform='gmarket', login_id=login_id)
    prof='/tmp/gmkt_date_chrome_%d'%os.getpid()
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
                rows=dl_date(d, sid); amt,adn=save(sid,market,rows)
                p('  [%s|%s] %s 광고 %d건 / %s원'%(sid,market,TARGET,adn,format(amt,',')))
        return True
    finally:
        try: d.quit()
        except Exception: pass
        try:
            import shutil; shutil.rmtree(prof, ignore_errors=True)
        except Exception: pass

os.makedirs(DL, exist_ok=True)
logins=LOGINS or [a.login_id for a in CrawlerAccount.objects.filter(platform='gmarket',is_active=True)]
p('=== %s 지마켓 광고비 재수집: %d계정 ==='%(TARGET, len(logins)))
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

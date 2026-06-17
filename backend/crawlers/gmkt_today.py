"""지마켓 '오늘' 광고비만 빠르게 수집 — 엑셀 + '판매예치금 발생액'.
- 범위: 오늘 하루(KST), gmarket만, 복수아이디 순회
- 멱등: (seller_id, market='gmarket', use_date=오늘) 삭제 후 삽입 → 다른날짜 데이터 보존
실행: python -u -c "import crawlers.gmkt_today" [로그인계정...]
로그: /tmp/gmkt_today.log
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
DL = '/tmp/gmkt_today_xl'
AD = ('CPC', 'AI매출업', '서버비용')
TODAY = datetime.now(KST).date()
LOG = open('/tmp/gmkt_today.log', 'a')


def p(*a):
    m = ' '.join(str(x) for x in a)
    LOG.write(m + '\n'); LOG.flush()
    try: print(m, flush=True)
    except Exception: pass


def drain(d):
    try:
        a = d.switch_to.alert; t = a.text; a.accept(); return t
    except Exception:
        return None


def wait_overlay(d):
    for _ in range(12):
        ov = d.find_elements(By.CSS_SELECTOR, '.layer_overlay')
        if not ov or all(not o.is_displayed() for o in ov):
            return
        time.sleep(0.5)


def jc(d, xp):
    els = d.find_elements(By.XPATH, xp)
    if els:
        d.execute_script('arguments[0].click();', els[0]); return True
    return False


def cls(cm):
    if 'AI매출업' in cm: return 'AI매출업'
    if '서버' in cm: return '서버비용'
    if 'CPC' in cm or 'cpc' in cm: return 'CPC'
    return '기타'


def dl_today(d, sid):
    for f in glob.glob(DL + '/*'):
        os.remove(f)
    try:
        Select(d.find_element(By.ID, 'sellerId')).select_by_value(sid)
    except Exception:
        pass
    time.sleep(0.3)
    iso = TODAY.isoformat()
    for fid, val in [('searchSDT', iso), ('searchEDT', iso)]:
        d.execute_script("var e=document.getElementById('%s');if(e){e.value='%s';e.dispatchEvent(new Event('change'));}" % (fid, val))
    wait_overlay(d)
    jc(d, '//*[@id="btnSearch"]/img') or jc(d, '//*[@id="btnSearch"]')
    drain(d); time.sleep(1.5)
    wait_overlay(d)
    has = False
    for tr in d.find_elements(By.CSS_SELECTOR, '#grid_sortingData tr'):
        if re.search(r'20\d\d-\d\d-\d\d', tr.text or ''):
            has = True; break
    if not has:
        return []
    jc(d, '//*[@id="excelDown"]')
    drain(d)
    for _ in range(16):
        files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
        if files:
            break
        time.sleep(0.5)
    files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
    if not files:
        # 엑셀 실패(옥션 엑셀 고장) → 그리드 폴백(20행 미만일 때만 신뢰), 오늘분만
        grows = []
        for tr in d.find_elements(By.CSS_SELECTOR, '#grid_sortingData tr'):
            tds = [td.text.strip() for td in tr.find_elements(By.TAG_NAME, 'td')]
            if len(tds) < 12 or not re.match(r'20\d\d-\d\d-\d\d', tds[1] or ''):
                continue
            try:
                ta = KST.localize(datetime.strptime(tds[1][:10], '%Y-%m-%d')); dd = ta.date()
            except Exception:
                continue
            if dd != TODAY:
                continue
            amt = int(re.sub(r'[^\d-]', '', tds[11]) or 0)
            grows.append((dd, ta, cls(tds[3]), tds[3][:255], amt, ''))
        return grows if len(grows) < 20 else []
    import xlrd
    try:
        sh = xlrd.open_workbook(files[-1]).sheet_by_index(0)
    except Exception:
        return []
    hdr = [str(x) for x in sh.row_values(0)]
    ci = {h: i for i, h in enumerate(hdr)}
    if '판매예치금 발생액' not in ci:
        return []
    rows = []
    for r in range(1, sh.nrows):
        row = sh.row_values(r)
        cm = str(row[ci.get('거래내역', 5)])
        amt = int(re.sub(r'[^\d-]', '', str(row[ci['판매예치금 발생액']])) or 0)
        dts = str(row[ci.get('거래일시', 1)]).strip()
        try:
            ta = KST.localize(datetime.strptime(dts[:19], '%Y-%m-%d %H:%M:%S')); dd = ta.date()
        except Exception:
            continue
        if dd != TODAY:   # 혹시 다른날 섞이면 제외
            continue
        rows.append((dd, ta, cls(cm), cm[:255], amt, str(row[ci.get('관련번호', 6)])[:50]))
    return rows


def save(sid, market, rows):
    # 안전장치: 0행이면 기존 데이터 삭제하지 않음(읽기실패로 인한 데이터 소실 방지)
    if not rows:
        return 0, 0
    GmarketCostHistory.objects.filter(seller_id=sid, market=market, use_date=TODAY).delete()
    objs, seq = [], {}
    for dd, ta, tt, cm, amt, rel in rows:
        s = seq.get(dd, 0); seq[dd] = s + 1
        objs.append(GmarketCostHistory(seller_id=sid, market=market, use_date=dd, traded_at=ta,
                    seq=s, use_type='차감' if amt < 0 else '적립', transaction_type=tt,
                    comment=cm, amount=amt, related_no=rel))
    if objs:
        GmarketCostHistory.objects.bulk_create(objs, batch_size=1000)
    ad = [r for r in rows if r[2] in AD]
    return abs(sum(r[4] for r in ad)), len(ad)


def collect(login_id):
    acc = CrawlerAccount.objects.get(platform='gmarket', login_id=login_id)
    prof = '/tmp/gmkt_chrome_%d' % os.getpid()
    d = create_driver(download_dir=DL, kill_existing=False, user_data_dir=prof)
    try:
        d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
        if not _esm_login(d, login_id, acc.password_enc):
            p('  [%s] 로그인 실패' % login_id); return False
        # 지마켓+옥션 둘 다 같은 로그인으로 수집(동일 ESM)
        for market, url in [('gmarket', 'https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'),
                            ('auction', 'https://www.esmplus.com/Member/Settle/IacSellBalanceManagement')]:
            d.get(url); time.sleep(4); wait_overlay(d)
            try:
                sel = WebDriverWait(d, 8).until(EC.presence_of_element_located((By.ID, 'sellerId')))
                subs = [o.get_attribute('value') for o in sel.find_elements(By.TAG_NAME, 'option') if o.get_attribute('value')]
            except Exception:
                subs = [login_id]
            for sid in subs:
                rows = dl_today(d, sid)
                amt, adn = save(sid, market, rows)
                p('  [%s|%s] 오늘 광고 %d건 / %s원' % (sid, market, adn, format(amt, ',')))
        return True
    finally:
        try: d.quit()
        except Exception: pass
        try:
            import shutil; shutil.rmtree(prof, ignore_errors=True)
        except Exception: pass


os.makedirs(DL, exist_ok=True)
logins = sys.argv[1:] or [a.login_id for a in CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
                          if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]
p('=== 오늘(%s) 지마켓 광고비 수집: %d계정 ===' % (TODAY, len(logins)))
ok = fail = 0
for i, lid in enumerate(logins, 1):
    p('[%d/%d] %s' % (i, len(logins), lid))
    try:
        if collect(lid):
            ok += 1
        else:
            fail += 1
    except Exception as e:
        fail += 1; p('  ! 오류: %s' % str(e)[:120])
    time.sleep(2)
try:
    stop_display()
except Exception:
    pass
p('=== 완료: 성공 %d / 실패 %d ===' % (ok, fail))
LOG.close()

import os, re, time, glob, calendar
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from datetime import date, datetime
import pytz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException
from crawlers.browser import create_driver, stop_display
from apps.cpc.models import CrawlerAccount, GmarketCostHistory
from crawlers.gmarket_cost_crawler import _esm_login

KST = pytz.timezone('Asia/Seoul')
DL = '/tmp/gmkt_auc234'
AD = ('CPC', 'AI매출업', '서버비용')


def drain(d):
    try:
        a = d.switch_to.alert; t = a.text; a.accept(); return t
    except Exception:
        return None


def cls(cm):
    if 'AI매출업' in cm: return 'AI매출업'
    if '서버' in cm: return '서버비용'
    if 'CPC' in cm or 'cpc' in cm: return 'CPC'
    return '기타'


def wait_overlay(d):
    # layer_overlay 가 사라질 때까지 대기(최대 8초)
    for _ in range(16):
        ov = d.find_elements(By.CSS_SELECTOR, '.layer_overlay')
        if not ov or all(not o.is_displayed() for o in ov):
            return
        time.sleep(0.5)


def jsclick(d, xpath):
    els = d.find_elements(By.XPATH, xpath)
    if els:
        d.execute_script('arguments[0].click();', els[0]); return True
    return False


def dl_month(d, sid, sdt, edt):
    for f in glob.glob(DL + '/*'):
        os.remove(f)
    try:
        Select(d.find_element(By.ID, 'sellerId')).select_by_value(sid)
    except Exception:
        pass
    time.sleep(0.4)
    for fid, val in [('searchSDT', sdt.isoformat()), ('searchEDT', edt.isoformat())]:
        d.execute_script("var e=document.getElementById('%s');if(e){e.value='%s';e.dispatchEvent(new Event('change'));}" % (fid, val))
    wait_overlay(d)
    jsclick(d, '//*[@id="btnSearch"]/img') or jsclick(d, '//*[@id="btnSearch"]')
    drain(d); time.sleep(2.5)
    wait_overlay(d)
    jsclick(d, '//*[@id="excelDown"]')
    drain(d); time.sleep(7)
    files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
    if not files:
        return []
    import xlrd
    sh = xlrd.open_workbook(files[-1]).sheet_by_index(0)
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
        rows.append((dd, ta, cls(cm), cm[:255], amt, str(row[ci.get('관련번호', 6)])[:50]))
    return rows


os.makedirs(DL, exist_ok=True)
acc = CrawlerAccount.objects.get(platform='gmarket', login_id='rejoice234')
d = create_driver(download_dir=DL, kill_existing=False)
try:
    d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
    print('R 로그인:', _esm_login(d, 'rejoice234', acc.password_enc), flush=True)
    d.get('https://www.esmplus.com/Member/Settle/IacSellBalanceManagement')
    time.sleep(4)
    wait_overlay(d)
    try:
        sel = WebDriverWait(d, 8).until(EC.presence_of_element_located((By.ID, 'sellerId')))
        subs = [o.get_attribute('value') for o in sel.find_elements(By.TAG_NAME, 'option') if o.get_attribute('value')]
    except Exception:
        subs = ['rejoice234']
    print('R [auction] sellerId:', subs, flush=True)
    months = [(date(2026, m, 1), date(2026, m, calendar.monthrange(2026, m)[1])) for m in range(1, 7)]
    for sid in subs:
        allr, mtot = [], {}
        for sdt, edt in months:
            mr = dl_month(d, sid, sdt, edt)
            allr += mr
            mtot['%02d' % sdt.month] = abs(sum(r[4] for r in mr if r[2] in AD))
        GmarketCostHistory.objects.filter(seller_id=sid, market='auction', use_date__year=2026).delete()
        objs, seq = [], {}
        for dd, ta, tt, cm, amt, rel in allr:
            s = seq.get(dd, 0); seq[dd] = s + 1
            objs.append(GmarketCostHistory(seller_id=sid, market='auction', use_date=dd, traded_at=ta,
                        seq=s, use_type='차감' if amt < 0 else '적립', transaction_type=tt,
                        comment=cm, amount=amt, related_no=rel))
        if objs:
            GmarketCostHistory.objects.bulk_create(objs, batch_size=1000)
        adn = len([r for r in allr if r[2] in AD]); adamt = abs(sum(r[4] for r in allr if r[2] in AD))
        print('R   [%s|auction] 광고%d건 합 %s원 | 월별 %s' % (sid, adn, format(adamt, ','),
              ' '.join('%s:%s' % (m, format(v, ',')) for m, v in sorted(mtot.items()))), flush=True)
finally:
    try:
        d.quit()
    except Exception:
        pass
    try:
        stop_display()
    except Exception:
        pass
print('R DONE', flush=True)

import os, re, time, glob, calendar
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
print('R step1 django ok', flush=True)
from datetime import date, datetime
import pytz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException
from crawlers.browser import create_driver, stop_display
from apps.cpc.models import CrawlerAccount, GmarketCostHistory
from crawlers.gmarket_cost_crawler import _esm_login
print('R step2 imports ok', flush=True)

KST = pytz.timezone('Asia/Seoul')
DL = '/tmp/gmkt_xl234'
AD = ('CPC', 'AI매출업', '서버비용')


def drain(d):
    try:
        a = d.switch_to.alert; t = a.text; a.accept(); return t
    except Exception:
        return None


def classify(cm):
    if 'AI매출업' in cm:
        return 'AI매출업'
    if '서버' in cm:
        return '서버비용'
    if 'CPC' in cm or 'cpc' in cm:
        return 'CPC'
    return '기타'


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
    try:
        d.find_element(By.XPATH, '//*[@id="btnSearch"]/img').click()
    except UnexpectedAlertPresentException:
        pass
    drain(d); time.sleep(2)
    try:
        d.find_element(By.XPATH, '//*[@id="excelDown"]').click()
    except UnexpectedAlertPresentException:
        pass
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
        rows.append((dd, ta, classify(cm), cm[:255], amt, str(row[ci.get('관련번호', 6)])[:50]))
    return rows


def save(sid, market, rows):
    GmarketCostHistory.objects.filter(seller_id=sid, market=market, use_date__year=2026).delete()
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


os.makedirs(DL, exist_ok=True)
acc = CrawlerAccount.objects.get(platform='gmarket', login_id='rejoice234')
print('R step3 driver 생성...', flush=True)
d = create_driver(download_dir=DL, kill_existing=False)
print('R step4 driver ok', flush=True)
try:
    d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
    print('R step5 로그인:', _esm_login(d, 'rejoice234', acc.password_enc), flush=True)
    months = [(date(2026, m, 1), date(2026, m, calendar.monthrange(2026, m)[1])) for m in range(1, 7)]
    for label, url in [('gmarket', 'https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'),
                       ('auction', 'https://www.esmplus.com/Member/Settle/IacSellBalanceManagement')]:
        d.get(url); time.sleep(4)
        try:
            sel = WebDriverWait(d, 8).until(EC.presence_of_element_located((By.ID, 'sellerId')))
            subs = [o.get_attribute('value') for o in sel.find_elements(By.TAG_NAME, 'option') if o.get_attribute('value')]
        except Exception:
            subs = ['rejoice234']
        print('R [%s] sellerId: %s' % (label, subs), flush=True)
        for sid in subs:
            allr, mtot = [], {}
            for sdt, edt in months:
                mr = dl_month(d, sid, sdt, edt)
                allr += mr
                mtot['%02d' % sdt.month] = abs(sum(r[4] for r in mr if r[2] in AD))
            amt, adn = save(sid, label, allr)
            print('R   [%s|%s] 광고%d건 합 %s원 | 월별 %s' % (sid, label, adn, format(amt, ','),
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

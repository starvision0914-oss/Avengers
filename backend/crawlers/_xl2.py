import os, re, time, glob, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import UnexpectedAlertPresentException
from crawlers.browser import create_driver
from crawlers.gmarket_cost_crawler import _esm_login
from apps.cpc.models import CrawlerAccount


def drain(d):
    try:
        a = d.switch_to.alert; t = a.text; a.accept(); return t
    except Exception:
        return None


acc = CrawlerAccount.objects.get(platform='gmarket', login_id='rejoice234')
DL = '/tmp/gmkt_xl'
os.makedirs(DL, exist_ok=True)
for f in glob.glob(DL + '/*'):
    os.remove(f)
d = create_driver(download_dir=DL, kill_existing=False)
try:
    d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
    _esm_login(d, 'rejoice234', acc.password_enc)
    d.get('https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'); time.sleep(4)
    Select(d.find_element(By.ID, 'sellerId')).select_by_value('rejoice234'); time.sleep(0.5)
    for fid, val in [('searchSDT', '2026-01-01'), ('searchEDT', '2026-01-31')]:
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
    drain(d); time.sleep(9)
    files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
    if files:
        import xlrd
        sh = xlrd.open_workbook(files[-1]).sheet_by_index(0)
        hdr = [str(x) for x in sh.row_values(0)]
        ci = {h: i for i, h in enumerate(hdr)}
        # 날짜 범위 확인
        dates = []
        for r in range(1, sh.nrows):
            dt = str(sh.row_values(r)[ci['거래일시']])[:10]
            if dt:
                dates.append(dt)
        print('R 총행:', sh.nrows - 1, '| 날짜범위:', min(dates), '~', max(dates), flush=True)
        # 발생구분 분포
        from collections import Counter
        gb = Counter(str(sh.row_values(r)[ci['발생구분']]) for r in range(1, sh.nrows))
        print('R 발생구분:', dict(gb), flush=True)
        # 거래내역 종류 + 각 금액컬럼 합
        print('R 거래내역별 (충전/사용액 · 판매예치금발생 · 광고성이머니):', flush=True)
        agg = {}
        for r in range(1, sh.nrows):
            row = sh.row_values(r)
            cm = str(row[ci['거래내역']])
            a1 = int(re.sub(r'[^\d-]', '', str(row[ci['충전/사용액']])) or 0)
            a2 = int(re.sub(r'[^\d-]', '', str(row[ci['판매예치금 발생액']])) or 0)
            a3 = int(re.sub(r'[^\d-]', '', str(row[ci['광고성이머니발생']])) or 0)
            x = agg.setdefault(cm, [0, 0, 0, 0]); x[0] += 1; x[1] += a1; x[2] += a2; x[3] += a3
        for cm, (n, s1, s2, s3) in sorted(agg.items(), key=lambda x: -abs(x[1][1])):
            print('R   [%s] %d건 | 충전/사용 %s | 예치금 %s | 이머니 %s' % (cm[:24], n, format(s1, ','), format(s2, ','), format(s3, ',')), flush=True)
finally:
    try:
        d.quit()
    except Exception:
        pass
print('R DONE', flush=True)

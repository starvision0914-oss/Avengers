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
    print('R 로그인:', _esm_login(d, 'rejoice234', acc.password_enc), flush=True)
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
    print('R 다운로드:', [os.path.basename(f) for f in files], flush=True)
    if files:
        import xlrd
        sh = xlrd.open_workbook(files[-1]).sheet_by_index(0)
        hdr = [str(x) for x in sh.row_values(0)]
        print('R 행수:', sh.nrows - 1, flush=True)
        print('R 헤더:', hdr, flush=True)
        ci = {h: i for i, h in enumerate(hdr)}
        cm_i = next((i for h, i in ci.items() if '내역' in h), 1)
        amt_i = next((i for h, i in ci.items() if '사용' in h or '금액' in h), 3)
        ad = adcnt = 0
        for r in range(1, sh.nrows):
            row = sh.row_values(r)
            cm = str(row[cm_i]) if cm_i < len(row) else ''
            if '광고구매' in cm:
                a = int(re.sub(r'[^\d-]', '', str(row[amt_i])) or 0)
                ad += a; adcnt += 1
        print('R 엑셀 광고비(광고구매행 충전/사용액 합):', format(abs(ad), ','), '원 (', adcnt, '건)', flush=True)
        print('R 그리드(우리DB)는 24,651원 17건이었음 → 비교', flush=True)
finally:
    try:
        d.quit()
    except Exception:
        pass
print('R DONE', flush=True)

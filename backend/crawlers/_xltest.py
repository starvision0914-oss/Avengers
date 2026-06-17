import os, re, time, glob, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
LOG = open('/tmp/xltest.out', 'w')
def p(*a):
    LOG.write(' '.join(str(x) for x in a) + '\n'); LOG.flush()
p('START')
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
p('드라이버 OK')
try:
    d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
    p('로그인:', _esm_login(d, 'rejoice234', acc.password_enc))
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
        d.find_element(By.XPATH, '//*[@id="excelDown"]').click(); p('엑셀버튼 클릭')
    except UnexpectedAlertPresentException:
        pass
    drain(d); time.sleep(9)
    files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
    p('다운로드:', [os.path.basename(f) for f in files])
    if files:
        import xlrd
        sh = xlrd.open_workbook(files[-1]).sheet_by_index(0)
        p('행수:', sh.nrows, '헤더:', sh.row_values(0))
        for r in range(1, min(5, sh.nrows)):
            p('  행', r, sh.row_values(r))
finally:
    try:
        d.quit()
    except Exception:
        pass
p('DONE')
LOG.close()

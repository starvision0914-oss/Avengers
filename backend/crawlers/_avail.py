import os, re, time, glob
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import UnexpectedAlertPresentException
from crawlers.browser import create_driver, stop_display
from apps.cpc.models import CrawlerAccount
from crawlers.gmarket_cost_crawler import _esm_login

DL = '/tmp/avail_xl'


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


def check(d, sdt, edt):
    for f in glob.glob(DL + '/*'):
        os.remove(f)
    for fid, val in [('searchSDT', sdt), ('searchEDT', edt)]:
        d.execute_script("var e=document.getElementById('%s');if(e){e.value='%s';e.dispatchEvent(new Event('change'));}" % (fid, val))
    wait_overlay(d)
    jc(d, '//*[@id="btnSearch"]/img') or jc(d, '//*[@id="btnSearch"]')
    al = drain(d)
    time.sleep(2)
    wait_overlay(d)
    jc(d, '//*[@id="excelDown"]')
    drain(d); time.sleep(6)
    files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
    if not files:
        return 'NO_FILE alert=%s' % al
    import xlrd
    sh = xlrd.open_workbook(files[-1]).sheet_by_index(0)
    return '%d행' % (sh.nrows - 1)


os.makedirs(DL, exist_ok=True)
acc = CrawlerAccount.objects.get(platform='gmarket', login_id='rejoice234')
d = create_driver(download_dir=DL, kill_existing=False)
try:
    d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
    print('R 로그인:', _esm_login(d, 'rejoice234', acc.password_enc), flush=True)
    d.get('https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'); time.sleep(4)
    Select(d.find_element(By.ID, 'sellerId')).select_by_value('rejoice234'); time.sleep(0.5)
    for y in [2022, 2023, 2024, 2025, 2026]:
        r = check(d, '%d-01-01' % y, '%d-01-31' % y)
        print('R %d-01: %s' % (y, r), flush=True)
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

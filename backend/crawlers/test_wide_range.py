"""엑셀 다운로드가 넓은 날짜범위(1년/전체)를 받아주는지 테스트.
- 같은 sellerId로 (a)월별 합 (b)1년 한번에 (c)전체 한번에 비교 → 행수 일치하면 넓은범위 가능(대폭 가속)
실행: python -u -c "import crawlers.test_wide_range" [login_id]
로그: /tmp/test_wide.log
"""
import os, re, time, glob, calendar, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from datetime import date
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver
from apps.cpc.models import CrawlerAccount
from crawlers.gmarket_cost_crawler import _esm_login

DL = '/tmp/test_wide_xl'
LOG = open('/tmp/test_wide.log', 'a')


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
    for _ in range(20):
        ov = d.find_elements(By.CSS_SELECTOR, '.layer_overlay')
        if not ov or all(not o.is_displayed() for o in ov):
            return
        time.sleep(0.5)


def jc(d, xp):
    els = d.find_elements(By.XPATH, xp)
    if els:
        d.execute_script('arguments[0].click();', els[0]); return True
    return False


def dl_range(d, sid, sdt, edt, label):
    for f in glob.glob(DL + '/*'):
        os.remove(f)
    try:
        Select(d.find_element(By.ID, 'sellerId')).select_by_value(sid)
    except Exception:
        pass
    time.sleep(0.3)
    for fid, val in [('searchSDT', sdt), ('searchEDT', edt)]:
        d.execute_script("var e=document.getElementById('%s');if(e){e.value='%s';e.dispatchEvent(new Event('change'));}" % (fid, val))
    wait_overlay(d)
    jc(d, '//*[@id="btnSearch"]/img') or jc(d, '//*[@id="btnSearch"]')
    al = drain(d)
    time.sleep(2)
    wait_overlay(d)
    al2 = drain(d)
    # 그리드 행수(화면)
    grid_rows = 0
    for tr in d.find_elements(By.CSS_SELECTOR, '#grid_sortingData tr'):
        if re.search(r'20\d\d-\d\d-\d\d', tr.text or ''):
            grid_rows += 1
    jc(d, '//*[@id="excelDown"]')
    al3 = drain(d)
    for _ in range(40):  # 최대 20초 폴링(큰 범위는 오래걸림)
        files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
        if files:
            break
        time.sleep(0.5)
    files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
    xrows = -1
    if files:
        import xlrd
        try:
            sh = xlrd.open_workbook(files[-1]).sheet_by_index(0)
            xrows = sh.nrows - 1
        except Exception as e:
            xrows = 'PARSE_ERR:%s' % str(e)[:50]
    p('  [%s] %s~%s alert=%s/%s/%s 그리드행=%d 엑셀행=%s' % (label, sdt, edt, al, al2, al3, grid_rows, xrows))
    return xrows


os.makedirs(DL, exist_ok=True)
login_id = (sys.argv[1] if len(sys.argv) > 1 else 'rejoice234')
acc = CrawlerAccount.objects.get(platform='gmarket', login_id=login_id)
prof = '/tmp/gmkt_chrome_test_%d' % os.getpid()
d = create_driver(download_dir=DL, kill_existing=False, user_data_dir=prof)
try:
    d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
    p('=== 넓은범위 테스트: %s ===' % login_id)
    if not _esm_login(d, login_id, acc.password_enc):
        p('로그인 실패'); sys.exit(0)
    d.get('https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement')
    time.sleep(4); wait_overlay(d)
    sel = WebDriverWait(d, 8).until(EC.presence_of_element_located((By.ID, 'sellerId')))
    subs = [o.get_attribute('value') for o in sel.find_elements(By.TAG_NAME, 'option') if o.get_attribute('value')]
    p('sellerId 서브목록: %s' % subs)
    sid = subs[0]
    p('--- 테스트 sid=%s ---' % sid)
    # (a) 월별 3개월 합(2025-01,02,03)
    msum = 0
    for m in [1, 2, 3]:
        last = calendar.monthrange(2025, m)[1]
        r = dl_range(d, sid, '2025-%02d-01' % m, '2025-%02d-%02d' % (m, last), '월%02d' % m)
        if isinstance(r, int) and r >= 0: msum += r
    p('  >> 2025 1~3월 월별합: %d행' % msum)
    # (b) 1분기 한번에(2025-01-01~2025-03-31)
    dl_range(d, sid, '2025-01-01', '2025-03-31', '1분기한번에')
    # (c) 1년 한번에(2025 전체)
    dl_range(d, sid, '2025-01-01', '2025-12-31', '2025년전체')
    # (d) 전체기간 한번에(2024-01-01~2026-06-30)
    dl_range(d, sid, '2024-01-01', '2026-06-30', '전체2.5년')
    p('=== 테스트 완료 ===')
finally:
    try: d.quit()
    except Exception: pass
    import shutil; shutil.rmtree(prof, ignore_errors=True)
LOG.close()

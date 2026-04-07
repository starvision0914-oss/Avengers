"""지마켓 간편광고/일반광고 ON/OFF 현황 크롤러"""
import time
import logging
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import create_driver, stop_display

logger = logging.getLogger('crawler')
BID_URL = 'https://ad.esmplus.com/cpc/bidmng/bidmanagement'

def _login(driver, login_id, password):
    driver.get('https://ad.esmplus.com/Member/SignIn/LogOn')
    time.sleep(2)
    try:
        driver.find_element(By.ID, 'SellerId').clear()
        driver.find_element(By.ID, 'SellerId').send_keys(login_id)
        driver.find_element(By.ID, 'SellerPassword').clear()
        driver.find_element(By.ID, 'SellerPassword').send_keys(password)
        try:
            driver.find_element(By.XPATH, '//img[@alt="로그인"]').click()
        except:
            driver.find_element(By.XPATH, '//*[@id="lnkSellerLogin"]/img').click()
        WebDriverWait(driver, 15).until(lambda d: 'SignIn' not in d.current_url and 'LogOn' not in d.current_url)
        time.sleep(2)
        return True
    except Exception as e:
        logger.error(f'로그인 실패 [{login_id}]: {e}')
        return False

def _count_status(driver, table_xpath):
    on, off = 0, 0
    try:
        rows = driver.find_elements(By.XPATH, f'{table_xpath}/tr')
        for row in rows:
            try:
                status_div = row.find_elements(By.TAG_NAME, 'td')
                if len(status_div) >= 3:
                    text = status_div[2].text.strip().upper()
                    if 'ON' in text:
                        on += 1
                    elif 'OFF' in text:
                        off += 1
            except:
                continue
    except:
        pass
    return on, off

def _wait_table_stable(driver, table_xpath, timeout=30):
    prev_count = -1
    stable = 0
    start = time.time()
    while time.time() - start < timeout:
        rows = driver.find_elements(By.XPATH, f'{table_xpath}/tr')
        count = len(rows)
        if count > 0 and count == prev_count:
            stable += 1
            if stable >= 3:
                return True
        else:
            stable = 0
        prev_count = count
        time.sleep(1)
    return prev_count > 0

def collect_one(driver, login_id, log_fn=None):
    def log(m):
        if log_fn: log_fn(f'[CPC상태:{login_id}] {m}')

    driver.get(BID_URL)
    time.sleep(3)

    # CPC1 (일반광고)
    cpc1_on, cpc1_off = 0, 0
    try:
        driver.find_element(By.XPATH, '//*[@id="ulBidMngState"]/li[1]/a/strong').click()
        time.sleep(1)
        try:
            driver.find_element(By.XPATH, "//*[@id='dvGroupAdStateListTab']//a[contains(@href,'#adViewList2')]").click()
            time.sleep(0.5)
            driver.find_element(By.XPATH, "//*[@id='adViewList2']//span[contains(text(),'전체 보기')]").click()
            time.sleep(1)
        except:
            pass
        _wait_table_stable(driver, '//*[@id="tbGroupAdStateList"]')
        cpc1_on, cpc1_off = _count_status(driver, '//*[@id="tbGroupAdStateList"]')
    except Exception as e:
        log(f'CPC1 수집 실패: {e}')

    # CPC2 (간편광고)
    cpc2_on, cpc2_off = 0, 0
    try:
        driver.find_element(By.XPATH, '//*[@id="ulBidMngState"]/li[2]/a/strong').click()
        time.sleep(1)
        try:
            driver.find_element(By.XPATH, "//*[@id='dvGroupAdSmartListTab']//a[contains(@href,'#smartAdviewList')]").click()
            time.sleep(0.5)
            driver.find_element(By.XPATH, "//*[@id='smartAdviewList']//span[contains(text(),'전체 보기')]").click()
            time.sleep(1)
        except:
            pass
        _wait_table_stable(driver, '//*[@id="tbSmartGroupAdStateList"]')
        cpc2_on, cpc2_off = _count_status(driver, '//*[@id="tbSmartGroupAdStateList"]')
    except Exception as e:
        log(f'CPC2 수집 실패: {e}')

    log(f'일반={cpc1_on}ON/{cpc1_off}OFF 간편={cpc2_on}ON/{cpc2_off}OFF')
    return {'cpc1_on': cpc1_on, 'cpc1_off': cpc1_off, 'cpc2_on': cpc2_on, 'cpc2_off': cpc2_off}

def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, GmarketCpcAdStatus, CrawlerLog
    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    if not qs.exists():
        if log_fn: log_fn('활성 계정 없음')
        return {'collected': 0, 'failed': 0}

    collected, failed, driver = 0, 0, None
    try:
        driver = create_driver()
        for acct in qs:
            try:
                driver.delete_all_cookies()
                if not _login(driver, acct.login_id, acct.password_enc):
                    failed += 1
                    continue
                result = collect_one(driver, acct.login_id, log_fn)
                GmarketCpcAdStatus.objects.update_or_create(
                    gmarket_id=acct.login_id, defaults=result
                )
                collected += 1
                CrawlerLog.objects.create(platform='gmarket', level='success',
                    message=f'CPC상태: 일반={result["cpc1_on"]}ON 간편={result["cpc2_on"]}ON', account_id=acct.login_id)
            except Exception as e:
                failed += 1
                CrawlerLog.objects.create(platform='gmarket', level='error', message=str(e), account_id=acct.login_id)
    finally:
        if driver:
            try: driver.quit()
            except: pass
        stop_display()
    if log_fn: log_fn(f'CPC 상태 수집 완료: 성공={collected} 실패={failed}')
    return {'collected': collected, 'failed': failed}

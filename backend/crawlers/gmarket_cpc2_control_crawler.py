"""지마켓 간편광고 ON/OFF 제어"""
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
    """ad.esmplus.com 정상 로그인 — 쿠키 우선, 실패 시 풀로그인(rdoSiteSelect 선택).
    (기존 SignIn 직접 로그인은 rdoSiteSelect 라디오 누락으로 '로그인 실패' → gmarket_crawler 재사용)"""
    from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
    from apps.cpc.models import CrawlerAccount
    acct = CrawlerAccount.objects.filter(login_id=login_id, platform='gmarket').first()
    try:
        if acct and _try_cookie_login(driver, acct):
            return True
        if _full_login(driver, login_id, password):
            if acct:
                _save_cookies(driver, acct)
            return True
    except Exception as e:
        logger.error(f'로그인 실패 [{login_id}]: {e}')
    return False

def _dismiss_alert(driver):
    """'다른광고주가 선택되었습니다' 등 진입 시 뜨는 alert accept(있으면). 떴으면 True."""
    found = False
    for _ in range(3):
        try:
            WebDriverWait(driver, 2).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
            found = True
            time.sleep(1)
        except Exception:
            break
    return found


def _go_cpc2_tab(driver):
    driver.get(BID_URL)
    time.sleep(3)
    if _dismiss_alert(driver):  # 광고주 불일치 alert → 새로고침 후 재진입
        driver.get(BID_URL)
        time.sleep(3)
        _dismiss_alert(driver)
    driver.find_element(By.XPATH, '//*[@id="ulBidMngState"]/li[2]/a/strong').click()
    time.sleep(1)
    try:
        driver.find_element(By.XPATH, "//*[@id='dvGroupAdSmartListTab']//a[contains(@href,'#smartAdviewList')]").click()
        time.sleep(0.5)
        driver.find_element(By.XPATH, "//*[@id='smartAdviewList']//span[contains(text(),'전체 보기')]").click()
        time.sleep(2)
    except:
        pass

def _count_on_off(driver):
    on, off = 0, 0
    rows = driver.find_elements(By.XPATH, '//*[@id="tbSmartGroupAdStateList"]/tr')
    for row in rows:
        tds = row.find_elements(By.TAG_NAME, 'td')
        if len(tds) >= 3:
            t = tds[2].text.strip().upper()
            if 'ON' in t: on += 1
            elif 'OFF' in t: off += 1
    return on, off

def control_one(driver, login_id, action, source='manual', log_fn=None):
    def log(m):
        if log_fn: log_fn(f'[간편:{login_id}] {m}')

    _go_cpc2_tab(driver)
    before_on, before_off = _count_on_off(driver)
    log(f'현재: ON={before_on} OFF={before_off}')

    if action == 'on' and before_off == 0:
        log('이미 전체 ON')
        return {'success': True, 'skipped': True, 'before_on': before_on, 'before_off': before_off}
    if action == 'off' and before_on == 0:
        log('이미 전체 OFF')
        return {'success': True, 'skipped': True, 'before_on': before_on, 'before_off': before_off}

    # 전체 선택
    driver.find_element(By.ID, 'chkSmartAdAll').click()
    time.sleep(0.5)

    # ON/OFF 버튼
    if action == 'on':
        driver.find_element(By.XPATH, '//*[@id="dvGroupAdSmartListTab"]/div[1]/div[2]/div/button[1]/span').click()
    else:
        driver.find_element(By.XPATH, '//*[@id="dvGroupAdSmartListTab"]/div[1]/div[2]/div/button[2]/span').click()

    # Alert 처리
    for _ in range(5):
        try:
            WebDriverWait(driver, 15).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
            time.sleep(0.5)
        except:
            break

    time.sleep(2)
    _go_cpc2_tab(driver)
    after_on, after_off = _count_on_off(driver)
    log(f'결과: ON={after_on} OFF={after_off}')

    return {
        'success': True,
        'before_on': before_on, 'before_off': before_off,
        'after_on': after_on, 'after_off': after_off,
    }

def run_control(action, source='manual', log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, Cpc2History, GmarketCpcAdStatus, CrawlerLog
    from apps.cpc import eleven_block_guard as guard
    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    else:
        qs = [a for a in qs if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

    ok, reason = guard.preflight('지마켓간편광고제어', platform='gmarket', wait=True, wait_timeout=1800)
    if not ok:
        if log_fn:
            log_fn(f'⏭️ 건너뜀 — {reason}')
        return []

    results, driver = [], None
    try:
        driver = create_driver()
        for acct in qs:
            try:
                driver.delete_all_cookies()
                if not _login(driver, acct.login_id, acct.password_enc):
                    continue
                result = control_one(driver, acct.login_id, action, source, log_fn)
                if result and not result.get('skipped'):
                    Cpc2History.objects.create(
                        gmarket_id=acct.login_id, action=action,
                        cpc2_before=result.get('before_on', 0),
                        cpc2_after=result.get('after_on', 0),
                        source=source,
                    )
                    GmarketCpcAdStatus.objects.update_or_create(
                        gmarket_id=acct.login_id,
                        defaults={'cpc2_on': result.get('after_on', 0), 'cpc2_off': result.get('after_off', 0)}
                    )
                results.append(result)
                CrawlerLog.objects.create(platform='gmarket', level='success',
                    message=f'간편광고 {action}: {result.get("before_on")}→{result.get("after_on")}',
                    account_id=acct.login_id)
            except Exception as e:
                if log_fn: log_fn(f'[간편:{acct.login_id}] 실패: {e}')
                CrawlerLog.objects.create(platform='gmarket', level='error', message=str(e), account_id=acct.login_id)
    finally:
        if driver:
            try: driver.quit()
            except: pass
        stop_display()
        guard.release_global_lock(platform='gmarket')
    return results

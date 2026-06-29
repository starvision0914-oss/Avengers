"""지마켓 간편광고 ON/OFF 제어"""
import time
import logging
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException
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
    # 간편광고 서브탭 — 1차 8초, 실패 시 2차 15초 재시도
    SUBTAB_XPATH = "//*[@id='dvGroupAdSmartListTab']//a[contains(@href,'#smartAdviewList')]"
    ALLVIEW_XPATH = "//*[@id='smartAdviewList']//span[contains(text(),'전체 보기')]"
    for wait_sec in (8, 15):
        try:
            WebDriverWait(driver, wait_sec).until(
                EC.element_to_be_clickable((By.XPATH, SUBTAB_XPATH))
            ).click()
            time.sleep(0.5)
            break
        except Exception as e:
            logger.warning(f'간편광고 서브탭 클릭 실패({wait_sec}s): {e}')
    for wait_sec in (5, 10):
        try:
            WebDriverWait(driver, wait_sec).until(
                EC.element_to_be_clickable((By.XPATH, ALLVIEW_XPATH))
            ).click()
            time.sleep(2)
            break
        except Exception as e:
            logger.warning(f'전체 보기 클릭 실패({wait_sec}s): {e}')

def _count_on_off(driver, wait=12):
    # 테이블 로딩 대기 — 12초로 늘려 느린 렌더링 대응
    try:
        WebDriverWait(driver, wait).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="tbSmartGroupAdStateList"]/tr'))
        )
    except Exception:
        pass
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

    # 0건이면 "전체 보기" 재클릭 후 1회 재시도 (느린 탭 렌더링 대응)
    if before_on + before_off == 0:
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='smartAdviewList']//span[contains(text(),'전체 보기')]"))
            ).click()
            time.sleep(3)
        except Exception:
            pass
        before_on, before_off = _count_on_off(driver, wait=15)

    log(f'현재: ON={before_on} OFF={before_off}')

    total = before_on + before_off
    if total == 0:
        # 재시도 후에도 0건 → 실제 광고 없는 계정
        log('간편광고 0건(재시도 후) — 건너뜀')
        return {'success': False, 'skipped': True, 'before_on': 0, 'before_off': 0}
    elif action == 'on' and before_off == 0:
        log('이미 전체 ON')
        return {'success': True, 'skipped': True, 'before_on': before_on, 'before_off': before_off}
    elif action == 'off' and before_on == 0:
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

def run_control(action, source='manual', log_fn=None, account_filter=None, include_cpc1=False):
    """간편광고(스마트) ON/OFF. include_cpc1=True면 같은 로그인으로 일반광고(일반그룹)도 함께 제어."""
    from apps.cpc.models import CrawlerAccount, Cpc2History, GmarketCpcAdStatus, CrawlerLog
    from apps.cpc import eleven_block_guard as guard
    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    if account_filter:
        acct_map = {a.login_id: a for a in qs.filter(login_id__in=account_filter)}
        qs = [acct_map[lid] for lid in account_filter if lid in acct_map]
    else:
        qs = [a for a in qs if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

    # 중복/누적 방지: 이미 광고제어 실행중이면 즉시 스킵
    if not guard.try_acquire_adcontrol('지마켓간편광고제어', platform='gmarket'):
        if log_fn:
            log_fn('⏭️ 이미 광고제어 실행 중 — 중복 방지로 스킵')
        return []

    ok, reason = guard.preflight('지마켓간편광고제어', platform='gmarket', wait=True, wait_timeout=1800)
    if not ok:
        guard.clear_adcontrol_busy('gmarket')
        if log_fn:
            log_fn(f'⏭️ 건너뜀 — {reason}')
        return []

    guard.clear_control_stop('gmarket')   # 새 실행 시작 — 묵은 중지플래그 제거
    results, driver = [], None
    try:
        driver = create_driver()
        # 페이지가 안 열려도 무한대기 않도록 캡(한 계정 14분 멈춤 방지) + 요소 대기 단축
        try:
            driver.set_page_load_timeout(40)
            driver.implicitly_wait(3)
        except Exception:
            pass
        for acct in qs:
            if guard.is_control_stop('gmarket'):
                if log_fn: log_fn('🛑 강제중지 요청 — 중단')
                break
            try:
                # 로그인 2회 재시도(일시적 로그인폼 미로딩=SellerId 못찾음 대비)
                logged = False
                for _try in range(2):
                    try:
                        driver.delete_all_cookies()
                        if _login(driver, acct.login_id, acct.password_enc):
                            logged = True; break
                    except Exception:
                        pass
                    _dismiss_alert(driver); time.sleep(2)
                if not logged:
                    if log_fn: log_fn(f'[간편:{acct.login_id}] 로그인 실패(2회) — 건너뜀')
                    CrawlerLog.objects.create(platform='gmarket', level='error',
                        message='간편 로그인 실패(2회)', account_id=acct.login_id)
                    continue
                # '다른광고주' 알림이 중간에 뜨면 닫고 1회 재시도
                try:
                    result = control_one(driver, acct.login_id, action, source, log_fn)
                except UnexpectedAlertPresentException:
                    _dismiss_alert(driver)
                    result = control_one(driver, acct.login_id, action, source, log_fn)
                after_val = '-'
                if result:
                    # 스킵(이미 ON/OFF)도 진행사항에 보이도록 기록 — 변경없으면 after=before
                    after_val = result.get('after_on')
                    if after_val is None:
                        after_val = result.get('before_on', 0)
                    Cpc2History.objects.create(
                        gmarket_id=acct.login_id, action=action,
                        cpc2_before=result.get('before_on', 0),
                        cpc2_after=after_val,
                        source=source,
                    )
                    if not result.get('skipped'):
                        GmarketCpcAdStatus.objects.update_or_create(
                            gmarket_id=acct.login_id,
                            defaults={'cpc2_on': result.get('after_on', 0), 'cpc2_off': result.get('after_off', 0)}
                        )
                results.append(result)
                CrawlerLog.objects.create(platform='gmarket', level='success',
                    message=f'간편광고 {action}: {result.get("before_on") if result else "-"}→{after_val}',
                    account_id=acct.login_id)

                # 일반광고(일반그룹)도 함께 — 같은 로그인 세션에서 이어서 처리
                if include_cpc1:
                    try:
                        from crawlers.gmarket_cpc1_control_crawler import control_one as _cpc1_one
                        r1 = _cpc1_one(driver, acct.login_id, action, source, log_fn)
                        a1 = r1.get('after_on') if r1 else None
                        if a1 is None:
                            a1 = r1.get('before_on', 0) if r1 else 0
                        # 진행사항에 구분되게 출처에 '/일반' 표기
                        Cpc2History.objects.create(
                            gmarket_id=acct.login_id, action=action,
                            cpc2_before=r1.get('before_on', 0) if r1 else 0,
                            cpc2_after=a1, source=f'{source}/일반')
                        CrawlerLog.objects.create(platform='gmarket', level='success',
                            message=f'일반광고 {action}: {r1.get("before_on") if r1 else "-"}→{a1}',
                            account_id=acct.login_id)
                    except Exception as e1:
                        if log_fn: log_fn(f'[일반:{acct.login_id}] 실패: {e1}')
                        CrawlerLog.objects.create(platform='gmarket', level='error',
                            message=f'일반광고 실패: {e1}', account_id=acct.login_id)
            except Exception as e:
                if log_fn: log_fn(f'[간편:{acct.login_id}] 실패: {e}')
                CrawlerLog.objects.create(platform='gmarket', level='error', message=str(e)[:200], account_id=acct.login_id)
                try: _dismiss_alert(driver)   # 잔여 알림 정리 → 다음 계정 보호(연쇄실패 방지)
                except Exception: pass
    finally:
        if driver:
            try: driver.quit()
            except: pass
        stop_display()
        guard.release_global_lock(platform='gmarket')
        guard.clear_control_stop('gmarket')
        guard.clear_adcontrol_busy('gmarket')
    return results

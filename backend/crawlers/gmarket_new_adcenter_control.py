"""지마켓 신규 광고센터(adcenter.esmplus.com) 캠페인 ON/OFF 제어.
2026-09-04 신규 오픈 — 기존 ad.esmplus.com(간편광고/AI)과는 완전히 별도의 로그인 시스템.
로그인 탭은 'ESM PLUS'가 기본 선택인데 우리 계정은 '지마켓' 탭으로만 로그인됨(실측 확인).
캠페인 목록의 ON/OFF는 확인창 없이 토글 클릭 한 번으로 즉시 반영(실측)."""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException
from .browser import create_driver, stop_display

logger = logging.getLogger('crawler')

LOGIN_URL = 'https://adcenter.esmplus.com/login'
MGMT_URL = 'https://adcenter.esmplus.com/ad/management'


def _dismiss_alert(driver):
    try:
        driver.switch_to.alert.accept()
        return True
    except Exception:
        return False


def _login(driver, login_id, password):
    """adcenter.esmplus.com 로그인 — '지마켓' 탭 선택 후 아이디/비번 입력."""
    driver.get(LOGIN_URL)
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, 'login-username')))
    except TimeoutException:
        return False
    try:
        driver.find_element(By.CSS_SELECTOR, '.button__tab--gmarket').click()
        time.sleep(0.5)
        user = driver.find_element(By.ID, 'login-username')
        user.clear()
        user.send_keys(login_id)
        pw = driver.find_element(By.ID, 'login-password')
        pw.clear()
        pw.send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        time.sleep(3)
    except Exception as e:
        logger.error(f'[신규광고센터:{login_id}] 로그인 폼 처리 오류: {e}')
        return False
    return 'login' not in driver.current_url


def _get_campaign_rows(driver, wait=10, _retried=False):
    """관리 페이지의 캠페인별 (토글엘리먼트, 이름, 현재상태) 목록. 매 호출마다 페이지 새로 진입해야 함
    (토글 클릭 후 다시 읽으려면 이 함수를 재호출).
    2026-09-04 실측: 계정에 따라 캠페인 목록 위에 '구매자에게 관심 받고 있는 상품을...' 추천 위젯이
    추가로 붙어 로딩이 더 걸리는 경우가 있었고, 이때 토글이 아직 안 떴는데 타임아웃돼 '캠페인 0개'로
    잘못 판정한 사례가 실제로 있었다(dlrmsgh012, 실제론 캠페인 5개 존재) — 1회 더 길게 재시도한다."""
    driver.get(MGMT_URL)
    try:
        WebDriverWait(driver, wait).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input.form__toggle')))
    except TimeoutException:
        if not _retried:
            time.sleep(2)
            return _get_campaign_rows(driver, wait=wait * 2, _retried=True)
        return []
    time.sleep(1)
    toggles = driver.find_elements(By.CSS_SELECTOR, 'input.form__toggle')
    names = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr td a, table tbody tr td span.for-a11y')
    # 이름 추출은 부정확할 수 있어(중첩 테이블) 참고용으로만 사용 — 개수만 정확하면 충분
    rows = []
    for i, tgl in enumerate(toggles):
        on = tgl.is_selected()
        rows.append({'idx': i, 'toggle': tgl, 'on': on})
    return rows


def control_one(driver, login_id, action, source='manual', log_fn=None):
    """계정 하나의 전체 캠페인을 action(on/off)으로 일괄 전환. 반환: {'before':N,'after':N,'changed':N}"""
    def log(msg):
        logger.info(f'[신규광고센터:{login_id}] {msg}')
        if log_fn:
            log_fn(f'[신규광고센터:{login_id}] {msg}')

    rows = _get_campaign_rows(driver)
    if not rows:
        log('캠페인 없음/조회 실패')
        return {'before': 0, 'after': 0, 'changed': 0, 'total': 0}

    want_on = (action == 'on')
    before_on = sum(1 for r in rows if r['on'])
    changed = 0
    # 클릭할 때마다 페이지가 리렌더되어 이전에 잡은 엘리먼트 참조가 stale해질 수 있으므로
    # 인덱스 기준으로 매번 다시 조회한다.
    for i in range(len(rows)):
        cur_rows = driver.find_elements(By.CSS_SELECTOR, 'input.form__toggle')
        if i >= len(cur_rows):
            break
        tgl = cur_rows[i]
        if tgl.is_selected() == want_on:
            continue
        try:
            parent = tgl.find_element(By.XPATH, './..')
            parent.click()
            changed += 1
            time.sleep(1)
            # 2026-09-04 실측: 계정 전체가 '운영중지' 상태에서 처음 ON하면 모달이 뜬다 —
            # "운영중인 AI매출업 광고가 있습니다. 캠페인 재개 시 기존 AI매출업 광고는 종료됩니다.
            # 계속하시겠습니까?" 이 모달을 안 닫으면 화면 전체가 막혀 다음 토글부터 전부
            # 'element not interactable'로 실패한다(사용자 확인 후 '확인' 눌러 신규로 전환하기로 결정).
            try:
                modal = driver.find_element(By.CSS_SELECTOR, 'div.box__layer-wrap')
                confirm_btn = modal.find_element(By.CSS_SELECTOR, 'button.button--blue')
                confirm_btn.click()
                log(f'{i}번 토글: AI매출업 종료 확인모달 → 확인 클릭')
                time.sleep(1)
            except Exception:
                pass  # 모달 없음(정상 케이스) — 그냥 진행
        except Exception as e:
            log(f'{i}번 토글 클릭 실패: {e}')

    time.sleep(1)
    final_rows = _get_campaign_rows(driver)
    after_on = sum(1 for r in final_rows if r['on'])
    log(f'{action.upper()} 완료 — 전{before_on}→후{after_on} (변경 {changed}건, 전체 {len(rows)}개)')
    return {'before': before_on, 'after': after_on, 'changed': changed, 'total': len(rows)}


def run_control(action, source='manual', log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, NewAdCenterHistory, CrawlerLog, protected_login_ids
    from apps.cpc import eleven_block_guard as guard

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    protected = protected_login_ids('gmarket')
    if protected:
        qs = qs.exclude(login_id__in=protected)
    if account_filter:
        acct_map = {a.login_id: a for a in qs.filter(login_id__in=account_filter)}
        qs = [acct_map[lid] for lid in account_filter if lid in acct_map]
    else:
        qs = [a for a in qs if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

    if not guard.try_acquire_adcontrol('지마켓신규광고센터제어', platform='gmarket'):
        if log_fn:
            log_fn('⏭️ 이미 광고제어 실행 중 — 중복 방지로 스킵')
        return []

    ok, reason = guard.preflight('지마켓신규광고센터제어', platform='gmarket', wait=True, wait_timeout=10800)
    if not ok:
        guard.clear_adcontrol_busy('gmarket')
        if log_fn:
            log_fn(f'⏭️ 건너뜀 — {reason}')
        return []

    guard.clear_control_stop('gmarket')
    results, driver = [], None
    try:
        driver = create_driver()
        try:
            driver.set_page_load_timeout(40)
        except Exception:
            pass
        for acct in qs:
            if guard.is_control_stop('gmarket'):
                if log_fn: log_fn('🛑 강제중지 요청 — 중단')
                break
            try:
                logged = False
                for _try in range(2):
                    if guard.is_control_stop('gmarket'):
                        break
                    try:
                        driver.delete_all_cookies()
                        if _login(driver, acct.login_id, acct.password_enc):
                            logged = True
                            break
                    except UnexpectedAlertPresentException:
                        _dismiss_alert(driver)
                    except Exception:
                        pass
                    time.sleep(2)
                if not logged:
                    if log_fn: log_fn(f'[신규광고센터:{acct.login_id}] 로그인 실패(2회) — 건너뜀')
                    CrawlerLog.objects.create(platform='gmarket', level='error',
                        message='신규광고센터 로그인 실패(2회)', account_id=acct.login_id)
                    continue

                result = control_one(driver, acct.login_id, action, source, log_fn)
                NewAdCenterHistory.objects.create(
                    gmarket_id=acct.login_id, action=action,
                    campaign_before=result['before'], campaign_after=result['after'],
                    source=source,
                )
                results.append({'login_id': acct.login_id, **result})
            except Exception as e:
                logger.exception(f'[신규광고센터:{acct.login_id}] 제어 오류')
                if log_fn: log_fn(f'[신규광고센터:{acct.login_id}] 오류: {e}')
                CrawlerLog.objects.create(platform='gmarket', level='error',
                    message=f'신규광고센터 제어 오류: {e}', account_id=acct.login_id)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        stop_display()
        guard.clear_adcontrol_busy('gmarket')
        guard.release_global_lock(platform='gmarket')

    return results

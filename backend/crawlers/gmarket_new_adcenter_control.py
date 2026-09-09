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


def _get_campaign_cost_rows(driver, wait=10, _retried=False):
    """관리 페이지 '오늘' 탭(기본값) 캠페인별 광고비용 목록.
    2026-09-09 실측: 표 컬럼 순서 = 체크박스,ON/OFF,캠페인명,상태,캠페인유형,노출수,클릭수,클릭률,
    평균클릭비용,전환수,전환율,전환금액,광고비용,광고수익율 — 12번째(0-index) td가 광고비용.
    캠페인명에 '통합운영'이 들어가면 AI광고(사용자 확인, 2026-09-09), 나머지는 GM_CPC."""
    driver.get(MGMT_URL)
    try:
        WebDriverWait(driver, wait).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input.form__toggle')))
    except TimeoutException:
        if not _retried:
            time.sleep(2)
            return _get_campaign_cost_rows(driver, wait=wait * 2, _retried=True)
        return []
    time.sleep(1)
    rows = []
    for tr in driver.find_elements(By.CSS_SELECTOR, 'table tbody tr'):
        tds = tr.find_elements(By.TAG_NAME, 'td')
        if len(tds) < 13:
            continue
        try:
            name = tds[2].text.strip()
            campaign_type = tds[4].text.strip()
            cost_txt = tds[12].text.strip().replace(',', '')
            cost = int(cost_txt) if cost_txt.isdigit() else 0
        except Exception:
            continue
        if not name:
            continue
        rows.append({'name': name, 'type': campaign_type, 'cost': cost, 'is_ai': '통합운영' in name})
    return rows


def collect_costs(driver, login_id, log_fn=None):
    """한 계정의 오늘자 캠페인별 광고비용을 수집해 upsert. 반환: [{'name','cost','is_ai'}, ...]"""
    from django.utils import timezone
    from apps.cpc.models import GmarketNewAdCost

    def log(msg):
        logger.info(f'[신규광고센터비용:{login_id}] {msg}')
        if log_fn:
            log_fn(f'[신규광고센터비용:{login_id}] {msg}')

    rows = _get_campaign_cost_rows(driver)
    if not rows:
        log('캠페인 없음/조회 실패')
        return []

    today = timezone.localdate()
    for r in rows:
        GmarketNewAdCost.objects.update_or_create(
            login_id=login_id, use_date=today, campaign_name=r['name'],
            defaults={'campaign_type': r['type'], 'is_ai': r['is_ai'], 'cost': r['cost']},
        )
    ai_total = sum(r['cost'] for r in rows if r['is_ai'])
    cpc_total = sum(r['cost'] for r in rows if not r['is_ai'])
    log(f'저장 완료 — AI {ai_total:,}원 / CPC {cpc_total:,}원 (캠페인 {len(rows)}개)')
    return rows


def run_collect_costs(source='manual', log_fn=None, account_filter=None):
    """전체(또는 지정) 계정의 신규광고센터 캠페인별 광고비용 수집."""
    from apps.cpc.models import CrawlerAccount, CrawlerLog, protected_login_ids
    from apps.cpc import eleven_block_guard as guard

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    protected = protected_login_ids('gmarket') - {'dlwodb777'}
    if protected:
        qs = qs.exclude(login_id__in=protected)
    if account_filter:
        acct_map = {a.login_id: a for a in qs.filter(login_id__in=account_filter)}
        qs = [acct_map[lid] for lid in account_filter if lid in acct_map]
    else:
        qs = [a for a in qs if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

    LOCK_PLATFORM = 'gmarket_newad'
    if not guard.try_acquire_adcontrol('지마켓신규광고센터비용수집', platform=LOCK_PLATFORM):
        if log_fn:
            log_fn('⏭️ 이미 광고제어 실행 중 — 중복 방지로 스킵')
        return []
    ok, reason = guard.preflight('지마켓신규광고센터비용수집', platform=LOCK_PLATFORM, wait=True, wait_timeout=10800)
    if not ok:
        guard.clear_adcontrol_busy(LOCK_PLATFORM)
        if log_fn:
            log_fn(f'⏭️ 건너뜀 — {reason}')
        return []

    guard.clear_control_stop(LOCK_PLATFORM)
    results, driver = [], None
    try:
        driver = create_driver()
        try:
            driver.set_page_load_timeout(40)
        except Exception:
            pass
        for acct in qs:
            if guard.is_control_stop(LOCK_PLATFORM):
                if log_fn: log_fn('🛑 강제중지 요청 — 중단')
                break
            try:
                logged = False
                for _try in range(2):
                    if guard.is_control_stop(LOCK_PLATFORM):
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
                    if log_fn: log_fn(f'[신규광고센터비용:{acct.login_id}] 로그인 실패(2회) — 건너뜀')
                    CrawlerLog.objects.create(platform='gmarket', level='error',
                        message='신규광고센터 비용수집 로그인 실패(2회)', account_id=acct.login_id)
                    continue
                rows = collect_costs(driver, acct.login_id, log_fn)
                results.append({'login_id': acct.login_id, 'campaigns': len(rows)})
            except Exception as e:
                logger.exception(f'[신규광고센터비용:{acct.login_id}] 수집 오류')
                if log_fn: log_fn(f'[신규광고센터비용:{acct.login_id}] 오류: {e}')
                CrawlerLog.objects.create(platform='gmarket', level='error',
                    message=f'신규광고센터 비용수집 오류: {e}', account_id=acct.login_id)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        stop_display()
        guard.clear_adcontrol_busy(LOCK_PLATFORM)
        guard.release_global_lock(platform=LOCK_PLATFORM)

    return results


def control_one(driver, login_id, action, source='manual', log_fn=None):
    """계정 하나의 전체 캠페인을 action(on/off)으로 일괄 전환. 반환: {'before':N,'after':N,'changed':N}
    2026-09-09 사용자 지시로 개별토글 클릭 방식 대신 화면의 '전체 캠페인' 체크(#check-all) →
    '노출상태 일괄변경' → ON/OFF 라디오 선택 → '변경하기'로 한 번에 처리(실측 확인한 셀렉터)."""
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
    total = len(rows)

    try:
        driver.find_element(By.ID, 'check-all').click()
        time.sleep(0.5)
        driver.find_element(By.XPATH, "//button[contains(text(),'노출상태 일괄변경')]").click()
        time.sleep(1)
        radio_id = 'status_on' if want_on else 'status_off'
        driver.find_element(By.ID, radio_id).click()
        time.sleep(0.3)
        driver.find_element(
            By.XPATH, "//div[contains(@class,'box__layer-wrap')]//button[contains(text(),'변경하기')]"
        ).click()
        time.sleep(1.5)
        # 2026-09-04 실측: 계정 전체가 '운영중지' 상태에서 처음 ON하면 확인모달이 뜬다 —
        # "운영중인 AI매출업 광고가 있습니다. 캠페인 재개 시 기존 AI매출업 광고는 종료됩니다.
        # 계속하시겠습니까?" 이 모달을 안 닫으면 화면이 막힌다(사용자 확인 후 신규로 전환).
        # '노출상태 일괄변경' 모달과 같은 클래스(box__layer-wrap)를 공유하므로 텍스트로 구분한다.
        try:
            for m in driver.find_elements(By.CSS_SELECTOR, 'div.box__layer-wrap'):
                if m.is_displayed() and ('AI매출업' in m.text or '종료' in m.text):
                    m.find_element(By.CSS_SELECTOR, 'button.button--blue').click()
                    log('AI매출업 종료 확인모달 → 확인 클릭')
                    time.sleep(1)
                    break
        except Exception:
            pass
    except Exception as e:
        log(f'일괄변경 실패: {e}')

    time.sleep(1)
    final_rows = _get_campaign_rows(driver)
    after_on = sum(1 for r in final_rows if r['on'])
    changed = sum(1 for r, f in zip(rows, final_rows) if r['on'] != f['on']) if len(rows) == len(final_rows) else total
    log(f'{action.upper()} 완료(일괄) — 전{before_on}→후{after_on} (전체 {total}개)')
    return {'before': before_on, 'after': after_on, 'changed': changed, 'total': total}


def run_control(action, source='manual', log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, NewAdCenterHistory, CrawlerLog, protected_login_ids
    from apps.cpc import eleven_block_guard as guard

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    # dlwodb777: 상품삭제/판매중지 자동화는 계속 금지(project_gmarket_dlwod777_manual_only)지만,
    # 2026-09-07 사용자가 신규광고센터 on/off만 명시적으로 재요청 — 이 기능에 한해서만 보호 예외.
    protected = protected_login_ids('gmarket') - {'dlwodb777'}
    if protected:
        qs = qs.exclude(login_id__in=protected)
    if account_filter:
        acct_map = {a.login_id: a for a in qs.filter(login_id__in=account_filter)}
        qs = [acct_map[lid] for lid in account_filter if lid in acct_map]
    else:
        qs = [a for a in qs if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

    LOCK_PLATFORM = 'gmarket_newad'  # adcenter.esmplus.com 전용 락 — ad.esmplus.com(간편광고/AI) 크롤과 분리(2026-09-07)

    if not guard.try_acquire_adcontrol('지마켓신규광고센터제어', platform=LOCK_PLATFORM):
        if log_fn:
            log_fn('⏭️ 이미 광고제어 실행 중 — 중복 방지로 스킵')
        return []

    ok, reason = guard.preflight('지마켓신규광고센터제어', platform=LOCK_PLATFORM, wait=True, wait_timeout=10800)
    if not ok:
        guard.clear_adcontrol_busy(LOCK_PLATFORM)
        if log_fn:
            log_fn(f'⏭️ 건너뜀 — {reason}')
        return []

    guard.clear_control_stop(LOCK_PLATFORM)
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
        # LOCK_PLATFORM('gmarket_newad')으로 잡은 락을 'gmarket'으로 잘못 반납해 신규광고센터
        # 전역락이 영구히 안 풀리던 버그(2026-09-09 발견 — 06:55 실행분 락이 계속 남아있었음).
        guard.clear_adcontrol_busy(LOCK_PLATFORM)
        guard.release_global_lock(platform=LOCK_PLATFORM)

    return results

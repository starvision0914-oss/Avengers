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
    (기존 SignIn 직접 로그인은 rdoSiteSelect 라디오 누락으로 '로그인 실패' → gmarket_crawler 재사용)

    '다른광고주가 선택되었습니다' alert은 직전 세션이 서버측에 아직 남아있을 때 로그인 도중
    뜰 수 있음(2026-07-06 실측) — 예전엔 예외로 바로 실패 처리했으나, alert만 닫고
    잠깐 대기 후 재시도하면 대부분 정상 로그인됨."""
    from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
    from apps.cpc.models import CrawlerAccount
    acct = CrawlerAccount.objects.filter(login_id=login_id, platform='gmarket').first()
    for attempt in range(2):
        try:
            if acct and _try_cookie_login(driver, acct):
                return True
            if _full_login(driver, login_id, password):
                if acct:
                    _save_cookies(driver, acct)
                return True
        except UnexpectedAlertPresentException as e:
            if _dismiss_alert(driver) and attempt == 0:
                logger.info(f'[{login_id}] 로그인 중 alert({e}) 감지 — 닫고 재시도')
                time.sleep(3)
                continue
            logger.error(f'로그인 실패 [{login_id}]: {e}')
            return False
        except Exception as e:
            logger.error(f'로그인 실패 [{login_id}]: {e}')
            return False
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
    from apps.cpc import eleven_block_guard as guard
    def log(m):
        if log_fn: log_fn(f'[간편:{login_id}] {m}')

    if guard.is_control_stop('gmarket'):
        log('강제중지 — 스킵')
        return {'success': False, 'skipped': True, 'stopped': True, 'before_on': 0, 'before_off': 0}

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
        if guard.is_control_stop('gmarket'):
            break
        try:
            WebDriverWait(driver, 15).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
            time.sleep(0.5)
        except:
            break

    # 대상 건수가 많을수록(예: 1,500개+) 사이트 자체 처리(선택 반영→저장)가 오래 걸려
    # 고정 대기만으로는 부족 — 처리 중인 페이지에 재진입(get)이 겹치면
    # 'aborted by navigation: Not attached to an active page'로 세션이 죽는다(2026-07-09 실측,
    # rejoice666 1,505개에서 재현). 건수 비례 대기 + 재진입 실패 시 재시도로 완화.
    target_n = before_off if action == 'on' else before_on
    time.sleep(min(2 + target_n / 300.0, 10))
    total_before = before_on + before_off
    for _nav_try in range(2):
        try:
            _go_cpc2_tab(driver)
            after_on, after_off = _count_on_off(driver)
            # 대량 처리 직후 재진입 시 테이블이 아직 안 채워진 채로 렌더링되면 예외 없이
            # 0행을 그대로 돌려줄 수 있다(2026-07-09 tmxkqlwus 1,449건에서 실측 — 재확인이
            # 조용히 0/0으로 나와 DB에 잘못 저장됨). ON/OFF 전환만으로는 총건수가 변하지
            # 않아야 하므로, 총건수가 어긋나면 렌더링 미완료로 보고 재시도/추정치 경로로 보낸다.
            if after_on + after_off != total_before:
                raise RuntimeError(
                    f'재확인 건수 불일치(원래 {total_before}건인데 {after_on + after_off}건 감지 — 렌더링 미완료로 추정)')
            break
        except Exception as e:
            # 세션 자체가 죽은 경우(아래 문구들)는 추정치로 눙치면 안 됨 — 여기서 삼키면
            # run_control의 죽은 driver 감지(dead session → 재생성)가 트리거되지 않아,
            # 이후 전 계정이 로그인 실패로 연쇄 실패한다(2026-07-21 실측, rejoice666 이후
            # 24계정 전부 '로그인 실패(2회)' — 실제로는 driver가 죽어있었을 뿐). 그대로 재던짐.
            dead = any(s in str(e).lower() for s in
                       ('not attached', 'invalid session', 'no such window',
                        'chrome not reachable', 'disconnected', 'aborted by navigation'))
            if dead:
                raise
            if _nav_try == 0:
                log(f'재진입 실패({e}) — 3초 대기 후 재시도')
                time.sleep(3)
            else:
                # 재확인만 실패한 것 — 액션 자체(클릭+alert)는 이미 서버에 반영됐을 가능성이 높음.
                # 다음 상태확인 크롤(crawl_gmarket_cpc_status)이 정확한 값으로 다시 채워줄 것이므로
                # 여기선 목표대로 반영됐다고 가정한 추정치만 기록.
                log(f'결과 재확인 실패({e}) — 액션은 반영됐을 수 있음, 다음 계정 계속')
                after_on, after_off = (total_before, 0) if action == 'on' else (0, total_before)
    log(f'결과: ON={after_on} OFF={after_off}')

    return {
        'success': True,
        'before_on': before_on, 'before_off': before_off,
        'after_on': after_on, 'after_off': after_off,
    }

def run_control(action, source='manual', log_fn=None, account_filter=None, include_cpc1=False):
    """간편광고(스마트) ON/OFF. include_cpc1=True면 같은 로그인으로 일반광고(일반그룹)도 함께 제어."""
    from apps.cpc.models import CrawlerAccount, Cpc2History, GmarketCpcAdStatus, CrawlerLog, protected_login_ids
    from apps.cpc import eleven_block_guard as guard
    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    # 테스트/타사 계정은 account_filter로 명시 지정해도 절대 제어하지 않음(뷰어·다운로드만 허용)
    protected = protected_login_ids('gmarket')
    if protected:
        qs = qs.exclude(login_id__in=protected)
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
                    if guard.is_control_stop('gmarket'):
                        break
                    try:
                        driver.delete_all_cookies()
                        if _login(driver, acct.login_id, acct.password_enc):
                            logged = True; break
                    except Exception:
                        pass
                    _dismiss_alert(driver); time.sleep(2)
                if not logged:
                    if guard.is_control_stop('gmarket'):
                        if log_fn: log_fn('🛑 강제중지 — 로그인 중 중단')
                        break
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

                # 강제중지로 스킵된 경우 — 기록 없이 루프 탈출
                if result and result.get('stopped'):
                    break

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
                    # 스킵(이미 ON/OFF)이어도 현재 값으로 상태 테이블은 항상 갱신
                    cur_on = result.get('after_on', result.get('before_on', 0))
                    cur_off = result.get('after_off', result.get('before_off', 0))
                    GmarketCpcAdStatus.objects.update_or_create(
                        gmarket_id=acct.login_id,
                        defaults={'cpc2_on': cur_on, 'cpc2_off': cur_off}
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
                # 세션이 죽었는지 확인(2026-07-09: rejoice666처럼 대량건 처리 중 네비게이션 충돌로
                # 'not attached'/'invalid session' 발생 시 driver 재사용 불가 → 이후 전 계정 로그인
                # 연쇄실패로 이어졌던 문제). 죽었으면 새 driver로 교체해서 나머지 계정은 계속 진행.
                dead = any(s in str(e).lower() for s in
                           ('invalid session', 'not attached', 'no such window',
                            'chrome not reachable', 'disconnected'))
                if not dead:
                    try:
                        _ = driver.current_url
                    except Exception:
                        dead = True
                if dead:
                    if log_fn: log_fn(f'[간편:{acct.login_id}] 브라우저 세션 손상 감지 — 재생성 후 계속')
                    try: driver.quit()
                    except Exception: pass
                    driver = create_driver()
                    try:
                        driver.set_page_load_timeout(40)
                        driver.implicitly_wait(3)
                    except Exception:
                        pass
                else:
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

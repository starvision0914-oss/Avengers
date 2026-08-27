"""지마켓 L코드 판매중 상품의 판매기간을 '설정안함'(dispEndDate=9999년대)으로 일괄 변경.
(2026-08-27) 가격/판매중지와 달리 판매기간은 필드 하나만 쏘는 작은 API가 없고, 개별 수정화면
(item.esmplus.com/goods/{goods_no})에서 상품 전체정보를 담아 PUT /api/ea/goods/{goods_no}로
저장하는 구조 — 실측 확인(2026-08-27, LCE_MX_L4499910_00: 2034-10-18→9999-12-31, sellStatus/가격 불변).
그래서 건별로 '수정화면 열기→판매기간 탭 클릭→저장 클릭' UI클릭 자동화가 맞다.

이미 dispEndDate 연도가 9999인 건(=사실상 설정안함)은 열기 전에 검색API로 걸러 스킵 —
재실행 시 자동으로 남은 것만 처리되는 자연스러운 재개(resume) 구조."""
import json
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .gmarket_loss_delete import _log, _GOODS_LOOKUP_JS

_UNLIMITED_YEAR = '9999'
_LOOKUP_CHUNK = 200
_PACE_SEC = 1.5   # 사람처럼 페이싱(수정화면 저장은 판매중지/가격보다 무거운 액션 — 더 여유있게)


def _safe_click(driver, el):
    """일반 Selenium .click()이 기본(실측 확인: PUT 200 정상 반영).
    (2026-08-27) CDP Input.dispatchMouseEvent(_cdp_click)로 바꿔봤더니 좌표는 정확해도
    React onClick이 아예 반응 안 함(class 안 바뀌고 PUT도 안 나감) — 이 폼에는 안 맞음.
    반대로 'element click intercepted'가 뜨는 드문 경우엔 JS click()으로 폴백
    (실제 click 이벤트가 발생해 React 델리게이션이 잡아냄)."""
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)


def _lookup_disp_end_dates(driver, product_nos, log_fn=None):
    """product_no 목록 -> {product_no: {goods_no, dispEndDate}}."""
    result = {}
    for i in range(0, len(product_nos), _LOOKUP_CHUNK):
        chunk = [str(p) for p in product_nos[i:i + _LOOKUP_CHUNK]]
        ids = ','.join(chunk)
        try:
            txt = driver.execute_async_script(_GOODS_LOOKUP_JS, ids)
            data = json.loads(txt).get('data') or {}
        except Exception as e:
            _log(log_fn, f'  ❌ 조회 예외: {e}')
            continue
        for it in data.get('items') or []:
            goods_no = it.get('goodsNo')
            disp_end = it.get('dispEndDate') or ''
            site_no = it.get('siteGoodsNo') or {}
            for site in ('gmkt', 'iac'):
                pno = site_no.get(site)
                if pno and str(pno) in chunk:
                    result[str(pno)] = {'goods_no': goods_no, 'dispEndDate': disp_end}
        time.sleep(0.3)
    return result


def _fix_one(driver, goods_no, seller_id, log_fn=None):
    """개별 수정화면에서 판매기간→설정안함 클릭 후 저장. 성공한 PUT 응답(200/204)만 성공으로 인정."""
    driver.switch_to.default_content()
    driver.get(f'https://www.esmplus.com/Home/v2/goods-edit?seq={goods_no}')
    try:
        iframe = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'innerIFrame')))
        driver.switch_to.frame(iframe)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//span[normalize-space(text())='판매기간']")))
    except Exception as e:
        _log(log_fn, f'    ⚠ {goods_no} 수정화면 로딩 실패: {e}')
        return False

    try:
        btn = driver.find_element(
            By.XPATH,
            "//span[normalize-space(text())='판매기간']/ancestor::div[contains(@class,'box__filter-item')][1]"
            "//button[normalize-space(text())='설정안함']")
        if 'is-active' in (btn.get_attribute('class') or ''):
            return True   # 이미 설정안함 — 저장 안 해도 됨
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.2)
        _safe_click(driver, btn)
        time.sleep(0.3)
        if 'is-active' not in (btn.get_attribute('class') or ''):
            _log(log_fn, f'    ⚠ {goods_no} 탭 클릭했지만 활성화 안 됨 — 저장 생략')
            return False

        save_btn = driver.find_element(By.XPATH, "//button[normalize-space(text())='수정하기']")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", save_btn)
        time.sleep(0.2)
        driver.get_log('performance')  # 클릭 전 비우기
        _safe_click(driver, save_btn)
    except Exception as e:
        _log(log_fn, f'    ❌ {goods_no} 클릭/저장 예외: {e}')
        return False

    # 저장 후 리다이렉트(결과페이지→광고 넛지 페이지)까지 이어지며 이미지/JS 등 리소스가 많이 뜨는
    # 무거운 페이지라 고정 대기(2초)로는 PUT 응답이 늦게 잡혀 '실패'로 오판되는 사례가 실측됨
    # (2026-08-27: 실제로는 저장됐는데 스크립트가 실패로 기록). 응답 올 때까지 폴링으로 대체.
    ok_status = None
    target_url_part = f'/api/ea/goods/{goods_no}'
    req_ids = set()
    deadline = time.time() + 8
    while time.time() < deadline and ok_status is None:
        time.sleep(0.5)
        try:
            for entry in driver.get_log('performance'):
                try:
                    msg = json.loads(entry['message'])['message']
                except Exception:
                    continue
                m = msg.get('method')
                if m == 'Network.requestWillBeSent':
                    req = msg['params']['request']
                    if req.get('method') == 'PUT' and target_url_part in req.get('url', ''):
                        req_ids.add(msg['params']['requestId'])
                elif m == 'Network.responseReceived' and msg['params'].get('requestId') in req_ids:
                    ok_status = msg['params']['response'].get('status')
                    break
        except Exception as e:
            _log(log_fn, f'    ⚠ {goods_no} 응답로그 파싱 예외: {e}')
            break

    return ok_status in (200, 204)


_MAX_CONSECUTIVE_FAILS = 5   # 연속 실패시 시스템적 버그 가능성 — 계속 밀어붙이지 않고 조기중단
_LOCK_CYCLE = 40   # 이 건수마다 락을 반납했다가 다시 잡음 — 몇 시간~며칠짜리 작업이 매시간 도는
                   # 광고비 크론 등 다른 지마켓 작업을 계속 막아버리는 문제 방지(2026-08-27 사용자 지적)


def run_saleperiod_fix(login_ids=None, limit=None, log_fn=None):
    """login_ids: None이면 전체 활성 지마켓 계정.
    limit: 이번 실행에서 시도(성공+실패)할 최대 건수 상한(테스트용) — 성공 건수만 세면 전부 실패해도
    안 멈추는 문제(2026-08-27 실측: click intercepted 버그로 940여건 실패하며 계속 진행)가 있어
    시도 총량 기준으로 뀸.
    락은 _LOCK_CYCLE건마다 반납→재획득(대기)한다 — 규모가 커서(전체 10만건대) 하루 이상 걸리는데,
    그 사이 계속 락을 쥐고 있으면 매시간 도는 광고비 크론 등이 전부 막힌다."""
    from apps.cpc.models import CrawlerAccount, GmarketMyProduct
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display
    from crawlers.gmarket_product_crawler import _try_cookie_login, _enter_goods_iframe, _esm_login, _save_cookies
    from django.db.models import Q

    if login_ids:
        accounts = list(CrawlerAccount.objects.filter(platform='gmarket', login_id__in=login_ids))
    else:
        accounts = list(CrawlerAccount.objects.filter(platform='gmarket', is_active=True))

    summary = {'accounts': 0, 'checked': 0, 'already_ok': 0, 'fixed': 0, 'failed': 0, 'verified': 0, 'verify_mismatch': 0}
    driver = None
    lock_held = False
    consecutive_fails = 0
    aborted = False

    def _acquire(acct_name):
        nonlocal lock_held
        ok, reason = guard.preflight('지마켓판매기간설정안함', platform='gmarket', wait=True)
        if ok:
            lock_held = True
        else:
            _log(log_fn, f'⛔ 락 재획득 실패({acct_name}): {reason}')
        return ok

    def _release():
        nonlocal driver, lock_held
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
            driver = None
        guard.release_global_lock('gmarket')
        lock_held = False

    def _login(acct):
        nonlocal driver
        driver = create_driver(enable_perf_log=True)
        logged = _try_cookie_login(driver, acct)
        if not logged:
            logged = _esm_login(driver, acct.login_id, acct.password_enc)
            if logged:
                _save_cookies(driver, acct)
        return logged and _enter_goods_iframe(driver)

    try:
        for acct in accounts:
            if aborted:
                break
            if limit and (summary['fixed'] + summary['failed']) >= limit:
                break
            pnos = list(GmarketMyProduct.objects.filter(account=acct, status_type='판매중').filter(
                Q(seller_product_code__startswith='LCE_SX_') | Q(seller_product_code__startswith='LCE_MX_')
            ).values_list('product_no', flat=True))
            if not pnos:
                continue

            if not _acquire(acct.login_id):
                continue
            if not _login(acct):
                _log(log_fn, f'[{acct.login_id}] ❌ 로그인/진입 실패 — 스킵')
                _release()
                continue

            info = _lookup_disp_end_dates(driver, pnos, log_fn)
            targets = [(pno, meta) for pno, meta in info.items() if not meta['dispEndDate'].startswith(_UNLIMITED_YEAR)]
            summary['accounts'] += 1
            summary['checked'] += len(info)
            summary['already_ok'] += len(info) - len(targets)
            _log(log_fn, f'[{acct.login_id}] L코드 판매중 {len(pnos)}건 중 조회됨 {len(info)}건, 대상(판매기간 설정됨) {len(targets)}건')

            idx = 0
            while idx < len(targets):
                if aborted or (limit and (summary['fixed'] + summary['failed']) >= limit):
                    break
                chunk = targets[idx:idx + _LOCK_CYCLE]
                idx += _LOCK_CYCLE

                http_ok_pnos = []
                for pno, meta in chunk:
                    if limit and (summary['fixed'] + summary['failed']) >= limit:
                        break
                    ok2 = _fix_one(driver, meta['goods_no'], acct.login_id, log_fn)
                    if ok2:
                        summary['fixed'] += 1
                        consecutive_fails = 0
                        http_ok_pnos.append(pno)
                        _log(log_fn, f'  ✅ {pno}(goods_no={meta["goods_no"]}) 저장응답 성공')
                    else:
                        summary['failed'] += 1
                        consecutive_fails += 1
                        _log(log_fn, f'  ❌ {pno}(goods_no={meta["goods_no"]}) 실패')
                        if consecutive_fails >= _MAX_CONSECUTIVE_FAILS:
                            _log(log_fn, f'⛔ 연속 {consecutive_fails}건 실패 — 시스템적 문제 가능성, 중단')
                            aborted = True
                            break
                    time.sleep(_PACE_SEC)

                # 저장응답(HTTP)만 믿지 않고, 실제로 dispEndDate가 9999년대로 바뀌었는지 재조회로 확인
                # (2026-08-26 판매중지 로그성공≠실제반영 사례 재발 방지)
                if http_ok_pnos:
                    driver.switch_to.default_content()
                    driver.get('https://www.esmplus.com/Home/v2/goods-manage')
                    time.sleep(1.5)
                    _enter_goods_iframe(driver)
                    recheck = _lookup_disp_end_dates(driver, http_ok_pnos, log_fn)
                    for pno in http_ok_pnos:
                        de = recheck.get(pno, {}).get('dispEndDate', '')
                        if de.startswith(_UNLIMITED_YEAR):
                            summary['verified'] += 1
                        else:
                            summary['verify_mismatch'] += 1
                            _log(log_fn, f'  ⚠ 실제반영 불일치: {pno} 저장응답은 성공이었으나 재조회 dispEndDate={de}')

                more_left = idx < len(targets)
                limit_reached = limit and (summary['fixed'] + summary['failed']) >= limit
                if more_left and not aborted and not limit_reached:
                    _log(log_fn, f'  ↻ {_LOCK_CYCLE}건 처리 — 락 반납 후 재획득 대기(다른 지마켓 작업 양보)')
                    _release()
                    time.sleep(3)
                    if not _acquire(acct.login_id) or not _login(acct):
                        _log(log_fn, f'[{acct.login_id}] ❌ 재획득/재로그인 실패 — 이 계정 중단')
                        break

            _release()

        _log(log_fn, f'완료 — {summary}')
        return {'ok': True, **summary}
    finally:
        if lock_held or driver:
            _release()
        stop_display()

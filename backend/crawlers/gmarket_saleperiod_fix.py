"""지마켓 L코드 판매중 상품의 판매기간+할인을 둘 다 '설정안함'으로 일괄 변경.
(2026-08-27) 가격/판매중지와 달리 판매기간·할인은 필드 하나만 쏘는 작은 API가 없고, 개별 수정화면
(item.esmplus.com/goods/{goods_no})에서 상품 전체정보를 담아 PUT /api/ea/goods/{goods_no}로
저장하는 구조 — 실측 확인(2026-08-27, LCE_MX_L4499910_00: 2034-10-18→9999-12-31, sellStatus/가격 불변).
그래서 건별로 '수정화면 열기→판매기간/할인 탭 클릭→저장 클릭' UI클릭 자동화가 맞다.
(2026-08-28) 할인도 같은 수정화면의 별도 box__filter-item('할인' 라벨, 설정함/설정안함 버튼)이라
한 번의 페이지 방문+한 번의 저장 클릭으로 두 설정을 함께 반영 — 실측 확인(dlwodbs222/4494707994:
sellerDiscount type=2(11%)→type=0/discountAmt=0, 판매기간 9999 유지, price 불변).

이미 dispEndDate 연도가 9999년대 + sellerDiscount.gmkt.type==0(할인없음)인 건은 열기 전에
검색API로 걸러 스킵 — 재실행 시 자동으로 남은 것만 처리되는 자연스러운 재개(resume) 구조."""
import json
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .gmarket_loss_delete import _log, _GOODS_LOOKUP_JS

_FAILLOG = '/tmp/gmkt_saleperiod_failures.log'


def _log_failure(m):
    """강제선점으로 재개될 때 stdout 리다이렉트가 유실돼도(2026-08-28 실측: 원본 argv만
    재실행되고 nohup 리다이렉트는 안 살아남아 로그가 끊김) 실패/불일치는 반드시 이 파일에
    남도록 stdout과 무관하게 직접 기록."""
    try:
        from django.utils import timezone
        with open(_FAILLOG, 'a', encoding='utf-8') as f:
            f.write(f'[{timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")}] {m}\n')
    except Exception:
        pass

_UNLIMITED_YEAR = '9999'
_LOOKUP_CHUNK = 200
_PACE_SEC = 0.2   # 사람처럼 페이싱(2026-08-27: 1.5초→0.5초, 2026-08-28 사용자 요청으로 추가단축 0.5초→0.2초)


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
    """product_no 목록 -> {product_no: {goods_no, dispEndDate, discount_type, discount_amt}}."""
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
            disc = (it.get('sellerDiscount') or {}).get('gmkt') or {}
            site_no = it.get('siteGoodsNo') or {}
            for site in ('gmkt', 'iac'):
                pno = site_no.get(site)
                if pno and str(pno) in chunk:
                    result[str(pno)] = {
                        'goods_no': goods_no, 'dispEndDate': disp_end,
                        'discount_type': disc.get('type'), 'discount_amt': disc.get('discountAmt'),
                    }
        time.sleep(0.3)
    return result


def _click_tab_off(driver, label_text, log_fn, goods_no):
    """label_text(정확매치, class에 'text' 포함) 라벨의 box__filter-item 안 '설정안함' 버튼 클릭.
    반환: (already_off, clicked_ok). 라벨 자체를 못 찾으면 (False, None) — 이 상품엔 해당 설정 탭이 없음(옵션상품 등)."""
    try:
        label = driver.find_element(
            By.XPATH, f"//span[normalize-space(text())='{label_text}' and contains(@class,'text')]")
        box = label.find_element(By.XPATH, "ancestor::div[contains(@class,'box__filter-item')][1]")
        btn = box.find_element(By.XPATH, ".//button[normalize-space(text())='설정안함']")
    except Exception:
        return False, None
    if 'is-active' in (btn.get_attribute('class') or ''):
        return True, True
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.1)
        _safe_click(driver, btn)
        time.sleep(0.15)
        if 'is-active' not in (btn.get_attribute('class') or ''):
            _log(log_fn, f'    ⚠ {goods_no} {label_text} 탭 클릭했지만 활성화 안 됨')
            return False, False
        return False, True
    except Exception as e:
        _log(log_fn, f'    ❌ {goods_no} {label_text} 클릭 예외: {e}')
        return False, False


def _fix_one(driver, goods_no, seller_id, log_fn=None, only_period=False):
    """개별 수정화면에서 판매기간(+할인, only_period=False일 때만) →설정안함 클릭 후 한 번에 저장.
    성공한 PUT 응답(200/204)만 성공으로 인정."""
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
        period_off, period_clicked = _click_tab_off(driver, '판매기간', log_fn, goods_no)
        if only_period:
            disc_off, disc_clicked = True, True   # 할인 탭 건드리지 않음(2026-08-28: 실패건 재시도는 판매기간만)
        else:
            disc_off, disc_clicked = _click_tab_off(driver, '할인', log_fn, goods_no)
        if period_clicked is False or disc_clicked is False:
            _log(log_fn, f'    ⚠ {goods_no} 탭 클릭 실패 — 저장 생략')
            return False
        need_save = (period_clicked and not period_off) or (disc_clicked and not disc_off)
        if not need_save:
            return True   # 이미 둘 다 설정안함 — 저장 안 해도 됨

        save_btn = driver.find_element(By.XPATH, "//button[normalize-space(text())='수정하기']")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", save_btn)
        time.sleep(0.1)
        driver.get_log('performance')  # 클릭 전 비우기
        _safe_click(driver, save_btn)
        # 할인 해제는 가끔 확인 alert가 뜰 수 있어 즉시 처리(안 뜨면 즉시 통과).
        # (2026-08-28) WebDriverWait(2초)는 alert 없는 대다수 케이스에서도 매번 풀타임아웃까지
        # 기다려 건당 2초씩 낭비됐음 — 0.3초 폴링(poll_frequency 0.1초)로 단축, 있으면 그새 잡힘.
        try:
            WebDriverWait(driver, 0.3, poll_frequency=0.1).until(EC.alert_is_present())
            al = driver.switch_to.alert
            _log(log_fn, f'    ℹ {goods_no} 저장 alert: {al.text[:60]}')
            al.accept()
        except Exception:
            pass
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
        time.sleep(0.2)
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
_SKIP_RECENT_HOURS = 2   # scan_only 재시작시 이 시간 내 이미 스캔된 계정은 재스캔 생략
_LOCK_CYCLE = 40   # 이 건수마다 락을 반납했다가 다시 잡음 — 몇 시간~며칠짜리 작업이 매시간 도는
                   # 광고비 크론 등 다른 지마켓 작업을 계속 막아버리는 문제 방지(2026-08-27 사용자 지적)


def _needs_fix(meta):
    return not (meta['dispEndDate'].startswith(_UNLIMITED_YEAR) and meta.get('discount_type') == 0)


def _save_status(acct, info, log_fn=None):
    """조회 결과(info: {pno: meta})를 GmarketSalePeriodStatus에 upsert(2026-08-28 사용자 요청 —
    매번 재조회 없이 계정별 판매기간 임박도를 DB로 바로 확인할 수 있게)."""
    from django.utils import timezone
    from apps.cpc.models import GmarketSalePeriodStatus
    if not info:
        return
    now = timezone.now()
    rows = [
        GmarketSalePeriodStatus(
            account=acct, product_no=pno, goods_no=meta.get('goods_no') or '',
            disp_end_date=meta.get('dispEndDate') or '', discount_type=meta.get('discount_type'),
            discount_amt=meta.get('discount_amt'), needs_fix=_needs_fix(meta), checked_at=now,
        )
        for pno, meta in info.items()
    ]
    try:
        # MySQL/MariaDB: update_conflicts=True 사용하되 unique_fields는 지정 불가
        # (UniqueConstraint(account,product_no)로 ON DUPLICATE KEY UPDATE 동작) — gmarket_product_crawner와 동일 패턴.
        GmarketSalePeriodStatus.objects.bulk_create(
            rows, update_conflicts=True,
            update_fields=['goods_no', 'disp_end_date', 'discount_type', 'discount_amt', 'needs_fix', 'checked_at'],
            batch_size=1000,
        )
    except Exception as e:
        _log(log_fn, f'  ⚠ 상태 저장 실패: {e}')


def run_saleperiod_fix(login_ids=None, limit=None, log_fn=None, scan_only=False, skip_auction=False):
    """login_ids: None이면 전체 활성 지마켓 계정.
    limit: 이번 실행에서 시도(성공+실패)할 최대 건수 상한(테스트용) — 성공 건수만 세면 전부 실패해도
    안 멈추는 문제(2026-08-27 실측: click intercepted 버그로 940여건 실패하며 계속 진행)가 있어
    시도 총량 기준으로 뀸.
    scan_only=True면 계정별 대상 건수만 조회+로그로 보여주고 실제 수정(edit 페이지 진입)은 하지 않음
    (2026-08-28 사용자 요청: 실행 전 리스트+숫자 확인).
    락은 _LOCK_CYCLE건마다 반납→재획득(대기)한다 — 규모가 커서(전체 10만건대) 하루 이상 걸리는데,
    그 사이 계속 락을 쥐고 있으면 매시간 도는 광고비 크론 등이 전부 막힌다."""
    from apps.cpc.models import CrawlerAccount, GmarketMyProduct, protected_login_ids
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display
    from crawlers.gmarket_product_crawler import _try_cookie_login, _enter_goods_iframe, _esm_login, _save_cookies
    from django.db.models import Q

    protected = protected_login_ids('gmarket')
    if login_ids:
        accounts = list(CrawlerAccount.objects.filter(platform='gmarket', login_id__in=login_ids).exclude(login_id__in=protected))
    else:
        accounts = list(CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(login_id__in=protected))

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
            pq = GmarketMyProduct.objects.filter(account=acct, status_type='판매중').filter(
                Q(seller_product_code__startswith='LCE_SX_') | Q(seller_product_code__startswith='LCE_MX_')
            )
            if skip_auction:
                # 옥션(상품번호 F접두) 수정화면에서 유독 저장실패가 반복되는 패턴 확인(2026-08-28) —
                # 원인 파악 전까지 지마켓(gmkt)만 먼저 처리, 옥션은 나중에 별도로.
                pq = pq.exclude(product_no__startswith='F')
            pnos = list(pq.values_list('product_no', flat=True))
            if not pnos:
                continue

            if scan_only:
                # (2026-08-28) 강제선점으로 죽었다 재시작될 때마다 계정 순회가 처음부터 다시 돌아
                # 이미 스캔한 계정을 매번 재스캔하며 시간을 크게 낭비하던 문제 확인 — 최근
                # _SKIP_RECENT_HOURS 이내에 이 계정 상품 대부분이 이미 스캔됐으면 건너뛴다.
                from django.utils import timezone
                from apps.cpc.models import GmarketSalePeriodStatus
                recent_cutoff = timezone.now() - timezone.timedelta(hours=_SKIP_RECENT_HOURS)
                recent_checked = GmarketSalePeriodStatus.objects.filter(
                    account=acct, product_no__in=pnos, checked_at__gte=recent_cutoff).count()
                if pnos and recent_checked / len(pnos) >= 0.9:
                    _log(log_fn, f'[{acct.login_id}] 최근 {_SKIP_RECENT_HOURS}시간 내 스캔됨({recent_checked}/{len(pnos)}) — 재스캔 스킵')
                    continue

            if not _acquire(acct.login_id):
                continue
            try:
                login_ok = _login(acct)
            except Exception as e:
                _log(log_fn, f'[{acct.login_id}] ❌ 로그인 중 예외 — 스킵: {e}')
                _log_failure(f'[{acct.login_id}] 로그인 중 예외로 계정 스킵: {e}')
                _release()
                continue
            if not login_ok:
                _log(log_fn, f'[{acct.login_id}] ❌ 로그인/진입 실패 — 스킵')
                _release()
                continue

            try:
                info = _lookup_disp_end_dates(driver, pnos, log_fn)
                _save_status(acct, info, log_fn)
            except Exception as e:
                # (2026-08-28) 예기치 못한 예외(브라우저 크래시 등)가 전체 프로세스를 죽여
                # 재개큐도 없이 통째로 멈추던 사고 재발방지 — 이 계정만 건너뛰고 계속 진행.
                _log(log_fn, f'[{acct.login_id}] ❌ 조회 중 예외 — 스킵: {e}')
                _log_failure(f'[{acct.login_id}] 조회 중 예외로 계정 스킵: {e}')
                _release()
                continue
            targets = [(pno, meta) for pno, meta in info.items() if _needs_fix(meta)]
            # 판매종료일 임박한 것부터 우선 처리(2026-08-28 사용자 요청) — 미설정(9999년대)은
            # 안 급하니 뒤로, 그 외엔 종료일 오름차순(가장 임박한 게 먼저).
            targets.sort(key=lambda t: t[1].get('dispEndDate') or '9999')
            summary['accounts'] += 1
            summary['checked'] += len(info)
            summary['already_ok'] += len(info) - len(targets)
            summary.setdefault('by_account', {})[acct.login_id] = {'checked': len(info), 'targets': len(targets)}
            _log(log_fn, f'[{acct.login_id}] L코드 판매중 {len(pnos)}건 중 조회됨 {len(info)}건, '
                          f'대상(판매기간·할인 중 하나라도 설정됨) {len(targets)}건')

            if scan_only:
                _release()
                continue

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
                        _log_failure(f'[{acct.login_id}] {pno}(goods_no={meta["goods_no"]}) 저장 실패')
                        if consecutive_fails >= _MAX_CONSECUTIVE_FAILS:
                            _log(log_fn, f'⛔ 연속 {consecutive_fails}건 실패 — 시스템적 문제 가능성, 중단')
                            _log_failure(f'[{acct.login_id}] 연속 {consecutive_fails}건 실패 — 중단')
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
                    _save_status(acct, recheck, log_fn)
                    for pno in http_ok_pnos:
                        rm = recheck.get(pno, {})
                        if not _needs_fix({'dispEndDate': rm.get('dispEndDate', ''), 'discount_type': rm.get('discount_type')}):
                            summary['verified'] += 1
                        else:
                            summary['verify_mismatch'] += 1
                            msg = (f'실제반영 불일치: {pno} 저장응답은 성공이었으나 재조회 '
                                   f'dispEndDate={rm.get("dispEndDate")} discount_type={rm.get("discount_type")}')
                            _log(log_fn, f'  ⚠ {msg}')
                            _log_failure(f'[{acct.login_id}] {msg}')

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


def run_targeted_fix(targets, log_fn=None, only_period=False):
    """명시적으로 지정한 (login_id, product_no, goods_no) 목록만 처리(2026-08-28 사용자 요청 —
    할인율1%+판매기간90일이하 같은 조건으로 뽑은 특정 대상만 돌리고 싶을 때).
    targets: [{'login_id':.., 'product_no':.., 'goods_no':..}, ...]
    실패해도 중단하지 않고 다음 건으로 넘어감(연속 N회 중단 규칙은 여기선 적용 안 함 —
    이미 조건으로 좁힌 소규모 대상이라 끝까지 밀어붙이고 실패건만 나중에 재시도하는 게 목적).
    반환: {'ok', 'fixed', 'failed', 'verified', 'verify_mismatch', 'failed_targets'(재시도용 원본 dict 리스트)}"""
    from apps.cpc.models import CrawlerAccount, protected_login_ids
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display
    from crawlers.gmarket_product_crawler import _try_cookie_login, _enter_goods_iframe, _esm_login, _save_cookies

    protected = protected_login_ids('gmarket')
    by_acc = {}
    for t in targets:
        if t['login_id'] in protected:
            continue
        by_acc.setdefault(t['login_id'], []).append(t)

    summary = {'fixed': 0, 'failed': 0, 'verified': 0, 'verify_mismatch': 0}
    failed_targets = []
    driver = None
    lock_held = False

    def _acquire():
        nonlocal lock_held
        ok, reason = guard.preflight('지마켓판매기간설정안함', platform='gmarket', wait=True)
        if ok:
            lock_held = True
        else:
            _log(log_fn, f'⛔ 락 획득 실패: {reason}')
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
        for login_id, items in by_acc.items():
            acct = CrawlerAccount.objects.filter(platform='gmarket', login_id=login_id).first()
            if not acct:
                for t in items:
                    failed_targets.append(t)
                continue
            if not _acquire():
                for t in items:
                    failed_targets.append(t)
                continue
            try:
                login_ok = _login(acct)
            except Exception as e:
                _log(log_fn, f'[{login_id}] ❌ 로그인 중 예외: {e}')
                _log_failure(f'[{login_id}] 타겟실행 로그인 중 예외: {e}')
                login_ok = False
            if not login_ok:
                _log(log_fn, f'[{login_id}] ❌ 로그인/진입 실패 — 이 계정 전체 실패처리')
                for t in items:
                    failed_targets.append(t)
                _release()
                continue

            idx = 0
            while idx < len(items):
                chunk = items[idx:idx + _LOCK_CYCLE]
                idx += _LOCK_CYCLE
                http_ok = []
                for t in chunk:
                    try:
                        ok2 = _fix_one(driver, t['goods_no'], login_id, log_fn, only_period=only_period)
                    except Exception as e:
                        _log(log_fn, f'  ❌ {t["product_no"]} 처리 중 예외: {e}')
                        ok2 = False
                    if ok2:
                        summary['fixed'] += 1
                        http_ok.append(t)
                        _log(log_fn, f'  ✅ {t["product_no"]}(goods_no={t["goods_no"]}) 저장응답 성공')
                    else:
                        summary['failed'] += 1
                        failed_targets.append(t)
                        _log(log_fn, f'  ❌ {t["product_no"]}(goods_no={t["goods_no"]}) 실패 — 패스')
                        _log_failure(f'[{login_id}] {t["product_no"]}(goods_no={t["goods_no"]}) 타겟실행 실패')
                    time.sleep(_PACE_SEC)

                if http_ok:
                    driver.switch_to.default_content()
                    driver.get('https://www.esmplus.com/Home/v2/goods-manage')
                    time.sleep(1.5)
                    _enter_goods_iframe(driver)
                    pnos = [t['product_no'] for t in http_ok]
                    recheck = _lookup_disp_end_dates(driver, pnos, log_fn)
                    _save_status(acct, recheck, log_fn)
                    for t in http_ok:
                        rm = recheck.get(t['product_no'], {})
                        ok_state = rm.get('dispEndDate', '').startswith(_UNLIMITED_YEAR) if only_period else \
                            not _needs_fix({'dispEndDate': rm.get('dispEndDate', ''), 'discount_type': rm.get('discount_type')})
                        if ok_state:
                            summary['verified'] += 1
                        else:
                            summary['verify_mismatch'] += 1
                            failed_targets.append(t)
                            _log_failure(f'[{login_id}] {t["product_no"]} 재조회 불일치(타겟실행)')

                more_left = idx < len(items)
                if more_left:
                    _log(log_fn, f'  ↻ {_LOCK_CYCLE}건 처리 — 락 반납 후 재획득 대기')
                    _release()
                    time.sleep(3)
                    if not _acquire():
                        for t in items[idx:]:
                            failed_targets.append(t)
                        break
                    try:
                        login_ok = _login(acct)
                    except Exception:
                        login_ok = False
                    if not login_ok:
                        for t in items[idx:]:
                            failed_targets.append(t)
                        break

            _release()

        _log(log_fn, f'타겟실행 완료 — {summary} / 실패(재시도대상) {len(failed_targets)}건')
        return {'ok': True, **summary, 'failed_targets': failed_targets}
    finally:
        if lock_held or driver:
            _release()
        stop_display()

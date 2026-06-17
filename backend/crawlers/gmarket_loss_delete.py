"""지마켓(ESM) 적자상품 자동 판매중지·삭제 — 11번가(eleven_loss_delete) 미러링.
플로우(사용자 제공 셀렉터): 상품관리 iframe → 상품번호 textarea 입력(★입력확인 필수)
→ 조회 → 전체선택 → '판매 상태 변경'→판매중지 → 재조회 → 삭제 → 잔여검증.

안전: 기본 validate(검증, 파괴적 클릭 없음). real은 셀러오피스 삭제 플로우 검증 후 활성화.
:r3:/:r19: 같은 React 동적 id는 신뢰 못 하므로 absolute path + 텍스트 폴백 사용."""
import json
import time

from selenium.webdriver.common.by import By

GOODS_MANAGE = 'https://www.esmplus.com/Home/v2/goods-manage'

# 사용자 제공 + 폴백 셀렉터 (iframe[0] 컨텍스트 기준)
XP_TEXTAREA = ['/html/body/div/main/div[4]/div[1]/div[2]/div/textarea']
XP_SEARCH = ['/html/body/div/main/div[4]/div[8]/button[2]',
             "//button[normalize-space()='조회' or normalize-space()='검색']"]
XP_SELECT_ALL = ['/html/body/div/main/div[5]/div[2]/div[1]//input[@type="checkbox"]',
                 '//thead//input[@type="checkbox"]']
XP_STATUS_CHANGE = ['/html/body/div/main/div[5]/div[2]/div[1]/div[1]/div[1]/button',
                    "//button[contains(.,'판매 상태 변경') or contains(.,'판매상태')]"]
XP_STOPSELL = ["//button[normalize-space()='판매중지']", "//a[normalize-space()='판매중지']",
               "//*[@role='menuitem'][contains(.,'판매중지')]", "//li[contains(.,'판매중지')]"]
XP_DELETE = ["//button[normalize-space()='삭제']", "//a[normalize-space()='삭제']"]
XP_CONFIRM = ["//button[normalize-space()='확인' or normalize-space()='예' or normalize-space()='네']",
              "//a[normalize-space()='확인' or normalize-space()='예']"]


def _log(fn, m):
    if fn:
        fn(m)


def _find(driver, xpaths, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        for xp in xpaths:
            els = [e for e in driver.find_elements(By.XPATH, xp) if e.is_displayed()]
            if els:
                return els[0], xp
        time.sleep(0.3)
    return None, None


def _click(driver, xpaths, label, log_fn, timeout=6):
    el, xp = _find(driver, xpaths, timeout)
    if not el:
        _log(log_fn, f'  ❌ {label} 버튼 못찾음')
        return False
    try:
        driver.execute_script("arguments[0].click();", el)
        _log(log_fn, f'  ✅ {label} 클릭 ({xp[:40]})')
        return True
    except Exception as e:
        _log(log_fn, f'  ❌ {label} 클릭 예외: {e}')
        return False


def _enter_goods_iframe(driver):
    driver.get(GOODS_MANAGE)
    time.sleep(9)
    frames = driver.find_elements(By.TAG_NAME, 'iframe')
    if frames:
        driver.switch_to.frame(frames[0])
        return True
    return False


def _clear_popups(driver, log_fn, rounds=4):
    """판매중지/삭제 확인창 자동 처리 — JS alert accept + '확인/예'만 클릭(취소/닫기 금지)."""
    for _ in range(rounds):
        try:
            al = driver.switch_to.alert
            txt = al.text[:60]
            al.accept()
            _log(log_fn, f'  alert 확인: "{txt}"')
            time.sleep(0.5)
            continue
        except Exception:
            pass
        el, _ = _find(driver, XP_CONFIRM, timeout=2)
        if el:
            try:
                driver.execute_script("arguments[0].click();", el)
                _log(log_fn, '  모달 "확인" 클릭')
                time.sleep(0.6)
            except Exception:
                break
        else:
            break


def _paste_and_search(driver, nums, log_fn):
    """상품번호 textarea 입력 + ★입력확인 + 조회. 반환: (성공여부, 입력검증통과여부)."""
    ta, _ = _find(driver, XP_TEXTAREA, timeout=8)
    if not ta:
        tas = driver.find_elements(By.TAG_NAME, 'textarea')
        ta = tas[0] if tas else None
    if not ta:
        _log(log_fn, '  ❌ 상품번호 입력칸(textarea) 못찾음')
        return False, False
    joined = '\n'.join(str(n) for n in nums)
    try:
        ta.clear()
    except Exception:
        pass
    ta.send_keys(joined)
    time.sleep(1)
    val = ta.get_attribute('value') or ''
    # ★ 입력 확인: 모든 상품번호가 입력칸에 들어갔는지 검증 (안 들어갔으면 중단)
    missing = [str(n) for n in nums if str(n) not in val]
    if missing:
        _log(log_fn, f'  ❌ 상품번호 입력 누락 {len(missing)}개 → 중단(안전). 예:{missing[:3]}')
        return False, False
    _log(log_fn, f'  ★ 상품번호 입력 확인 OK ({len(nums)}개)')
    if not _click(driver, XP_SEARCH, '조회', log_fn):
        return False, True
    time.sleep(6)
    return True, True


def _result_count(driver):
    """검색결과 행수 — 가상그리드라 입력번호 등장수로 근사(정확 셀렉터는 추후 보강)."""
    try:
        rows = driver.find_elements(By.XPATH, "//table//tbody//tr")
        return len(rows)
    except Exception:
        return -1


def run_delete(targets, mode='validate', log_fn=None):
    """targets: [{login_id, product_no, seller_code, status}]. mode: validate(기본) | real."""
    from apps.cpc.models import CrawlerAccount, GmarketLossDeleted
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver
    from crawlers.gmarket_cost_crawler import _esm_login

    # 계정별 묶기
    by_acc = {}
    for t in targets:
        by_acc.setdefault(t['login_id'], []).append(t)

    ok, reason = guard.preflight('지마켓적자삭제', platform='gmarket')
    if not ok:
        _log(log_fn, f'⛔ preflight 차단: {reason}')
        return {'ok': False, 'skipped': reason}

    summary = {'accounts': 0, 'deleted': 0, 'marked': 0, 'failed': 0}
    results = []
    try:
        for eid, items in by_acc.items():
            nums = []
            seen = set()
            for t in items:
                p = ''.join(ch for ch in str(t.get('product_no', '')) if ch.isdigit())
                if p and p not in seen:
                    seen.add(p)
                    nums.append(p)
            if not nums:
                continue
            _log(log_fn, f'[{eid}] 대상 {len(nums)}개 (판매중지→재조회→삭제) mode={mode}')
            acc = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
            if not acc:
                summary['failed'] += 1
                continue
            d = None
            try:
                d = create_driver(kill_existing=False)
                d.set_page_load_timeout(45)
                # 쿠키 우선 로그인(캡차 회피)
                if acc.cookie_data:
                    try:
                        d.get('https://www.esmplus.com/'); time.sleep(2)
                        for c in json.loads(acc.cookie_data):
                            c.pop('sameSite', None)
                            try: d.add_cookie(c)
                            except Exception: pass
                        d.get('https://www.esmplus.com/'); time.sleep(2)
                    except Exception:
                        pass
                if not _esm_login(d, eid, acc.password_enc or ''):
                    _log(log_fn, f'[{eid}] ❌ 로그인 실패(캡차 가능) — 건너뜀')
                    summary['failed'] += 1
                    continue
                if not _enter_goods_iframe(d):
                    _log(log_fn, f'[{eid}] ❌ 상품관리 iframe 진입 실패')
                    summary['failed'] += 1
                    continue

                # === 1) 판매중지: 입력+확인 → 조회 → 전체선택 → 판매상태변경→판매중지 ===
                okp, verified = _paste_and_search(d, nums, log_fn)
                if not verified:
                    summary['failed'] += 1
                    continue
                cnt = _result_count(d)
                _log(log_fn, f'  조회 결과행(근사): {cnt}')
                if mode == 'validate':
                    sa, _ = _find(d, XP_SELECT_ALL, 3)
                    sc, _ = _find(d, XP_STATUS_CHANGE, 3)
                    de, _ = _find(d, XP_DELETE, 3)
                    _log(log_fn, f'  [validate] 전체선택:{"O" if sa else "X"} 판매상태변경:{"O" if sc else "X"} 삭제:{"O" if de else "X"} — 클릭 안함')
                    results.append({'login_id': eid, 'validated': True, 'rows': cnt})
                    summary['accounts'] += 1
                    continue

                # ---- real 모드 (파괴적) ----
                _click(d, XP_SELECT_ALL, '전체선택', log_fn)
                time.sleep(1)
                if _click(d, XP_STATUS_CHANGE, '판매 상태 변경', log_fn):
                    time.sleep(1)
                    _click(d, XP_STOPSELL, '판매중지', log_fn)
                    _clear_popups(d, log_fn)
                    time.sleep(2)

                # === 2) 재조회 → 전체선택 → 삭제 ===
                okp2, _ = _paste_and_search(d, nums, log_fn)
                _click(d, XP_SELECT_ALL, '전체선택(삭제전)', log_fn)
                time.sleep(1)
                if _click(d, XP_DELETE, '삭제', log_fn):
                    _clear_popups(d, log_fn)
                    time.sleep(2)

                # === 3) 잔여검증: 재조회해서 0이면 성공 ===
                _paste_and_search(d, nums, log_fn)
                remaining = _result_count(d)
                deleted_ok = (remaining == 0)
                _log(log_fn, f'  잔여검증: {remaining}행 → 삭제{"성공" if deleted_ok else "미완(보류)"}')
                if deleted_ok:
                    for t in items:
                        pn = ''.join(ch for ch in str(t.get('product_no', '')) if ch.isdigit())
                        if pn:
                            GmarketLossDeleted.objects.get_or_create(
                                login_id=eid, product_no=pn,
                                defaults={'seller_code': t.get('seller_code') or ''})
                            summary['marked'] += 1
                    summary['deleted'] += len(nums)
                results.append({'login_id': eid, 'deleted': deleted_ok, 'remaining': remaining})
                summary['accounts'] += 1
            finally:
                if d:
                    try: d.quit()
                    except Exception: pass
                guard.is_blocked()  # 상태 갱신
    finally:
        try:
            guard.release_global_lock(platform='gmarket')
        except Exception:
            pass

    label = 'VALIDATE(검증)' if mode == 'validate' else '실삭제'
    msg = (f'🗑 [지마켓 적자삭제 {label} 완료] (판매중지→재조회→삭제)\n'
           f'계정 {summary["accounts"]} / 삭제완료 {summary["deleted"]} / '
           f'비고기록 {summary["marked"]} / 실패 {summary["failed"]}')
    _log(log_fn, msg)
    try:
        from apps.cpc import eleven_block_guard as guard2
        guard2._send_telegram_alert(msg)
    except Exception:
        pass
    return {'ok': True, 'mode': mode, **summary, 'results': results}

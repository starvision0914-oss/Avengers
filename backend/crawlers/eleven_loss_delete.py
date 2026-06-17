"""적자상품 자동 판매중지·삭제 (셀러오피스 상품조회/수정 /view/8006 일괄처리).

계정별 1회 로그인 → /view/8006 진입 후 적자 상품번호를 '숫자만' 일괄 검색해 처리:
  1단계) 판매금지 상품  : 검색 → 전체선택 → 선택상품 삭제
  2단계) 판매중/판매중지/품절 : 검색 → 전체선택 → 판매중지 → 선택상품 삭제
모달/팝업 자동 해제, 잔여 상품 재삭제, 삭제분은 비고('삭제완료', St11LossDeleted) 기록.

셀렉터: 사용자 제공 xpath를 1순위로 시도하되, jqWidgets/ExtJS 자동생성 ID(jqxWidget*, ext-gen*)는
세션마다 바뀌므로 텍스트 기반 폴백을 함께 둔다.

안전:
- 전역 단일락(preflight) — 동시 크롤 금지.
- mode='validate'(기본): 검색/전체선택까지만 하고 판매중지·삭제 클릭은 하지 않음(셀렉터 검증용).
- mode='real': 실제 판매중지·삭제 수행(되돌릴 수 없음).
"""
import logging
import re
import time

logger = logging.getLogger('crawler')

SOFFICE = 'https://soffice.11st.co.kr'
PRODUCT_PAGE = f'{SOFFICE}/view/8006'
# 상품관리 UI는 이 iframe 안에 있음 (라이브 확인 2026-06-09)
IFRAME_ID = 'Content_ifrm_8006'

REST_STATUSES = ('판매중', '판매중지', '품절')   # 2단계: 판매중지 후 삭제
BANNED_STATUS = '판매금지'                          # 1단계: 바로 삭제

# 사용자 제공 셀렉터(1순위) + 폴백
XP_PRDNO = ['//*[@id="prdNo"]']
XP_SEARCH = ['//*[@id="btnSearch"]/span/span', '//*[@id="btnSearch"]']
XP_SELECTALL = [
    '//*[@id="jqxWidgetd0651191"]/div/div',                              # 사용자 제공
    "//div[contains(@class,'jqx-grid-column-header')]//div[contains(@class,'jqx-checkbox')]",
    "(//div[contains(@class,'jqx-grid-header')]//div[contains(@class,'jqx-checkbox')])[1]",
    "//thead//input[@type='checkbox']",
    "(//input[@type='checkbox'][contains(@id,'ll') or contains(@id,'All') or contains(@onclick,'all') or contains(@onclick,'All')])[1]",
    "(//th//input[@type='checkbox'])[1]",
]
XP_STOPSELL = [
    '//*[@id="ext-gen1019"]/div[3]/div[1]/div[5]/div/a[1]/span',         # 사용자 제공
    "//a[normalize-space(.)='판매중지']",
    "//span[normalize-space(text())='판매중지']/ancestor::a[1]",
    "//button[normalize-space(.)='판매중지']",
]
XP_DELETE = [
    '//*[@id="ext-gen1019"]/div[3]/div[1]/div[5]/div/a[12]/span',        # 사용자 제공
    "//a[normalize-space(.)='선택상품삭제']",
    "//a[contains(normalize-space(.),'선택상품') and contains(normalize-space(.),'삭제')]",
    "//span[contains(normalize-space(.),'선택상품') and contains(normalize-space(.),'삭제')]/ancestor::a[1]",
    "//a[normalize-space(.)='삭제']",
]
# 결과 그리드 행 카운트 후보
XP_GRID_ROWS = [
    "//div[contains(@class,'jqx-grid-content')]//div[@role='row']",
    "//div[contains(@class,'jqx-grid-content')]/div/div[@role='row']",
]


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def _timed(log_fn, eid, label, fn):
    """fn()을 실행하고 소요시간(초)을 로그. 어느 구간이 오래 걸리는지 추적용."""
    t0 = time.time()
    try:
        return fn()
    finally:
        _log(log_fn, f'  ⏱ [{eid}] {label}: {time.time() - t0:.1f}s')


def _focus_frame(driver):
    """상품관리 iframe(Content_ifrm_8006)으로 포커스 이동. 검색/삭제 후 재진입에도 사용."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    driver.switch_to.default_content()
    try:
        WebDriverWait(driver, 12).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, IFRAME_ID)))
        return True
    except Exception:
        return False


def _find(driver, xpaths, timeout=8):
    """xpath 목록을 순서대로 시도해 처음 보이는 요소를 반환. (xpath, element) 또는 (None, None)."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    deadline_each = max(1, timeout // max(1, len(xpaths)))
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, deadline_each).until(
                EC.presence_of_element_located((By.XPATH, xp)))
            return xp, el
        except Exception:
            continue
    return None, None


def _digits_only(targets):
    """상품번호에서 숫자만 추출. 숫자가 아닌 항목은 제외, 중복 제거(순서 유지)."""
    seen, out = set(), []
    for t in targets:
        d = re.sub(r'\D', '', str(t.get('product_no', '')))
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _grid_rowcount(driver):
    from selenium.webdriver.common.by import By
    for xp in XP_GRID_ROWS:
        try:
            n = len(driver.find_elements(By.XPATH, xp))
            if n:
                return n
        except Exception:
            pass
    return 0


def _paste_and_search(driver, nums, log_fn, eid):
    """prdNo에 숫자만 줄바꿈으로 붙여넣고 검색 실행. 검색 후 그리드 행수 반환."""
    _focus_frame(driver)
    xp, el = _find(driver, XP_PRDNO, 10)
    if not el:
        _log(log_fn, f'  [{eid}] ⚠️ 상품번호 입력칸(prdNo) 미발견')
        return None
    val = '\n'.join(nums)   # 숫자만, 줄바꿈 구분
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        el.clear()
    except Exception:
        pass
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", el, val)
    sxp, sbtn = _find(driver, XP_SEARCH, 8)
    if not sbtn:
        _log(log_fn, f'  [{eid}] ⚠️ 검색버튼(btnSearch) 미발견')
        return None
    driver.execute_script("arguments[0].click();", sbtn)
    time.sleep(3)
    rows = _grid_rowcount(driver)
    _log(log_fn, f'  [{eid}] 검색 {len(nums)}건 입력 → 그리드 {rows}행')
    return rows


def _select_all(driver, log_fn, eid):
    _focus_frame(driver)
    xp, el = _find(driver, XP_SELECTALL, 8)
    if not el:
        _log(log_fn, f'  [{eid}] ⚠️ 전체선택 체크박스 미발견')
        return False
    driver.execute_script("arguments[0].click();", el)
    time.sleep(1)
    return True


def _click(driver, xpaths, label, log_fn, eid):
    xp, el = _find(driver, xpaths, 8)
    if not el:
        _log(log_fn, f'  [{eid}] ⚠️ "{label}" 버튼 미발견')
        return False
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    driver.execute_script("arguments[0].click();", el)
    _log(log_fn, f'  [{eid}] "{label}" 클릭')
    time.sleep(1.5)
    return True


XP_MODAL = ("//*[contains(@class,'layer') or contains(@class,'modal') or contains(@class,'popup') "
            "or contains(@class,'dialog') or @role='dialog']")
# 확인/진행(긍정) 버튼만 — '닫기/취소'는 누르면 작업이 취소되므로 절대 클릭 금지
XP_CONFIRM = [
    "//*[contains(@class,'layer') or contains(@class,'modal') or contains(@class,'popup') or contains(@class,'dialog') or @role='dialog']"
    "//*[(self::button or self::a) and (normalize-space()='확인' or normalize-space()='예' or normalize-space()='네')]",
    "//button[normalize-space()='확인' or normalize-space()='예' or normalize-space()='네']",
    "//a[normalize-space()='확인' or normalize-space()='예' or normalize-space()='네']",
]


def _clear_popups(driver, eid, log_fn=None):
    """판매중지/삭제 확인창 처리 — JS alert는 accept, DOM 모달은 '확인/예'만 클릭(닫기/취소 금지).
    어떤 모달이 떴는지 텍스트를 로그로 남겨 진단에 활용."""
    from selenium.webdriver.common.by import By
    from crawlers.eleven_crawler import _drain_alerts
    n = 0
    for _ in range(4):
        # 1) 브라우저 JS alert/confirm — accept(=확인)
        n += _drain_alerts(driver, login_id=eid)
        # 2) DOM 레이어 모달 — 내용 로깅 + '확인/예'만 클릭
        try:
            modals = [m for m in driver.find_elements(By.XPATH, XP_MODAL) if m.is_displayed() and (m.text or '').strip()]
        except Exception:
            modals = []
        if modals:
            txt = ' | '.join((m.text or '').strip().replace('\n', ' ')[:80] for m in modals[:2])
            _log(log_fn, f'  [{eid}] 모달 감지: "{txt[:160]}"')
        clicked = False
        for xp in XP_CONFIRM:
            try:
                for b in driver.find_elements(By.XPATH, xp):
                    if b.is_displayed():
                        driver.execute_script("arguments[0].click();", b)
                        n += 1
                        clicked = True
                        _log(log_fn, f'  [{eid}] 모달 "{(b.text or "").strip()[:20]}" 클릭')
                        time.sleep(0.6)
                        break
            except Exception:
                pass
            if clicked:
                break
        if not modals and not clicked:
            break   # 더 닫을 모달 없음
        time.sleep(0.5)
    return n


def _process_group(driver, nums, stopsell_nums, mode, log_fn, eid, max_retry=2):
    """한 그룹 일괄처리.
    nums        : 삭제 대상 전체 상품번호(숫자만). 검색→전체선택→삭제.
    stopsell_nums: 판매중지 대상(=판매중 상태만). None이면 판매중지 단계 생략(판매금지 그룹).
                   판매중만 검색해 전체선택→판매중지 → 이미 판매중지/품절 항목에 뜨는 오류모달 회피.
    validate면 파괴적 클릭 없이 셀렉터/상태만 확인.
    반환: {'searched','selectall','stopsell_btn','delete_btn','deleted','remaining'}"""
    res = {'searched': None, 'selectall': False, 'stopsell_btn': None, 'delete_btn': None,
           'deleted': False, 'remaining': None}

    if mode == 'validate':
        rows = _timed(log_fn, eid, 'paste+search', lambda: _paste_and_search(driver, nums, log_fn, eid))
        res['searched'] = rows
        if rows is None:
            return res
        # 검색결과는 이미 전체체크 상태 → select_all 누르지 않음(누르면 해제됨)
        if stopsell_nums is not None:
            _log(log_fn, f'  [{eid}] (validate) 판매중지 대상(판매중) {len(stopsell_nums)}개')
            sxp, _e = _timed(log_fn, eid, 'find 판매중지', lambda: _find(driver, XP_STOPSELL, 6))
            res['stopsell_btn'] = sxp
            _log(log_fn, f'  [{eid}] (validate) 판매중지 버튼: {"OK " + sxp if sxp else "미발견"}')
        dxp, _e = _timed(log_fn, eid, 'find 삭제', lambda: _find(driver, XP_DELETE, 6))
        res['delete_btn'] = dxp
        _log(log_fn, f'  [{eid}] (validate) 삭제 버튼: {"OK " + dxp if dxp else "미발견"}')
        return res

    # ── real ──
    # ⚠️ 검색결과 그리드는 '전체 체크된 상태'로 표시됨 → select_all을 누르면 오히려 해제됨("선택된 항목 없음").
    #    따라서 select_all은 누르지 않고, 검색 직후(체크된 상태) 바로 판매중지/삭제 클릭한다.
    # 1) 판매중지: '판매중' 상품번호만 검색 → (이미 전체체크) → 판매중지
    if stopsell_nums:
        _log(log_fn, f'  [{eid}] [1단계] 판매중 {len(stopsell_nums)}개 판매중지')
        r1 = _timed(log_fn, eid, 'paste+search(판매중)', lambda: _paste_and_search(driver, stopsell_nums, log_fn, eid))
        if r1:
            if _timed(log_fn, eid, 'click 판매중지', lambda: _click(driver, XP_STOPSELL, '판매중지', log_fn, eid)):
                res['stopsell_btn'] = 'clicked'
                _timed(log_fn, eid, 'popups(판매중지후)', lambda: _clear_popups(driver, eid, log_fn))
                time.sleep(2)
    elif stopsell_nums is not None:
        _log(log_fn, f'  [{eid}] 판매중 상품 없음 — 판매중지 생략')

    # 2) 삭제: 전체(판매중·판매중지·품절) 검색 → (이미 전체체크) → 선택상품삭제
    _log(log_fn, f'  [{eid}] [2단계] 전체 {len(nums)}개 삭제')
    rows = _timed(log_fn, eid, 'paste+search(삭제)', lambda: _paste_and_search(driver, nums, log_fn, eid))
    res['searched'] = rows
    if rows:
        if _timed(log_fn, eid, 'click 삭제', lambda: _click(driver, XP_DELETE, '선택상품삭제', log_fn, eid)):
            res['delete_btn'] = 'clicked'
            _timed(log_fn, eid, 'popups(삭제후)', lambda: _clear_popups(driver, eid, log_fn))
            time.sleep(2)

    # 3) 잔여 검증 후 재삭제 (select_all 없이) — 실제 잔여 0일 때만 삭제 성공으로 인정
    remaining = rows or 0
    for i in range(max_retry):
        r = _timed(log_fn, eid, f'잔여검증{i + 1}', lambda: _paste_and_search(driver, nums, log_fn, eid))
        remaining = r or 0
        if not r:
            break
        _log(log_fn, f'  [{eid}] 잔여 {r}행 → 재삭제 {i + 1}회')
        _click(driver, XP_DELETE, '선택상품삭제(재)', log_fn, eid)
        _clear_popups(driver, eid, log_fn)
        time.sleep(2)
    res['remaining'] = remaining
    res['deleted'] = (remaining == 0)   # 클릭 여부가 아니라 '잔여 0' 검증으로 성공 판정 → 잘못된 비고기록 방지
    return res


def _mark_deleted(eid, targets):
    """삭제한 상품을 St11LossDeleted에 기록 → 비고 '삭제완료'."""
    from apps.cpc.models import St11LossDeleted
    marked = 0
    for t in targets:
        p = re.sub(r'\D', '', str(t.get('product_no', '')))
        if not p:
            continue
        St11LossDeleted.objects.get_or_create(
            eleven_id=eid, product_no=p,
            defaults={'seller_code': t.get('seller_code') or ''})
        marked += 1
    return marked


def run_delete(targets, mode='validate', eid_filter=None, log_fn=None):
    """targets: [{'eleven_id','product_no','seller_code','status'}...].
    mode: 'validate'(기본, 파괴적 클릭 없음) | 'real'(실삭제).
    eid_filter: 특정 계정만 처리(테스트)."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.eleven_crawler import _do_login, _drain_alerts
    from crawlers.browser import create_driver, stop_display

    if mode not in ('validate', 'real'):
        mode = 'validate'

    ok, reason = guard.preflight('적자삭제')
    if not ok:
        _log(log_fn, f'⏭️ 적자삭제 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    # 계정별 그룹화 (계정 정렬 + 계정 내 상품번호 정렬)
    grouped = {}
    for t in targets:
        eid = t['eleven_id']
        if eid_filter and eid != eid_filter:
            continue
        grouped.setdefault(eid, []).append(t)
    by_acc = {eid: sorted(grouped[eid], key=lambda x: str(x['product_no']))
              for eid in sorted(grouped.keys())}

    pw_map = {a.login_id: a.password_enc for a in CrawlerAccount.objects.filter(platform='11st')}
    summary = {'accounts': 0, 'banned_done': 0, 'rest_done': 0, 'marked': 0, 'failed': 0}
    results = []
    try:
        for eid, items in by_acc.items():
            blocked, _, _ = guard.is_blocked()
            if blocked:
                _log(log_fn, '⛔ 차단 감지 — 중단')
                break
            all_nums = _digits_only(items)   # 상태 무관 전체 대상(판매금지·판매중·판매중지·품절 모두)
            _log(log_fn, f'[{eid}] 로그인 시도 — 대상 {len(all_nums)}개 (전부 판매중지 → 재조회 → 삭제) (mode={mode})')
            if not all_nums:
                _log(log_fn, f'[{eid}] 처리할 숫자 상품번호 없음 — 건너뜀')
                continue
            driver = None
            acc = {'eleven_id': eid, 'all': None}
            try:
                driver = create_driver(kill_existing=False)
                t_login = time.time()
                sn = _do_login(driver, eid, pw_map.get(eid, ''))
                _log(log_fn, f'  ⏱ [{eid}] 로그인: {time.time() - t_login:.1f}s')
                if not sn:
                    _log(log_fn, f'[{eid}] 로그인 실패 — 건너뜀')
                    summary['failed'] += 1
                    continue
                # 삭제 플로우는 짧은 명시적 대기(_find)로 제어 → 암묵적 대기(10s) 끄기.
                # (안 끄면 폴백 셀렉터마다 10초씩 누적되어 수백초로 폭증)
                driver.implicitly_wait(0)
                driver.set_page_load_timeout(30)
                _drain_alerts(driver, login_id=eid)
                t_nav = time.time()
                driver.get(PRODUCT_PAGE)
                time.sleep(3)
                _log(log_fn, f'[{eid}] 상품조회 페이지 접속 ({time.time() - t_nav:.1f}s, title="{(driver.title or "")[:30]}")')

                # 전체(판매금지 포함)를 판매중지 먼저 → 같은 상품번호로 재조회 → 삭제.
                # stopsell_nums=nums=all_nums 이므로 _process_group이 '판매중지 검색·클릭 → 재검색 → 삭제'를 수행.
                acc['all'] = _process_group(driver, all_nums, all_nums,
                                            mode=mode, log_fn=log_fn, eid=eid)
                if mode == 'real' and acc['all'].get('deleted'):
                    summary['rest_done'] += len(all_nums)

                if mode == 'real':
                    done_targets = items if (acc['all'] and acc['all'].get('deleted')) else []
                    if done_targets:
                        summary['marked'] += _mark_deleted(eid, done_targets)
                summary['accounts'] += 1
            except Exception as e:
                _log(log_fn, f'[{eid}] 오류: {str(e)[:140]}')
                summary['failed'] += 1
            finally:
                try:
                    if driver:
                        driver.quit()
                except Exception:
                    pass
                results.append(acc)
            time.sleep(3)   # 계정 간 페이싱
    finally:
        guard.release_global_lock()
        try:
            stop_display()
        except Exception:
            pass

    label = 'VALIDATE(검증)' if mode == 'validate' else '실삭제'
    msg = (f'🗑 [적자삭제 {label} 완료] (전부 판매중지→재조회→삭제)\n'
           f'계정 {summary["accounts"]} / 삭제완료 {summary["rest_done"]} / '
           f'비고기록 {summary["marked"]} / 실패 {summary["failed"]}')
    _log(log_fn, msg)
    try:
        guard._send_telegram_alert(msg)
    except Exception:
        pass
    return {'ok': True, 'mode': mode, **summary, 'results': results}

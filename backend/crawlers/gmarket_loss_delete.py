"""지마켓(ESM) 적자상품 자동 판매중지·삭제 — 11번가(eleven_loss_delete) 미러링.
플로우(사용자 제공 셀렉터): 상품관리 iframe → 상품번호 textarea 입력(★입력확인 필수)
→ 조회 → 전체선택 → '판매 상태 변경'→판매중지 → 재조회 → 삭제 → 잔여검증.

안전: 기본 validate(검증, 파괴적 클릭 없음). real은 셀러오피스 삭제 플로우 검증 후 활성화.
:r3:/:r19: 같은 React 동적 id는 신뢰 못 하므로 absolute path + 텍스트 폴백 사용."""
import json
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

GOODS_MANAGE = 'https://www.esmplus.com/Home/v2/goods-manage'

# 사용자 제공 + 폴백 셀렉터 (iframe[0] 컨텍스트 기준)
XP_TEXTAREA = ['/html/body/div/main/div[4]/div[1]/div[2]/div/textarea']
XP_SEARCH = ['/html/body/div/main/div[4]/div[8]/button[2]',
             "//button[normalize-space()='조회' or normalize-space()='검색']"]
XP_SELECT_ALL = ['/html/body/div/main/div[5]/div[2]/div[1]//input[@type="checkbox"]',
                 '//thead//input[@type="checkbox"]']
XP_STATUS_CHANGE = ['/html/body/div/main/div[5]/div[2]/div[1]/div[1]/div[1]/button',
                    "//button[contains(.,'판매 상태 변경') or contains(.,'판매상태')]"]
XP_STOPSELL = ['/html/body/div/main/div[5]/div[2]/div[1]/div[1]/div[1]/ul/li[2]/button',
               "//button[normalize-space()='판매중지']", "//a[normalize-space()='판매중지']",
               "//*[@role='menuitem'][contains(.,'판매중지')]"]
# (2026-08-24: 기존 마지막 폴백 "//li[contains(.,'판매중지')]"는 실제로는 왼쪽 사이드바의
#  '상태별 필터' 항목(판매중지 N건 카운트)을 잘못 매칭해왔음 — 진짜 액션 버튼이 아니라서
#  클릭 로그는 매번 성공으로 찍혔지만 실제 판매상태는 전혀 안 바뀌던 원인. 사용자가 VNC로
#  화면 직접 보고 확인해준 절대경로로 교체, 그 li[contains] 폴백은 위험해서 제거.
XP_DELETE = ["//button[normalize-space()='삭제']", "//a[normalize-space()='삭제']"]
XP_CONFIRM = ["//button[normalize-space()='확인' or normalize-space()='예' or normalize-space()='네']",
              "//a[normalize-space()='확인' or normalize-space()='예']"]
# 2026-08-24 발견(사용자와 VNC로 직접 실측): 판매중지 옵션을 고르는 것만으로는 변경이 반영 안 됨 —
# 별도로 이 "변경"(파란 큰 버튼)을 눌러야 실제 커밋됨. 이걸 안 눌러서 여태 클릭 로그는 '성공'인데
# 실제 사이트 반영은 0건이었던 게 근본 원인. 클릭 후 "N건 처리 완료" 결과 모달이 뜬다.
XP_APPLY_CHANGE = ["//button[normalize-space()='변경' and contains(@class,'button--xxlarge')]",
                    "//button[normalize-space()='변경']"]


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


def _cdp_click(driver, el):
    """CDP로 네이티브 마우스 이벤트(mousePressed/mouseReleased)를 요소 중심 좌표에 직접 주입.
    ActionChains(move_to_element)는 W3C 액션 좌표계산이 뷰포트 경계를 벗어났다고 종종 오판해
    'move target out of bounds'로 실패함(2026-08-24 ESM 판매중지에서 실측) — CDP는 그 사전검사가
    없어 getBoundingClientRect로 구한 실제 좌표에 그대로 이벤트를 꽂아넣어 더 안정적임.
    isTrusted=true인 진짜 브라우저 입력이라 execute_script 합성클릭과 달리 React 핸들러가 반응함."""
    rect = driver.execute_script(
        "var r=arguments[0].getBoundingClientRect();return [r.left+r.width/2, r.top+r.height/2];", el)
    x, y = rect[0], rect[1]
    driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
        'type': 'mouseMoved', 'x': x, 'y': y})
    driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
        'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
    driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
        'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})


_GOODS_LOOKUP_JS = (
    "var cb=arguments[arguments.length-1];var ids=arguments[0];"
    "fetch('/api/ea/goods/search',{method:'POST',credentials:'include',"
    "headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({query:{goodsIds:ids,keyword:'',sellStatus:[],category:{},"
    "registrationDate:{},shipping:{},additionalService:[]},pageIndex:1,pageSize:200,"
    "sortField:0,sortOrder:1})})"
    ".then(function(r){return r.text();}).then(function(t){cb(t);}).catch(function(e){cb('ERR:'+e);});"
)

_SET_SELL_STATUS_JS = (
    "var cb=arguments[arguments.length-1];var gid=arguments[0];var market=arguments[1];"
    "var sg=arguments[2];var sa=arguments[3];"
    "var body={isSell:{}};body.isSell[market]=false;"
    "fetch('/api/ea/goods/'+gid+'/sellStatus',{method:'PUT',credentials:'include',"
    "headers:{'Content-Type':'application/json','X-G-SELLER-ID':sg,'X-A-SELLER-ID':sa},"
    "body:JSON.stringify(body)})"
    ".then(function(r){return r.text().then(function(t){cb(JSON.stringify({status:r.status,text:t}));});})"
    ".catch(function(e){cb(JSON.stringify({status:0,text:String(e)}));});"
)


def _lookup_goods_by_pno(driver, product_nos, log_fn=None):
    """product_no(사이트별 상품번호) 목록 → {product_no: {goods_no, market_key, seller_g, seller_a}}.
    (2026-08-24) '/api/ea/goods/search'를 goodsIds로 필터링해 조회 — 화면 클릭 없이 즉시 응답,
    같은 API를 나의상품 검증에도 이미 재사용 중이라 신뢰도 확인됨."""
    want = {str(p) for p in product_nos}
    result = {}
    ids = ','.join(want)
    try:
        txt = driver.execute_async_script(_GOODS_LOOKUP_JS, ids)
    except Exception as e:
        _log(log_fn, f'  ❌ goodsNo 조회 예외: {e}')
        return result
    try:
        data = json.loads(txt).get('data') or {}
    except Exception:
        _log(log_fn, f'  ❌ goodsNo 조회 파싱 실패: {str(txt)[:150]}')
        return result
    for it in data.get('items') or []:
        goods_no = it.get('goodsNo')
        site_no = it.get('siteGoodsNo') or {}
        site_seller = it.get('siteSellerId') or {}
        for site in ('gmkt', 'iac'):
            pno = site_no.get(site)
            if pno and str(pno) in want:
                result[str(pno)] = {
                    'goods_no': goods_no, 'market_key': site,
                    'seller_g': site_seller.get('gmkt') or '',
                    'seller_a': site_seller.get('iac') or '',
                }
    return result


def _api_suspend_products(driver, product_nos, log_fn=None):
    """UI 클릭(검색→선택→상태변경→판매중지→변경) 없이 API로 직접 판매중지.
    (2026-08-24) 여러 계정을 연속 처리할 때 화면 클릭 방식이 불안정(체크박스/변경버튼을
    못 찾는 경우 빈발)해 API 방식으로 교체. 실제 사이트에 반영 성공한 product_no만 반환
    (HTTP 200/204만 성공으로 인정 — 낙관적 가정 금지)."""
    info = _lookup_goods_by_pno(driver, product_nos, log_fn)
    ok = []
    for pno in product_nos:
        meta = info.get(str(pno))
        if not meta:
            _log(log_fn, f'  ⚠ {pno} 검색 안 됨(삭제됐거나 이미 다른 상태일 수 있음)')
            continue
        try:
            txt = driver.execute_async_script(
                _SET_SELL_STATUS_JS, meta['goods_no'], meta['market_key'],
                meta['seller_g'], meta['seller_a'])
            r = json.loads(txt)
            if r.get('status') in (200, 204):
                ok.append(pno)
            else:
                _log(log_fn, f'  ❌ {pno} 실패 status={r.get("status")} {str(r.get("text",""))[:100]}')
        except Exception as e:
            _log(log_fn, f'  ❌ {pno} 예외: {e}')
        time.sleep(0.3)   # 사람처럼 페이싱
    _log(log_fn, f'  API 판매중지: {len(ok)}/{len(product_nos)}건 성공')
    return ok


def _select_all_rows(driver, log_fn):
    """헤더 '전체선택' 체크박스 대신 각 행 체크박스를 개별로 직접 클릭.
    (2026-08-24 실측: 검색 2건 중 헤더 전체선택 클릭으로는 1건만 실제 선택돼 1건만 판매중지
    반영되는 문제 확인 — 표(tbody) 행별 체크박스를 하나씩 직접 클릭하는 방식으로 교체)."""
    from selenium.webdriver.common.by import By
    chks = driver.find_elements(By.XPATH, "//tbody//input[@type='checkbox']")
    n = 0
    for chk in chks:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", chk)
            chk.click()
            n += 1
        except Exception as e:
            _log(log_fn, f'    ⚠ 행 체크박스 클릭 실패: {e}')
    _log(log_fn, f'  ✅ 행별 체크박스 {n}/{len(chks)}개 선택')
    return n > 0


def _click(driver, xpaths, label, log_fn, timeout=6):
    """순수 Selenium 기본 el.click()을 사용 — 2026-08-24 실측으로 확정.
    검색 버튼에 CDP dispatchMouseEvent/ActionChains를 써봤지만 예외 없이 '성공'으로 찍히면서도
    실제로는 검색이 전혀 안 되는(항상 0건) 문제가 있었음. 반면 el.click()은 즉시 정상(13,507건)
    동작 확인됨 — 이 페이지에서는 WebDriver 표준 클릭이 오히려 가장 신뢰도 높음.
    (애초 '클릭 성공했는데 반영 안 됨' 사고의 진짜 원인은 클릭 방식이 아니라 잘못된 엉뚱한
    요소를 클릭 대상으로 잡고 있었던 selector 버그였음 — 그 selector는 이미 수정됨)
    el.click() 실패(가려짐 등) 시에만 JS 클릭으로 폴백."""
    el, xp = _find(driver, xpaths, timeout)
    if not el:
        _log(log_fn, f'  ❌ {label} 버튼 못찾음')
        return False
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        el.click()
        _log(log_fn, f'  ✅ {label} 클릭 ({xp[:40]})')
        return True
    except Exception as e:
        _log(log_fn, f'  ⚠ {label} 클릭 실패({e}) — JS 클릭 폴백')
        try:
            driver.execute_script("arguments[0].click();", el)
            _log(log_fn, f'  ✅ {label} 클릭(JS폴백) ({xp[:40]})')
            return True
        except Exception as e2:
            _log(log_fn, f'  ❌ {label} 클릭 예외: {e2}')
            return False


def _enter_goods_iframe(driver):
    driver.get(GOODS_MANAGE)
    time.sleep(9)
    frames = driver.find_elements(By.TAG_NAME, 'iframe')
    if frames:
        driver.switch_to.frame(frames[0])
        return True
    return False


def _read_apply_result(driver, log_fn):
    """'변경' 클릭 후 뜨는 "처리결과" 모달에서 실제 성공한 상품번호만 추출.
    표 형태: 결과(성공/실패) | 마스터상품번호 | 상품번호 | 사이트 | 상품명 | 사유.
    모달이 안 뜨거나 못 읽으면 빈 리스트(안전 기본값 — 낙관적 전체성공 가정 금지)."""
    try:
        rows = WebDriverWait(driver, 8).until(
            EC.presence_of_all_elements_located((By.XPATH, "//*[contains(text(),'처리결과')]/ancestor::*[3]//table//tbody//tr")))
        ok_pnos = []
        for r in rows:
            tds = r.find_elements(By.TAG_NAME, 'td')
            if len(tds) >= 3 and '성공' in tds[0].text:
                ok_pnos.append(tds[2].text.strip())
        _log(log_fn, f'  처리결과 모달: {len(ok_pnos)}/{len(rows)}건 성공')
        return ok_pnos
    except Exception as e:
        _log(log_fn, f'  ⚠ 처리결과 모달 못 읽음: {e}')
        return []


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
    try:
        ta.clear()
    except Exception:
        pass
    # 사용자 지시: 상품번호 사이 쉼표(,)로 구분해 한 번에 입력.
    joined = ','.join(str(n) for n in nums)
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


CHUNK_SIZE = 200  # 한 번에 검색+전체선택하는 상품번호 개수 — 너무 크면 가상그리드가 다 못 띄워
                   # '클릭은 성공했지만 실제론 일부만 처리'되는 문제가 있어 나눠 처리(2026-08-22, 사용자 지정).


def run_delete(targets, mode='validate', log_fn=None):
    """targets: [{login_id, product_no, seller_code, status}]. mode: validate(기본) | real | stop_only(판매중지만, 삭제안함)."""
    from apps.cpc.models import CrawlerAccount, GmarketLossDeleted, GmarketMyProduct
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver
    from crawlers.gmarket_cost_crawler import _esm_login

    # 계정별 묶기
    by_acc = {}
    for t in targets:
        by_acc.setdefault(t['login_id'], []).append(t)

    ok, reason = guard.preflight('지마켓적자삭제', platform='gmarket', wait=True)
    if not ok:
        _log(log_fn, f'⛔ preflight 차단: {reason}')
        return {'ok': False, 'skipped': reason}
    if reason != 'ok':
        _log(log_fn, f'⏳ 락 대기 후 시작: {reason}')

    summary = {'accounts': 0, 'deleted': 0, 'marked': 0, 'failed': 0}
    results = []
    try:
        for eid, items in by_acc.items():
            nums = []
            seen = set()
            for t in items:
                # 2026-08-24: 숫자만 남기는(isdigit) 필터가 옥션 상품번호의 알파벳 접두어(E/D 등,
                # 예: E641752041)까지 지워버려 옥션 상품을 전부 '검색 안 됨'으로 실패시키던 버그.
                # 지마켓 순수상품번호는 원래 숫자만이라 접두어 자체가 없으므로, 그냥 원본 그대로
                # 써도 두 형식(숫자만/문자+숫자) 다 안전하게 처리된다.
                p = str(t.get('product_no', '')).strip()
                if p and p not in seen:
                    seen.add(p)
                    nums.append(p)
            if not nums:
                continue
            _log(log_fn, f'[{eid}] 대상 {len(nums)}개 (판매중지→재조회→삭제) mode={mode}')
            for t in items:
                _log(log_fn, f'    · {t.get("product_no","")} {t.get("product_name") or "(상품명 미확인)"}')
            acc = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
            if not acc:
                summary['failed'] += 1
                continue
            d = None
            try:
                d = create_driver(kill_existing=False)
                d.set_page_load_timeout(45)
                # 창이 작으면(랜덤 뷰포트 1366x768 등) 검색결과 뒤쪽 행이 화면 밖이라 안 그려져
                # 체크박스를 못 찾는 문제 있었음(2026-08-24 실측) — 세로로 넉넉하게 키움.
                try:
                    d.set_window_size(1600, 2000)
                except Exception:
                    pass
                # 쿠키 우선 로그인(캡차 회피) — 성공하면 그걸로 끝, 굳이 또 전체 로그인 안 함
                # (2026-08-24 사용자 지시: 로그인 접속하면 1회만. 예전엔 쿠키 성공해도 무조건
                # _esm_login을 한 번 더 호출해 매번 로그인이 중복 발생했음)
                cookie_ok = False
                if acc.cookie_data:
                    try:
                        d.get('https://www.esmplus.com/'); time.sleep(2)
                        for c in json.loads(acc.cookie_data):
                            c.pop('sameSite', None)
                            try: d.add_cookie(c)
                            except Exception: pass
                        d.get('https://www.esmplus.com/'); time.sleep(2)
                        u = d.current_url.lower()
                        cookie_ok = ('login' not in u and 'signin' not in u)
                    except Exception:
                        pass
                if not cookie_ok:
                    if not _esm_login(d, eid, acc.password_enc or ''):
                        _log(log_fn, f'[{eid}] ❌ 로그인 실패(캡차 가능) — 건너뜀')
                        summary['failed'] += 1
                        continue
                else:
                    _log(log_fn, f'[{eid}] 쿠키 로그인 성공(재로그인 생략)')
                if not _enter_goods_iframe(d):
                    _log(log_fn, f'[{eid}] ❌ 상품관리 iframe 진입 실패')
                    summary['failed'] += 1
                    continue

                # === 1) 판매중지: 입력+확인 → 조회 → 전체선택 → 판매상태변경→판매중지 ===
                # 한 번에 너무 많은 상품번호(수백~수천)를 검색하면 가상그리드가 다 못 띄운 채로
                # 전체선택→판매중지 클릭만 '성공'해버려 실제론 일부만 처리되는 문제가 있었다
                # (2026-08-22 발견 — 31,593개 지정 중 2,741개만 실제 처리됨).
                # → CHUNK_SIZE 단위로 나눠 검색·처리하고, 청크별로 실제 처리 개수를 집계한다.
                if mode == 'validate':
                    okp, verified = _paste_and_search(d, nums[:CHUNK_SIZE], log_fn)
                    if not verified:
                        summary['failed'] += 1
                        continue
                    cnt = _result_count(d)
                    _log(log_fn, f'  조회 결과행(근사, 첫 배치): {cnt}')
                    sa, _ = _find(d, XP_SELECT_ALL, 3)
                    sc, _ = _find(d, XP_STATUS_CHANGE, 3)
                    de, _ = _find(d, XP_DELETE, 3)
                    _log(log_fn, f'  [validate] 전체선택:{"O" if sa else "X"} 판매상태변경:{"O" if sc else "X"} 삭제:{"O" if de else "X"} — 클릭 안함')
                    results.append({'login_id': eid, 'validated': True, 'rows': cnt})
                    summary['accounts'] += 1
                    continue

                # ---- real / stop_only 모드 (판매중지는 공통, 삭제는 real만) ----
                chunks = [nums[i:i + CHUNK_SIZE] for i in range(0, len(nums), CHUNK_SIZE)]
                acc_stopped = 0
                acc_deleted = 0
                acc_marked = 0
                acc_fail_chunks = 0
                for ci, chunk in enumerate(chunks, 1):
                    _log(log_fn, f'  [{eid}] 배치 {ci}/{len(chunks)} ({len(chunk)}개)')

                    if mode == 'stop_only':
                        # 2026-08-24: 화면 클릭 방식(검색→선택→상태변경→판매중지→변경)이 여러
                        # 계정을 연속 처리할 때 불안정해(체크박스/변경버튼 못 찾음 빈발) API 직접
                        # 호출로 교체 — goodsNo 조회 후 sellStatus API를 바로 호출.
                        applied_pnos = _api_suspend_products(d, chunk, log_fn)
                        if applied_pnos:
                            GmarketMyProduct.objects.filter(
                                account=acc, product_no__in=applied_pnos).update(status_type='판매중지')
                            acc_stopped += len(applied_pnos)
                        if len(applied_pnos) < len(chunk):
                            acc_fail_chunks += 1
                        continue

                    okp, verified = _paste_and_search(d, chunk, log_fn)
                    if not verified:
                        acc_fail_chunks += 1
                        continue
                    cnt = _result_count(d)
                    _log(log_fn, f'    조회 결과행(근사): {cnt}')
                    time.sleep(2)   # 행 렌더링 여유시간(2026-08-24: 너무 빨리 체크박스를 찾아 일부 행을 놓치던 문제)

                    _select_all_rows(d, log_fn)
                    time.sleep(1)
                    applied_pnos = []
                    if _click(d, XP_STATUS_CHANGE, '판매 상태 변경', log_fn):
                        time.sleep(1)
                        if _click(d, XP_STOPSELL, '판매중지', log_fn):
                            time.sleep(1)
                            # "변경" 확정 버튼 — 이걸 안 누르면 옵션만 고른 상태로 아무 반영도 안 됨
                            # (2026-08-24 실측 확인). 클릭 후 뜨는 "처리결과" 모달에서 실제
                            # 성공한 상품번호만 골라 DB에 반영(낙관적 전체성공 가정 금지).
                            if _click(d, XP_APPLY_CHANGE, '변경', log_fn):
                                time.sleep(2)
                                applied_pnos = _read_apply_result(d, log_fn)
                        _clear_popups(d, log_fn)
                        time.sleep(2)
                    stopped = bool(applied_pnos)

                    # === real 모드: 재조회 → 전체선택 → 삭제 → 잔여검증 (청크 단위) ===
                    _paste_and_search(d, chunk, log_fn)
                    _click(d, XP_SELECT_ALL, '전체선택(삭제전)', log_fn)
                    time.sleep(1)
                    if _click(d, XP_DELETE, '삭제', log_fn):
                        _clear_popups(d, log_fn)
                        time.sleep(2)
                    _paste_and_search(d, chunk, log_fn)
                    remaining = _result_count(d)
                    deleted_ok = (remaining == 0)
                    _log(log_fn, f'    잔여검증: {remaining}행 → 삭제{"성공" if deleted_ok else "미완(보류)"}')
                    if deleted_ok:
                        for pn in chunk:
                            GmarketLossDeleted.objects.get_or_create(
                                login_id=eid, product_no=pn,
                                defaults={'seller_code': ''})
                            acc_marked += 1
                        acc_deleted += len(chunk)
                    else:
                        acc_fail_chunks += 1

                if mode == 'stop_only':
                    summary.setdefault('stopped', 0)
                    summary['stopped'] += acc_stopped
                    if acc_fail_chunks:
                        summary['failed'] += acc_fail_chunks
                    results.append({'login_id': eid, 'stopped': acc_stopped, 'requested': len(nums),
                                    'failed_batches': acc_fail_chunks})
                    summary['accounts'] += 1
                    continue

                summary['deleted'] += acc_deleted
                summary['marked'] += acc_marked
                if acc_fail_chunks:
                    summary['failed'] += acc_fail_chunks
                results.append({'login_id': eid, 'deleted': acc_deleted, 'requested': len(nums),
                                'failed_batches': acc_fail_chunks})
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

    label = {'validate': 'VALIDATE(검증)', 'real': '실삭제', 'stop_only': '판매중지'}.get(mode, mode)
    if mode == 'stop_only':
        msg = (f'🛑 [지마켓 적자상품 {label} 완료]\n'
               f'계정 {summary["accounts"]} / 판매중지 {summary.get("stopped", 0)}건 / 실패 {summary["failed"]}')
    else:
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

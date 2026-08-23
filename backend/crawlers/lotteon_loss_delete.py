"""롯데온 죽은 W코드(오너클랜소싱, 매칭無) 상품 정리 — gmarket_loss_delete.py 미러링.

롯데온은 11번가/지마켓/스마트스토어와 달리 "판매중지" 상태를 판매자가 직접 설정할 수 없다
(판매자센터 "판매중지 상품관리" 페이지 안내: 법령/정책 위반 상품 전용, 롯데 측이 부여).
당초 판매중(SALE) 미매칭 건은 "판매종료"로 전환하려 했으나(비가역), 사용자 요청(2026-08-23)으로
최종적으로는 실제 삭제(mode='delete')까지 지원 — 판매중지/판매종료/품절 상태의 죽은 W코드
리스팅을 진짜 삭제(재판매 불가, 완전 비가역)한다. SALE(정상매칭) 4건은 대상에서 제외해야 함(호출부 책임).

플로우(실측, rejoice234, 2026-08-23):
  로그인(2FA 불필요, 폼입력만) → 상품관리>상품 조회/수정 → "판매자내부상품번호" 라디오 선택
  → 상품번호 textarea에 붙여넣기 → 조회 → 헤더 전체선택 체크박스
  → 삭제(mode='delete'): "선택상품삭제" 클릭 → 확인창("삭제된 상품은 재판매가 불가능합니다") 확인
    → 완료창("정상 처리되었습니다") 확인 → 같은 코드로 재조회해 실제로 사라졌는지 검증 후에만 DB에서도 삭제
    (지마켓 사례처럼 "클릭 성공=성공 판정" 하지 않고 재조회로 직접 검증한다).
  → 판매종료(mode='real', 레거시): "상품판매 변경" 클릭(새 탭 "상품정보일괄수정")→"일괄수정"→팝업 드롭다운에서
    "판매종료" 선택→"수정"→결과표(성공여부/실패사유)에서 실제 성공한 건만 DB 반영.
"""
import time

from selenium.webdriver.common.by import By

MAIN_URL = 'https://store.lotteon.com'

XP_LOGIN_ID = ['input[placeholder="사용자ID"]']
XP_LOGIN_PW = ['input[type="password"]']
XP_LOGIN_BTN = ['.btn_login']
XP_SEARCH_TA = ['[id$="_tbx_SelectPdCnts"]']
XP_SEARCH_BTN = ["input[value='조회']"]
XP_SELECT_ALL = ["[id$='header__column9_checkboxLabel__id']"]
XP_SALE_CHANGE_BTN = ["input[value='상품판매 변경']"]
XP_DELETE_BTN = ["input[value='선택상품삭제']"]
XP_DIALOG_CONFIRM = ["input[value='확인']"]
XP_BATCH_MOD_BTN = ["[id$='btn_btchMod']"]
XP_POPUP_IFRAME = ["[id$='cmNoPop_iframe']"]
STATUS_DROPDOWN_BTN = 'mf_spdSlStatCd_button'
STATUS_OPTION_END = 'mf_spdSlStatCd_itemTable_2'  # 0=판매중 1=품절 2=판매종료 (실측 고정 인덱스)
CONFIRM_BTN = 'mf_btn_trigger1'   # 수정
CANCEL_BTN = 'mf_btn_trigger11'   # 취소

CHUNK_SIZE = 100  # 실측(2026-08-23): 판매자내부상품코드는 최대 100개까지 조회 가능(사이트 자체 팝업 제한).
                  # 200으로 돌리면 "판매자내부상품코드는 최대 100개까지 조회 가능합니다" 팝업이 뜨며
                  # 검색 자체가 무산돼 매 배치 0건으로 실패한다(4335건 전량 실패로 최초 발견).


def _log(fn, m):
    if fn:
        fn(m)


def _find(driver, selectors, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        for sel in selectors:
            els = [e for e in driver.find_elements(By.CSS_SELECTOR, sel) if e.is_displayed()]
            if els:
                return els[0]
        time.sleep(0.3)
    return None


def _find_by_text(driver, text, tag='label', timeout=4):
    """탭 인스턴스 번호(ML0000000NN)가 세션마다 바뀔 수 있는 요소는 id 대신 텍스트로 찾는다."""
    end = time.time() + timeout
    xp = f"//{tag}[contains(text(),'{text}')]"
    while time.time() < end:
        els = [e for e in driver.find_elements(By.XPATH, xp) if e.is_displayed()]
        if els:
            return els[0]
        time.sleep(0.3)
    return None


def _click(driver, el):
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)


def _login(driver, login_id, password, log_fn=None):
    driver.get(MAIN_URL)
    time.sleep(3)
    if 'login' in driver.current_url.lower():
        idf = _find(driver, XP_LOGIN_ID)
        pwf = _find(driver, XP_LOGIN_PW)
        if not idf or not pwf:
            _log(log_fn, '로그인 입력칸 못찾음')
            return False
        idf.clear(); idf.send_keys(login_id)
        pwf.clear(); pwf.send_keys(password)
        btn = _find(driver, XP_LOGIN_BTN)
        if btn:
            _click(driver, btn)
        time.sleep(3)
    if 'login' in driver.current_url.lower():
        _log(log_fn, '로그인 실패(2FA 요구 등) — 사람 개입 필요')
        return False
    return True


def _enter_product_page(driver, log_fn=None):
    driver.execute_script("document.getElementById('mf_wfm_menuBox_gen_1stMenu_1_btn_1stMenu')?.click();")
    time.sleep(2)
    driver.execute_script(
        "document.getElementById('mf_wfm_menuBox_gen_1stMenu_1_gen_2ndMenu_3_btn_2ndMenu')?.click();")
    time.sleep(6)
    ta = _find(driver, XP_SEARCH_TA, timeout=8)
    if not ta:
        _log(log_fn, '상품번호 입력칸 못찾음 — 페이지 로드 실패')
        return False
    return True


def _search_and_select_all(driver, codes, log_fn=None, select=True):
    """codes(판매자내부상품번호=seller_product_code/W코드 리스트)로 검색 후 헤더 전체선택(select=False면 검색만).
    반환: 검색결과 있었는지(bool)."""
    inner_code_radio = _find_by_text(driver, '판매자내부상품번호')
    if inner_code_radio:
        _click(driver, inner_code_radio)
        time.sleep(0.3)
    else:
        _log(log_fn, '  ⚠ "판매자내부상품번호" 라디오 못찾음 — 기본(판매자상품번호)으로 검색될 수 있음')

    ta = _find(driver, XP_SEARCH_TA)
    if not ta:
        return False
    ta.clear()
    ta.send_keys('\n'.join(codes))
    time.sleep(0.5)
    val = ta.get_attribute('value') or ''
    missing = [c for c in codes if c not in val]
    if missing:
        _log(log_fn, f'  ❌ 상품번호 입력 누락 {len(missing)}개 → 중단(안전)')
        return False
    btn = _find(driver, XP_SEARCH_BTN)
    if not btn:
        return False
    _click(driver, btn)
    time.sleep(4)

    # 100개 초과 조회 시 사이트 자체 팝업으로 검색이 무산됨(실측 확인, 2026-08-23) — 방어적으로 감지.
    limit_popup = driver.find_elements(By.XPATH, "//*[contains(text(),'최대 100개까지 조회 가능')]")
    if any(e.is_displayed() for e in limit_popup):
        _log(log_fn, f'  ❌ 100개 초과 조회 팝업 발생(코드 {len(codes)}개) — CHUNK_SIZE 확인 필요')
        ok_btn = driver.find_elements(By.CSS_SELECTOR, "input[value='확인']")
        if ok_btn:
            _click(driver, ok_btn[0])
        return False

    if not select:
        return True

    header_cb = _find(driver, XP_SELECT_ALL, timeout=4)
    if not header_cb:
        _log(log_fn, '  검색결과 없음(전체선택 체크박스 미노출) — 스킵')
        return False
    _click(driver, header_cb)
    time.sleep(1)
    return True


def _change_status_to_end(driver, log_fn=None):
    """선택된 상품을 '판매종료'로 변경 시도 후 결과표(성공여부/실패사유)를 읽어 반환.
    반환: {판매자상품코드: True/False(성공여부)} — 결과표에서 명시적으로 '성공'이 아니면 전부 실패로 간주(fail-closed)."""
    btn = _find(driver, XP_SALE_CHANGE_BTN)
    if not btn:
        _log(log_fn, '  ❌ "상품판매 변경" 버튼 못찾음')
        return {}
    _click(driver, btn)
    time.sleep(2)

    batch_btn = _find(driver, XP_BATCH_MOD_BTN, timeout=8)
    if not batch_btn:
        _log(log_fn, '  ❌ "일괄수정" 버튼 못찾음(상품정보일괄수정 탭 전환 실패)')
        return {}
    _click(driver, batch_btn)
    time.sleep(1.5)

    iframe = _find(driver, XP_POPUP_IFRAME, timeout=6)
    if not iframe:
        _log(log_fn, '  ❌ 일괄수정 팝업(iframe) 못찾음')
        return {}
    driver.switch_to.frame(iframe)
    try:
        dd = driver.find_elements(By.ID, STATUS_DROPDOWN_BTN)
        if not dd:
            _log(log_fn, '  ❌ 상태변경 드롭다운 못찾음')
            return {}
        _click(driver, dd[0])
        time.sleep(1)
        opt = driver.find_elements(By.ID, STATUS_OPTION_END)
        if not opt:
            _log(log_fn, '  ❌ "판매종료" 옵션 못찾음')
            return {}
        _click(driver, opt[0])
        time.sleep(0.5)

        confirm = driver.find_elements(By.ID, CONFIRM_BTN)
        if not confirm:
            _log(log_fn, '  ❌ "수정" 버튼 못찾음')
            return {}
        _click(driver, confirm[0])
        time.sleep(3)

        # 결과표 파싱: 판매자상품코드 | 판매자상품명 | 성공여부 | 실패사유
        results = {}
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, 'td')
            if len(cells) < 3:
                continue
            texts = [c.text.strip() for c in cells]
            code = texts[0] if texts else ''
            if not code:
                continue
            success_text = texts[2] if len(texts) > 2 else ''
            results[code] = (success_text == '성공')
            reason = texts[3] if len(texts) > 3 else ''
            _log(log_fn, f'    [{code}] {"성공" if results[code] else f"실패({reason or success_text})"}')
        return results
    finally:
        driver.switch_to.default_content()


def _delete_selected(driver, log_fn=None):
    """선택된 상품 실제 삭제. 확인창("삭제된 상품은 재판매가 불가능합니다")→확인, 완료창("정상 처리되었습니다")→확인
    순서로 2번 확인 필요(실측). 결과표가 따로 없어(배치 전체 단위 처리) 여기서는 클릭 진행 여부만 반환하고,
    실제 성공 여부는 호출부에서 재조회로 검증한다(지마켓 낙관적판정 버그 재발 방지 — 클릭 성공 ≠ 실제 성공)."""
    btn = _find(driver, XP_DELETE_BTN)
    if not btn:
        _log(log_fn, '  ❌ "선택상품삭제" 버튼 못찾음')
        return False
    _click(driver, btn)
    time.sleep(1.5)

    confirm1 = _find(driver, XP_DIALOG_CONFIRM, timeout=4)
    if not confirm1:
        _log(log_fn, '  ❌ 삭제 확인창 못찾음')
        return False
    _click(driver, confirm1)
    time.sleep(2)

    # 완료창("정상 처리되었습니다")도 확인 클릭 — 없을 수도 있어 짧게만 대기
    confirm2 = _find(driver, XP_DIALOG_CONFIRM, timeout=3)
    if confirm2:
        _click(driver, confirm2)
        time.sleep(1)
    return True


def _verify_gone(driver, codes, log_fn=None):
    """codes(seller_product_code 리스트)를 재조회해 페이지 소스에 남아있는지로 실제 삭제 여부 검증.
    반환: (성공한 코드 리스트, 실패한 코드 리스트). 검색 자체가 실패하면(입력칸 못찾음 등) 안전하게 전부 실패 처리."""
    if not _search_and_select_all(driver, codes, log_fn, select=False):
        _log(log_fn, '  ⚠ 재조회 실패 — 검증 불가, 안전하게 전부 실패 처리')
        return [], list(codes)
    html = driver.page_source
    still_there = [c for c in codes if c in html]
    gone = [c for c in codes if c not in still_there]
    return gone, still_there


def run_delete(targets, mode='validate', log_fn=None):
    """targets: [{login_id, product_no}]. mode: validate(기본, 클릭 없이 확인만) | real(실제 판매종료).
    지마켓과 달리 결과표를 직접 읽어 실제 성공 건만 반영(2026-08-23, 낙관적 판정 버그 재발 방지)."""
    from apps.cpc import eleven_block_guard as guard
    from apps.lotteon.models import LotteonAccount, LotteonMyProduct
    from crawlers.browser import create_driver

    by_acc = {}
    for t in targets:
        by_acc.setdefault(t['login_id'], []).append(str(t['product_no']))

    ok, reason = guard.preflight('롯데온적자삭제', platform='lotteon')
    if not ok:
        _log(log_fn, f'⛔ preflight 차단: {reason}')
        return {'ok': False, 'skipped': reason}

    summary = {'accounts': 0, 'ended': 0, 'failed': 0}
    results = []
    try:
        for eid, codes in by_acc.items():
            acc = LotteonAccount.objects.filter(login_id=eid).first()
            if not acc:
                summary['failed'] += len(codes)
                continue
            _log(log_fn, f'[{eid}] 대상 {len(codes)}개 (판매종료) mode={mode}')

            driver = None
            try:
                driver = create_driver(user_data_dir=f'/tmp/lotteon_profiles/{eid}', kill_existing=False)
                if not _login(driver, eid, acc.login_pw, log_fn):
                    summary['failed'] += len(codes)
                    continue
                if not _enter_product_page(driver, log_fn):
                    summary['failed'] += len(codes)
                    continue

                acc_ended = 0
                acc_failed = 0
                chunks = [codes[i:i + CHUNK_SIZE] for i in range(0, len(codes), CHUNK_SIZE)]
                for ci, chunk in enumerate(chunks, 1):
                    _log(log_fn, f'  배치 {ci}/{len(chunks)} ({len(chunk)}개)')
                    if not _search_and_select_all(driver, chunk, log_fn):
                        acc_failed += len(chunk)
                        continue
                    if mode == 'validate':
                        _log(log_fn, '  [validate] 검색+전체선택 확인 완료 — 실제 변경 없음')
                        continue

                    if mode == 'delete':
                        if not _delete_selected(driver, log_fn):
                            acc_failed += len(chunk)
                            continue
                        gone, still_there = _verify_gone(driver, chunk, log_fn)
                        if gone:
                            LotteonMyProduct.objects.filter(
                                account=acc, seller_product_code__in=gone).delete()
                        if still_there:
                            _log(log_fn, f'    ⚠ 삭제 실패(재조회에도 남아있음) {len(still_there)}개: {still_there[:10]}')
                        acc_ended += len(gone)
                        acc_failed += len(still_there)
                        continue

                    res = _change_status_to_end(driver, log_fn)
                    ok_codes = [c for c, v in res.items() if v]
                    if ok_codes:
                        LotteonMyProduct.objects.filter(
                            account=acc, seller_product_code__in=ok_codes).update(status_code='END')
                    acc_ended += len(ok_codes)
                    acc_failed += len(chunk) - len(ok_codes)

                summary['ended'] += acc_ended
                summary['failed'] += acc_failed
                summary['accounts'] += 1
                results.append({'login_id': eid, 'ended': acc_ended, 'requested': len(codes), 'failed': acc_failed})
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
    finally:
        try:
            guard.release_global_lock(platform='lotteon')
        except Exception:
            pass

    label = {'validate': 'VALIDATE(검증)', 'delete': '실삭제'}.get(mode, '판매종료')
    action_label = '삭제' if mode == 'delete' else '판매종료'
    msg = (f'🛑 [롯데온 미매칭 {label} 완료]\n'
           f'계정 {summary["accounts"]} / {action_label} {summary.get("ended", 0)}건 / 실패 {summary["failed"]}')
    _log(log_fn, msg)
    if mode != 'validate':
        try:
            from apps.cpc import eleven_block_guard as guard2
            guard2._send_telegram_alert(msg)
        except Exception:
            pass
    return {'ok': True, 'mode': mode, **summary, 'results': results}

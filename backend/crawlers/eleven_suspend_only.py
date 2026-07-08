"""11번가 상품 판매중지 전용(삭제 없음).

핵심 발견(2026-07-08): 상품목록 그리드가 jqxGrid 커스텀 체크박스 위젯이라 일반 JS
click()/jQuery API로는 실제 grid 선택 상태가 갱신되지 않음. iframe 내부 요소의
뷰포트 좌표에 iframe 자체의 offset을 더해 CDP Input.dispatchMouseEvent로 "진짜"
신뢰된(trusted) 클릭을 보내야만 jqxGrid('getselectedrowindexes')가 갱신된다.
또한 "판매중지" 버튼은 새 팝업 창(window.open)에 최종 확인 폼을 띄우는 구조라
window_handles 전환 후 그 안의 "적용" 버튼까지 클릭해야 완료된다.
"""
import logging
import time

logger = logging.getLogger('crawler')


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def _cdp_click(driver, el, iframe_id):
    from selenium.webdriver.common.by import By
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
    time.sleep(0.35)
    inner = driver.execute_script(
        "var r=arguments[0].getBoundingClientRect(); return [r.x,r.y,r.width,r.height];", el)
    driver.switch_to.default_content()
    iframe_el = driver.find_element(By.ID, iframe_id)
    outer = driver.execute_script("var r=arguments[0].getBoundingClientRect(); return [r.x,r.y];", iframe_el)
    x = outer[0] + inner[0] + inner[2] / 2
    y = outer[1] + inner[1] + inner[3] / 2
    driver.execute_cdp_cmd('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': x, 'y': y})
    driver.execute_cdp_cmd('Input.dispatchMouseEvent',
                            {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
    time.sleep(0.1)
    driver.execute_cdp_cmd('Input.dispatchMouseEvent',
                            {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})


def _suspend_current_search(driver, eid, log_fn):
    """검색된 결과에서 전체선택 → jsSubmit(SELL_STOP) → 팝업 '적용' 클릭까지 수행.
    반환: (checked_ok, popup_ok)"""
    from selenium.webdriver.common.by import By
    from crawlers.eleven_loss_delete import IFRAME_ID, _focus_frame

    # 1) 헤더 "전체선택" 체크박스를 진짜(trusted) 클릭으로 체크
    header_cb = None
    for xp in ['//div[contains(@class,"jqx-grid-column-header")]//div[contains(@class,"jqx-checkbox")]',
               '(//div[@id="dvdataGrid"]//div[contains(@class,"jqx-checkbox")])[1]']:
        els = driver.find_elements(By.XPATH, xp)
        if els:
            header_cb = els[0]
            break
    if not header_cb:
        _log(log_fn, f'[{eid}] 헤더 체크박스 못찾음')
        return False, False
    _cdp_click(driver, header_cb, IFRAME_ID)
    time.sleep(0.8)
    _focus_frame(driver)

    sel = driver.execute_script(
        "try { return jQuery('#dvdataGrid').jqxGrid('getselectedrowindexes').length; } catch(e){ return -1; }")
    if not sel or sel <= 0:
        _log(log_fn, f'[{eid}] 전체선택 후에도 선택된 행 없음(sel={sel})')
        return False, False

    # 2) jsSubmit('SELL_STOP') 직접 호출 → 새 팝업 오픈
    before_handles = len(driver.window_handles)
    driver.execute_script("try { jsSubmit('SELL_STOP'); } catch(e) {}")
    time.sleep(2)
    if len(driver.window_handles) <= before_handles:
        # 검증 실패(선택 0건 등)로 alert만 뜬 경우
        try:
            alert = driver.switch_to.alert
            txt = alert.text
            alert.accept()
            _log(log_fn, f'[{eid}] 팝업 안뜨고 alert: {txt}')
        except Exception:
            _log(log_fn, f'[{eid}] 팝업도 alert도 없음')
        return True, False

    driver.switch_to.window(driver.window_handles[-1])
    try:
        apply_btn = None
        for e in driver.find_elements(By.XPATH, "//*[normalize-space(.)='적용']"):
            if e.rect.get('width', 0) > 0:
                apply_btn = e
                break
        if not apply_btn:
            _log(log_fn, f'[{eid}] 팝업에서 적용버튼 못찾음')
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            _focus_frame(driver)
            return True, False
        driver.execute_script("arguments[0].click();", apply_btn)
        time.sleep(1.5)
        try:
            alert = driver.switch_to.alert
            _log(log_fn, f'[{eid}] 적용 후 alert: {alert.text}')
            alert.accept()
            time.sleep(1)
        except Exception:
            pass
    finally:
        try:
            if len(driver.window_handles) > 1:
                driver.close()
        except Exception:
            pass
        driver.switch_to.window(driver.window_handles[0])
        _focus_frame(driver)
    return True, True


def suspend_only(targets, mode='validate', eid_filter=None, log_fn=None):
    """targets: [{'eleven_id' or 'login_id','product_no'}...]. mode: validate(검색만) | real(실제 판매중지)."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.eleven_crawler import _do_login, _drain_alerts
    from crawlers.browser import create_driver, stop_display
    from crawlers.eleven_loss_delete import PRODUCT_PAGE, _paste_and_search, _digits_only

    if mode not in ('validate', 'real'):
        mode = 'validate'

    ok, reason = guard.preflight('11번가살생물제판매중지')
    if not ok:
        _log(log_fn, f'⏭️ 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    grouped = {}
    for t in targets:
        eid = t.get('eleven_id') or t.get('login_id')
        if eid_filter and eid != eid_filter:
            continue
        grouped.setdefault(eid, []).append(t)
    by_acc = {eid: sorted(grouped[eid], key=lambda x: str(x['product_no']))
              for eid in sorted(grouped.keys())}

    pw_map = {a.login_id: a.password_enc for a in CrawlerAccount.objects.filter(platform='11st')}
    summary = {'accounts': 0, 'suspended_accounts': 0, 'failed': 0}
    results = []
    try:
        for eid, items in by_acc.items():
            blocked, _, _ = guard.is_blocked()
            if blocked:
                _log(log_fn, '⛔ 차단 감지 — 중단')
                break
            nums = _digits_only(items)
            _log(log_fn, f'[{eid}] 로그인 시도 — 판매중지 대상 {len(nums)}개 (mode={mode})')
            if not nums:
                continue
            driver = None
            try:
                driver = create_driver(kill_existing=False)
                driver.set_window_size(1920, 1080)
                sn = _do_login(driver, eid, pw_map.get(eid, ''))
                if not sn:
                    _log(log_fn, f'[{eid}] 로그인 실패 — 건너뜀')
                    summary['failed'] += 1
                    continue
                driver.implicitly_wait(0)
                driver.set_page_load_timeout(30)
                _drain_alerts(driver, login_id=eid)
                driver.get(PRODUCT_PAGE)
                time.sleep(3)

                rows = _paste_and_search(driver, nums, log_fn, eid)

                if mode == 'validate':
                    _log(log_fn, f'[{eid}] (validate) 검색결과 {rows}행')
                    results.append({'eleven_id': eid, 'rows': rows})
                    summary['accounts'] += 1
                    continue

                checked_ok, popup_ok = False, False
                if rows:
                    checked_ok, popup_ok = _suspend_current_search(driver, eid, log_fn)
                results.append({'eleven_id': eid, 'rows': rows, 'checked': checked_ok, 'applied': popup_ok})
                if popup_ok:
                    summary['suspended_accounts'] += 1
                else:
                    summary['failed'] += 1
                summary['accounts'] += 1
            except Exception as e:
                _log(log_fn, f'[{eid}] 오류: {str(e)[:200]}')
                summary['failed'] += 1
            finally:
                try:
                    if driver:
                        driver.quit()
                except Exception:
                    pass
            time.sleep(3)
    finally:
        guard.release_global_lock()
        try:
            stop_display()
        except Exception:
            pass

    label = 'VALIDATE(검증)' if mode == 'validate' else '실행'
    msg = (f'⛔ [11번가 살생물제 판매중지 {label}]\n'
           f'계정 {summary["accounts"]} / 판매중지완료 {summary["suspended_accounts"]} / 실패 {summary["failed"]}')
    _log(log_fn, msg)
    if mode == 'real':
        try:
            guard._send_telegram_alert(msg)
        except Exception:
            pass
    return {'ok': True, 'mode': mode, **summary, 'results': results}

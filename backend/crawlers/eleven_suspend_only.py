"""11번가 상품 판매중지 전용(삭제 없음) — eleven_loss_delete.py 내부 함수 재사용.
살생물제 등 규제대응처럼 '삭제'까지는 원치 않고 '판매중지'만 필요한 경우 사용.

셀러오피스 상품조회(/view/8006) → 상품번호 검색(전체 체크상태) → 판매중지 클릭 → 팝업정리.
삭제 단계는 절대 실행하지 않음.
"""
import logging
import time

logger = logging.getLogger('crawler')


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def suspend_only(targets, mode='validate', eid_filter=None, log_fn=None):
    """targets: [{'eleven_id','product_no'}...]. mode: validate(버튼 찾기만) | real(실제 클릭)."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.eleven_crawler import _do_login, _drain_alerts
    from crawlers.browser import create_driver, stop_display
    from crawlers.eleven_loss_delete import (
        PRODUCT_PAGE, XP_STOPSELL, _focus_frame, _find, _paste_and_search,
        _click, _clear_popups, _digits_only,
    )

    if mode not in ('validate', 'real'):
        mode = 'validate'

    ok, reason = guard.preflight('11번가살생물제판매중지')
    if not ok:
        _log(log_fn, f'⏭️ 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    grouped = {}
    for t in targets:
        eid = t['eleven_id']
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

                if mode == 'validate':
                    rows = _paste_and_search(driver, nums, log_fn, eid)
                    sxp, _e = _find(driver, XP_STOPSELL, 6)
                    _log(log_fn, f'[{eid}] (validate) 검색결과 {rows}행 / 판매중지버튼: {"OK" if sxp else "미발견"}')
                    results.append({'eleven_id': eid, 'rows': rows, 'stopsell_btn': bool(sxp)})
                    summary['accounts'] += 1
                    continue

                # real: 검색(전체체크 상태) → 판매중지 → 팝업정리. 삭제 단계 없음.
                rows = _paste_and_search(driver, nums, log_fn, eid)
                clicked = False
                if rows:
                    clicked = _click(driver, XP_STOPSELL, '판매중지', log_fn, eid)
                    if clicked:
                        _clear_popups(driver, eid, log_fn)
                        time.sleep(2)
                results.append({'eleven_id': eid, 'rows': rows, 'clicked': clicked})
                if clicked:
                    summary['suspended_accounts'] += 1
                else:
                    summary['failed'] += 1
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

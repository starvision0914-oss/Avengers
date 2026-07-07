"""지마켓/옥션(ESM) 상품 판매중지 전용(삭제 없음) — gmarket_loss_delete.py 내부 함수 재사용.
ESM 통합상품관리는 지마켓·옥션을 한 화면에서 같이 다루므로 계정(login_id) 단위로 처리.
삭제 단계는 절대 실행하지 않음.
"""
import json
import logging
import time

logger = logging.getLogger('crawler')


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def suspend_only(targets, mode='validate', log_fn=None):
    """targets: [{'login_id','product_no'}...]. mode: validate(버튼 찾기만) | real(실제 클릭)."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver
    from crawlers.gmarket_cost_crawler import _esm_login
    from crawlers.gmarket_loss_delete import (
        _enter_goods_iframe, _paste_and_search, _click, _clear_popups, _find,
        XP_SELECT_ALL, XP_STATUS_CHANGE, XP_STOPSELL,
    )

    by_acc = {}
    for t in targets:
        eid = t['login_id']
        p = ''.join(ch for ch in str(t.get('product_no', '')) if ch.isdigit())
        if p:
            by_acc.setdefault(eid, [])
            if p not in by_acc[eid]:
                by_acc[eid].append(p)

    ok, reason = guard.preflight('지마켓살생물제판매중지', platform='gmarket')
    if not ok:
        _log(log_fn, f'⛔ preflight 차단: {reason}')
        return {'ok': False, 'skipped': reason}

    summary = {'accounts': 0, 'suspended_accounts': 0, 'failed': 0}
    results = []
    try:
        for eid, nums in by_acc.items():
            _log(log_fn, f'[{eid}] 대상 {len(nums)}개 (판매중지만) mode={mode}')
            acc = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
            if not acc:
                _log(log_fn, f'[{eid}] 계정 없음 — 건너뜀')
                summary['failed'] += 1
                continue
            d = None
            try:
                d = create_driver(kill_existing=False)
                d.set_page_load_timeout(45)
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

                okp, verified = _paste_and_search(d, nums, log_fn)
                if not verified:
                    summary['failed'] += 1
                    continue

                if mode == 'validate':
                    sa, _ = _find(d, XP_SELECT_ALL, 3)
                    sc, _ = _find(d, XP_STATUS_CHANGE, 3)
                    stp, _ = _find(d, XP_STOPSELL, 3)
                    _log(log_fn, f'  [validate] 전체선택:{"O" if sa else "X"} 판매상태변경:{"O" if sc else "X"} 판매중지:{"O" if stp else "X"} — 클릭 안함')
                    results.append({'login_id': eid, 'validated': True})
                    summary['accounts'] += 1
                    continue

                # ---- real (판매중지까지만, 삭제 없음) ----
                _click(d, XP_SELECT_ALL, '전체선택', log_fn)
                time.sleep(1)
                suspended = False
                if _click(d, XP_STATUS_CHANGE, '판매 상태 변경', log_fn):
                    time.sleep(1)
                    if _click(d, XP_STOPSELL, '판매중지', log_fn):
                        _clear_popups(d, log_fn)
                        time.sleep(2)
                        suspended = True
                results.append({'login_id': eid, 'suspended': suspended})
                if suspended:
                    summary['suspended_accounts'] += 1
                else:
                    summary['failed'] += 1
                summary['accounts'] += 1
            finally:
                if d:
                    try: d.quit()
                    except Exception: pass
                guard.is_blocked()
    finally:
        try:
            guard.release_global_lock(platform='gmarket')
        except Exception:
            pass

    label = 'VALIDATE(검증)' if mode == 'validate' else '실행'
    msg = (f'⛔ [지마켓/옥션 살생물제 판매중지 {label}]\n'
           f'계정 {summary["accounts"]} / 판매중지완료 {summary["suspended_accounts"]} / 실패 {summary["failed"]}')
    _log(log_fn, msg)
    if mode == 'real':
        try:
            from apps.cpc import eleven_block_guard as guard2
            guard2._send_telegram_alert(msg)
        except Exception:
            pass
    return {'ok': True, 'mode': mode, **summary, 'results': results}

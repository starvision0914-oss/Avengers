"""지마켓 광고 통합 제어 — 한 번 로그인으로 AI 광고 → 간편광고(CPC2)를 순차 제어.

AI 제어기와 간편 제어기가 모두 같은 사이트(ad.esmplus.com) + 같은 로그인(gmarket_crawler)을
쓰므로, 계정당 1회만 로그인해서 AI를 먼저 끄고/켠 뒤 같은 세션에서 간편광고까지 처리한다.
→ 동시 접속(2세션)으로 인한 IP 차단·캡차 반복을 방지.

account별로 ai_accounts/cpc2_accounts 멤버십에 따라 해당 제어만 수행한다.
guard.preflight(platform='gmarket')로 전역락 — 다른 지마켓 크롤과 직렬화.
"""
import time
from apps.cpc import eleven_block_guard as guard
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_ai_control_crawler import _login, control_account
from crawlers.gmarket_cpc2_control_crawler import control_one


def _log(fn, msg):
    print(time.strftime('%H:%M:%S '), msg, flush=True)
    if fn:
        try:
            fn(msg)
        except Exception:
            pass


def run_combined(action, ai_accounts=None, cpc2_accounts=None, source='schedule', log_fn=None):
    """action=on/off. ai_accounts/cpc2_accounts = 각 제어 대상 login_id 리스트.
    두 집합의 합집합을 계정당 1회 로그인으로 순회하며, 멤버십에 맞는 제어만 수행."""
    from django.utils import timezone
    from apps.cpc.models import (CrawlerAccount, GmarketAiAdHistory, Cpc2History,
                                 GmarketCpcAdStatus, CrawlerLog)
    ai_accounts = set(ai_accounts or [])
    cpc2_accounts = set(cpc2_accounts or [])
    union = ai_accounts | cpc2_accounts
    if not union:
        _log(log_fn, '대상 계정 없음 — 종료')
        return

    qs = (CrawlerAccount.objects.filter(platform='gmarket', is_active=True, login_id__in=union)
          .exclude(crawling_status='차단됨'))

    ok, reason = guard.preflight('지마켓광고통합제어', platform='gmarket', wait=True, wait_timeout=1800)
    if not ok:
        _log(log_fn, f'⏭️ 건너뜀 — {reason}')
        return

    guard.clear_control_stop('gmarket')   # 새 실행 — 묵은 중지플래그 제거
    driver = None
    done = 0
    try:
        driver = create_driver()
        try:
            driver.set_page_load_timeout(40); driver.implicitly_wait(3)
        except Exception:
            pass
        for acct in qs:
            if guard.is_control_stop('gmarket'):
                _log(log_fn, '🛑 강제중지 요청 — 중단')
                break
            lid = acct.login_id
            try:
                driver.delete_all_cookies()
                if not _login(driver, lid, acct.password_enc):
                    _log(log_fn, f'[{lid}] 로그인 실패 — 건너뜀')
                    continue
                _log(log_fn, f'[{lid}] 로그인 성공 → 제어 시작')

                # 1) AI 광고 먼저 (같은 세션)
                if lid in ai_accounts:
                    try:
                        results = control_account(driver, lid, action, source, log_fn)
                        for r in results:
                            GmarketAiAdHistory.objects.create(
                                gmarket_id=lid, seller_id=r['seller_id'], group_name=r['group_name'],
                                event_time=timezone.now(), history_type=f'AI {action.upper()}',
                                detail=f'{r["before"]}→{r["after"]} ({"성공" if r["success"] else "실패"})')
                        _log(log_fn, f'[{lid}] AI {action} {len(results)}건')
                    except Exception as e:
                        _log(log_fn, f'[{lid}] AI 제어 오류: {e}')

                # 2) 간편광고(CPC2) 이어서 (재로그인 없이 같은 세션)
                if lid in cpc2_accounts:
                    try:
                        result = control_one(driver, lid, action, source, log_fn)
                        if result and not result.get('skipped'):
                            Cpc2History.objects.create(
                                gmarket_id=lid, action=action,
                                cpc2_before=result.get('before_on', 0),
                                cpc2_after=result.get('after_on', 0), source=source)
                            GmarketCpcAdStatus.objects.update_or_create(
                                gmarket_id=lid,
                                defaults={'cpc2_on': result.get('after_on', 0),
                                          'cpc2_off': result.get('after_off', 0)})
                        _log(log_fn, f'[{lid}] 간편 {action} 완료')
                    except Exception as e:
                        _log(log_fn, f'[{lid}] 간편 제어 오류: {e}')

                done += 1
                CrawlerLog.objects.create(
                    platform='gmarket', level='success',
                    message=f'통합광고제어 {action} (AI+간편)', account_id=lid)
            except Exception as e:
                _log(log_fn, f'[{lid}] 오류: {e}')
                CrawlerLog.objects.create(platform='gmarket', level='error',
                                          message=str(e), account_id=lid)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        stop_display()
        guard.release_global_lock(platform='gmarket')
        guard.clear_control_stop('gmarket')
    _log(log_fn, f'통합광고제어 완료 — {done}개 계정 ({action})')

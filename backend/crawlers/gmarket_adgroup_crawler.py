"""지마켓 CPC 광고그룹별 성과 수집.

소스: ESM 광고센터 ad.esmplus.com/cpc/bidmng/bidmanagement
  - #tbGroupAdStateList       (일반광고 그룹별 성과)
  - #tbSmartGroupAdStateList  (간편광고 그룹별 성과)
컬럼(행 td 인덱스): 1=광고그룹명 2=상태 3=광고수(ON/OFF "0/55") 4=평균순위 5=노출수
  6=클릭수 7=클릭율(%) 8=평균클릭비용 9=총비용(광고비) 10=1일허용예산 11=상품수
저장: GmarketAdGroupPerf (stat_date 기준 계정 단위 삭제후 재삽입 = 멱등).
로그인/쿠키는 gmarket_crawler 재사용(쿠키 재사용으로 IP 안전+속도).
"""
import logging
import re
import time

from django.utils import timezone

logger = logging.getLogger('crawler')


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def _pint(s):
    try:
        return int(re.sub(r'[^\d-]', '', str(s)) or 0)
    except Exception:
        return 0


def _pdec(s):
    try:
        m = re.search(r'-?\d+\.?\d*', str(s).replace(',', ''))
        return float(m.group()) if m else 0.0
    except Exception:
        return 0.0


def _parse_on_off(s):
    # "0/55" → (0, 55)
    m = re.findall(r'\d+', str(s))
    on = int(m[0]) if len(m) >= 1 else 0
    off = int(m[1]) if len(m) >= 2 else 0
    return on, off


def _parse_grid(driver, table_id, ad_type, gid, stat_date, now):
    from selenium.webdriver.common.by import By
    from apps.cpc.models import GmarketAdGroupPerf
    out = []
    els = driver.find_elements(By.ID, table_id)
    if not els:
        return out
    seen = set()
    for tr in els[0].find_elements(By.TAG_NAME, 'tr'):
        tds = tr.find_elements(By.TAG_NAME, 'td')
        if len(tds) < 12:
            continue
        name = (tds[1].text or '').strip()
        if not name or name in seen:
            continue
        seen.add(name)
        on, off = _parse_on_off(tds[3].text)
        out.append(GmarketAdGroupPerf(
            gmarket_id=gid, ad_type=ad_type, stat_date=stat_date,
            ad_group_name=name[:255], status=(tds[2].text or '').strip()[:20],
            ad_on=on, ad_off=off, avg_rank=(tds[4].text or '').strip()[:20],
            impressions=_pint(tds[5].text), clicks=_pint(tds[6].text),
            ctr=_pdec(tds[7].text), avg_click_cost=_pint(tds[8].text),
            total_cost=_pint(tds[9].text), daily_budget=(tds[10].text or '').strip().replace('\n', ' ')[:50],
            product_count=(tds[11].text or '').strip().replace('\n', ' ')[:50],
            collected_at=now))
    return out


def collect_account(driver, account, log_fn=None):
    from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies, CPC_URL
    from apps.cpc.models import GmarketAdGroupPerf
    gid = account.login_id
    now = timezone.now()
    stat_date = timezone.localdate()

    if not _try_cookie_login(driver, account):
        if not _full_login(driver, gid, account.password_enc):
            _log(log_fn, f'[{gid}] 로그인 실패 — 건너뜀')
            return None
        _save_cookies(driver, account)

    driver.get(CPC_URL)
    time.sleep(6)

    rows = []
    rows += _parse_grid(driver, 'tbGroupAdStateList', 'normal', gid, stat_date, now)
    rows += _parse_grid(driver, 'tbSmartGroupAdStateList', 'smart', gid, stat_date, now)

    # stat_date 기준 계정 단위 삭제후 재삽입(멱등)
    GmarketAdGroupPerf.objects.filter(gmarket_id=gid, stat_date=stat_date).delete()
    if rows:
        GmarketAdGroupPerf.objects.bulk_create(rows, batch_size=500)
    spend = sum(r.total_cost for r in rows)
    clicks = sum(r.clicks for r in rows)
    _log(log_fn, f'[{gid}] 광고그룹 {len(rows)}개 / 광고비 {spend:,} / 클릭 {clicks:,}')
    return {'groups': len(rows), 'spend': spend, 'clicks': clicks}


def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).order_by('display_order', 'login_id')
    accounts = [a for a in qs if (not account_filter or a.login_id in account_filter)]

    ok, reason = guard.preflight('지마켓광고그룹', platform='gmarket')
    if not ok:
        _log(log_fn, f'⏭️ 지마켓 광고그룹 성과 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    driver = None
    done = failed = 0
    try:
        for a in accounts:
            blocked, _, _ = guard.is_blocked(platform='gmarket')
            if blocked:
                _log(log_fn, '⛔ 차단 감지 — 중단')
                break
            _log(log_fn, f'[{a.login_id}] 광고그룹 성과 수집...')
            try:
                if driver is None:
                    driver = create_driver(kill_existing=False)
                driver.delete_all_cookies()
                res = collect_account(driver, a, log_fn)
                if res is None:
                    failed += 1
                else:
                    done += 1
                time.sleep(8)   # 보수적 페이싱(IP 차단 방지)
            except Exception as e:
                failed += 1
                _log(log_fn, f'[{a.login_id}] 오류: {str(e)[:120]}')
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        try:
            stop_display(None)
        except Exception:
            pass
        guard.release_global_lock(platform='gmarket')
    _log(log_fn, f'📊 [지마켓 광고그룹 성과 완료] 계정 {done} / 실패 {failed}')
    return {'ok': True, 'accounts': done, 'failed': failed}

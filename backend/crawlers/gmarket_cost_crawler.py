"""지마켓/옥션(ESM) 광고비 수집 — 판매예치금 거래내역(IacSellBalanceUseListSearch).

ESM 판매예치금(현금성)은 통합 → 거래내역 API가 통합 반환. '[광고] CPC 광고구매'가 광고비.
흐름:
  1. signin.esmplus.com 로그인(지마켓 탭) — 계정별
  2. /Member/Settle/IacSellBalanceManagement 진입(같은 origin)
  3. POST IacSellBalanceUseListSearch 를 월 단위로 호출(페이지네이션)
  4. GmarketCostHistory 에 (seller_id, use_date, seq) 누적 — 월 구간 삭제후 재삽입(중복방지)
"""
import json
import logging
import re
import time
from datetime import date, timedelta

from django.utils import timezone

logger = logging.getLogger('crawler')

# 지마켓(Gmkt)·옥션(Iac) 판매예치금 거래내역은 별도 페이지/엔드포인트로 분리됨.
GMKT_PAGE = 'https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement?menuCode=TDM131'
IAC_PAGE = 'https://www.esmplus.com/Member/Settle/IacSellBalanceManagement?menuCode=TDM134'
BALANCE_PAGE = IAC_PAGE  # 하위호환

# 같은 origin에서 거래내역 API 호출. (인자: endpoint, page, sdt, edt, searchAccount=평문 login_id)
# ★ X-Requested-With 헤더 필수 — ESM이 2026-06-18경부터 이 헤더 없는 요청엔 JSON 대신
#   HTML 전체페이지를 반환하도록 변경(응답이상의 근본원인). 페이지가 보내는 요청을 그대로 복제.
#   searchAccount는 평문 login_id($("#sellerId").val() 옵션값) — data-token 경로는 막힘.
_SEARCH_JS = (
    "var cb=arguments[arguments.length-1];var ep=arguments[0];var p=arguments[1];"
    "var sdt=arguments[2];var edt=arguments[3];var acc=arguments[4];"
    "var body='page='+p+'&limit=500&searchAccount='+encodeURIComponent(acc)"
    "+'&searchType=&searchSDT='+sdt+'&searchEDT='+edt"
    "+'&searchKey=0&searchKeyword=&SortFeild=TransDate&SortType=Desc&start=0';"
    "fetch(ep,{method:'POST',credentials:'include',headers:{"
    "'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',"
    "'X-Requested-With':'XMLHttpRequest',"
    "'Accept':'application/json, text/javascript, */*; q=0.01'},body:body})"
    ".then(function(r){return r.text();}).then(function(t){cb(t);}).catch(function(e){cb('ERR:'+e);});"
)


def _norm_gmkt(r):
    """지마켓 GmktSellBalanceUseListSearch 행 → 표준 dict."""
    td = (r.get('TransDate') or '').strip()
    return {'d': td[:10], 'dt': td if len(td) > 10 else None,
            'use_type': r.get('SaveTypeNm') or '',
            'comment': r.get('SdCodeNm') or r.get('Comment') or '',
            'amount': _parse_amt(r.get('SdMoney') if r.get('SdMoney') not in (None, '') else r.get('TransMoney')),
            'related': str(r.get('RefNo') or r.get('GoodsNo') or '')}


def _norm_iac(r):
    """옥션 IacSellBalanceUseListSearch 행 → 표준 dict."""
    ud = (r.get('UseDate') or '').strip()
    return {'d': ud[:10], 'dt': ud if len(ud) > 10 else None,
            'use_type': r.get('UseType') or '',
            'comment': r.get('Comment') or '',
            'amount': _parse_amt(r.get('UseAmnt')),
            'related': str(r.get('OrderNo') or r.get('DeliveryNo') or r.get('PayNo') or '')}


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


# 쿠키 재사용 TTL(시간) — 유효 쿠키면 로그인 생략(로그인 부하↓ = IP 안전 + 속도↑).
COOKIE_TTL_HOURS = 72


def _try_cookie_login(driver, account):
    """저장 쿠키로 빠른 로그인. soffice가 아닌 BALANCE_PAGE 도달(=로그인 유지) 확인. 실패 시 False(풀로그인 폴백)."""
    from datetime import timedelta
    if not account.cookie_data or not account.cookie_saved_at:
        return False
    if timezone.now() - account.cookie_saved_at > timedelta(hours=COOKIE_TTL_HOURS):
        return False
    try:
        driver.get('https://www.esmplus.com/')
        time.sleep(1)
        for cookie in json.loads(account.cookie_data):
            cookie.pop('sameSite', None)
            cookie.pop('expiry', None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        driver.get(BALANCE_PAGE)
        time.sleep(2)
        url = driver.current_url.lower()
        return ('login' not in url and 'signin' not in url and 'logon' not in url)
    except Exception:
        return False


def _save_cookies(driver, account):
    try:
        account.cookie_data = json.dumps(driver.get_cookies())
        account.cookie_saved_at = timezone.now()
        account.save(update_fields=['cookie_data', 'cookie_saved_at'])
    except Exception:
        pass


def _dismiss_esm_popups(driver):
    """로그인 직후 뜨는 소프트 팝업 해제 — '하루동안 보지 않기' 체크 + 레이어 닫기.
    (간헐적 공지/연락처 안내 팝업이 Home 진입을 가리는 경우 대응)"""
    from selenium.webdriver.common.by import By
    try:
        for cb in driver.find_elements(By.XPATH, "//label[contains(.,'하루동안 보지') or contains(.,'오늘 하루')]"):
            if cb.is_displayed():
                driver.execute_script("arguments[0].click();", cb)
    except Exception:
        pass
    try:
        for b in driver.find_elements(By.XPATH,
                "//button[contains(@class,'button__close') or contains(@class,'btn_close') or normalize-space(.)='닫기']"):
            if b.is_displayed():
                driver.execute_script("arguments[0].click();", b)
    except Exception:
        pass


def _esm_logged_in(driver):
    u = driver.current_url.lower()
    return 'login' not in u and 'signin' not in u


def _esm_login(driver, eid, pw):
    """ESM 로그인 — 간헐적 보안/공지 팝업 대응(리다이렉트 폴링 + 소프트팝업 해제 + 재시도).
    sleep(6) 고정 대기로는 Home 리다이렉트 전 실패 오판 + 일부 계정 간헐 보안팝업 차단 발생."""
    from selenium.webdriver.common.by import By
    for attempt in range(3):
        try:
            driver.get('https://www.esmplus.com/')
        except Exception:
            pass
        time.sleep(3)
        if _esm_logged_in(driver):
            _dismiss_esm_popups(driver)
            return True
        # 지마켓 탭 선택 후 id/pw 입력
        for b in driver.find_elements(By.XPATH, "//button[contains(@class,'button__tab')]"):
            if (b.text or '').strip() == '지마켓':
                driver.execute_script("arguments[0].click();", b)
                time.sleep(1)
                break
        try:
            idf = driver.find_element(By.ID, 'typeMemberInputId01')
            pwf = driver.find_element(By.ID, 'typeMemberInputPassword01')
            idf.clear(); idf.send_keys(eid)
            pwf.clear(); pwf.send_keys(pw)
            driver.find_element(By.XPATH, "//button[contains(@class,'button--blue') and contains(.,'로그인')]").click()
        except Exception:
            time.sleep(2)
            continue
        # 로그인 후 Home 리다이렉트 최대 25초 폴링(중간중간 소프트팝업 해제)
        for _ in range(25):
            time.sleep(1)
            if _esm_logged_in(driver):
                _dismiss_esm_popups(driver)
                return True
            _dismiss_esm_popups(driver)
        # 여전히 signin/login이면(하드 인증게이트 등) 다음 시도
        time.sleep(2)
    return _esm_logged_in(driver)


def _classify(comment):
    """차감내역 분류 — 광고비 3종(CPC/AI매출업/서버비용) + 비광고.
    지마켓 SdCodeNm은 소문자('cpc광고구매')라 대소문자 무시 비교."""
    c = comment or ''
    cl = c.lower().replace(' ', '')
    if 'ai매출업' in cl:
        return 'AI매출업'
    if '서버' in c:               # 서버비용/서버이용료
        return '서버비용'
    if 'cpc' in cl:
        return 'CPC'
    if '전환' in c:
        return '예치금전환'
    if '정산' in c or '입금' in c or '적립' in c:
        return '정산'
    return '기타'


# 광고비로 집계할 분류
AD_TYPES = ('CPC', 'AI매출업', '서버비용')


def _parse_amt(v):
    try:
        return int(re.sub(r'[^\d\-]', '', str(v)))
    except Exception:
        return 0


def _month_ranges(d0, d1):
    """[d0,d1]를 월 단위 (시작,끝) 리스트로."""
    out = []
    cur = date(d0.year, d0.month, 1)
    while cur <= d1:
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
        s = max(cur, d0)
        e = min(nxt - timedelta(days=1), d1)
        out.append((s, e))
        cur = nxt
    return out


def _fetch_month(driver, eid, endpoint, sdt, edt, log_fn, normalizer):
    """(rows, ok) 반환. rows=정규화 dict 리스트. ok=False면 수집 실패(응답이상/HTML/ERR).
    정상 빈 달은 ok=True, rows=[]. '실패'와 '진짜 0건'을 구분해 데이터 유실 방지.
    searchAccount=평문 login_id(eid). endpoint별 normalizer로 스키마 흡수."""
    rows = []
    page = 1
    while page <= 200:
        txt = driver.execute_async_script(_SEARCH_JS, endpoint, page, sdt, edt, eid)
        if not txt or txt.startswith('ERR:') or not txt.strip().startswith('{'):
            _log(log_fn, f'[{eid}] {sdt}~{edt} p{page} 응답이상 — 저장 스킵(기존 보존)')
            return rows, False     # 실패: 부분수집 포함 무효 처리
        data = json.loads(txt)
        batch = data.get('data') or []
        if not batch:
            break
        rows.extend(normalizer(r) for r in batch)
        if len(batch) < 500:
            break
        page += 1
        time.sleep(0.5)
    return rows, True


def _save(eid, market, sdt, edt, rows):
    """(seller_id, market) 단위 월 구간 삭제후 재삽입(멱등). seq는 (날짜) 내 순번.
    rows가 비면 삭제하지 않고 기존 보존(응답이상 거짓0건 방어). rows=정규화 dict."""
    from apps.cpc.models import GmarketCostHistory
    from datetime import datetime
    import pytz
    kst = pytz.timezone('Asia/Seoul')
    if not rows:
        return 0
    GmarketCostHistory.objects.filter(
        seller_id=eid, market=market, use_date__gte=sdt, use_date__lte=edt).delete()
    objs = []
    seq_by_date = {}
    for r in rows:
        ud = r.get('d')
        if not ud:
            continue
        d = datetime.strptime(ud[:10], '%Y-%m-%d').date()
        seq = seq_by_date.get(d, 0)
        seq_by_date[d] = seq + 1
        traded = None
        if r.get('dt'):
            try:
                traded = kst.localize(datetime.strptime(r['dt'][:19], '%Y-%m-%d %H:%M:%S'))
            except Exception:
                traded = None
        cmt = (r.get('comment') or '')[:255]
        objs.append(GmarketCostHistory(
            seller_id=eid, market=market, use_date=d, seq=seq, traded_at=traded,
            use_type=(r.get('use_type') or '')[:20],
            transaction_type=_classify(cmt),
            comment=cmt, amount=r.get('amount') or 0,
            related_no=str(r.get('related') or '')[:50]))
    if objs:
        GmarketCostHistory.objects.bulk_create(objs, batch_size=1000)
    return len(objs)


def _collect_account_months(driver, login_id, months, log_fn):
    """마스터·서브 공통 — 지마켓+옥션 월별 거래내역 수집 후 저장. (rows, ad_rows) 반환."""
    acc_rows = acc_ad = 0
    for page_url, endpoint, market, norm in (
        (GMKT_PAGE, 'GmktSellBalanceUseListSearch', 'gmarket', _norm_gmkt),
        (IAC_PAGE, 'IacSellBalanceUseListSearch', 'auction', _norm_iac),
    ):
        driver.get(page_url)
        time.sleep(4)
        for sdt, edt in months:
            rows, ok = _fetch_month(driver, login_id, endpoint, str(sdt), str(edt), log_fn, norm)
            if not ok:
                continue
            n = _save(login_id, market, sdt, edt, rows)
            ad = sum(1 for r in rows if _classify(r.get('comment')) in AD_TYPES)
            acc_rows += n
            acc_ad += ad
            _log(log_fn, f'[{login_id}] {market} {sdt:%Y-%m}: {n}건 (광고 {ad})')
            time.sleep(0.5)
    return acc_rows, acc_ad


def run_all_accounts(log_fn=None, account_filter=None, date_from=None, date_to=None, wait=False):
    """지마켓 계정의 ESM 판매예치금 거래내역(광고비 포함)을 월 단위 수집.
    wait=True면 다른 지마켓 크롤이 돌고 있어도 끝날 때까지 대기 후 수집(스킵 안 함) — 거래내역 누락 방지.
    전략: 모든 계정 독립 로그인 시도 → 실패+origin_id 있으면 마스터 세션으로 재수집(rejoice235/236 대응).
          starvisi처럼 origin_id 있어도 독립 로그인 가능한 계정은 그대로 독립 처리."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display

    d1 = date_to or timezone.localdate()
    d0 = date_from or date(d1.year, 1, 1)
    ok, reason = guard.preflight('지마켓광고비', platform='gmarket', wait=wait, wait_timeout=1800)
    if not ok:
        _log(log_fn, f'⏭️ 지마켓 광고비 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    accounts = [a for a in qs if (not account_filter or a.login_id in account_filter)]
    months = _month_ranges(d0, d1)
    done = failed = total_rows = ad_rows = 0
    # 로그인 실패한 서브 계정 → 마스터 처리 후 재수집
    login_failed_subs = []
    driver = None
    try:
        for a in accounts:
            blocked, _, _ = guard.is_blocked(platform='gmarket')
            if blocked:
                _log(log_fn, '⛔ 차단 감지 — 중단')
                break
            _log(log_fn, f'[{a.login_id}] ESM 로그인...')
            try:
                if driver is None:
                    driver = create_driver(kill_existing=False)
                driver.delete_all_cookies()
                if _try_cookie_login(driver, a):
                    _log(log_fn, f'[{a.login_id}] 쿠키 로그인')
                elif _esm_login(driver, a.login_id, a.password_enc):
                    _log(log_fn, f'[{a.login_id}] 풀 로그인')
                    _save_cookies(driver, a)
                else:
                    # 로그인 실패 — origin_id 있으면 마스터 세션 대기, 없으면 건너뜀
                    if a.gmarket_origin_id:
                        _log(log_fn, f'[{a.login_id}] 로그인 실패 → 마스터({a.gmarket_origin_id}) 세션 대기')
                        login_failed_subs.append(a)
                    else:
                        _log(log_fn, f'[{a.login_id}] 로그인 실패 — 건너뜀')
                        failed += 1
                    continue
                acc_rows, acc_ad = _collect_account_months(driver, a.login_id, months, log_fn)
                total_rows += acc_rows
                ad_rows += acc_ad
                done += 1
                _log(log_fn, f'[{a.login_id}] 완료 — 거래 {acc_rows}건 (광고 {acc_ad}건)')
                # 이 계정이 마스터인 로그인 실패 서브들 즉시 수집
                pending = [s for s in login_failed_subs if s.gmarket_origin_id == a.login_id]
                for sub in pending:
                    login_failed_subs.remove(sub)
                    _log(log_fn, f'[{sub.login_id}] 서브 수집 (마스터 세션)...')
                    try:
                        s_rows, s_ad = _collect_account_months(driver, sub.login_id, months, log_fn)
                        total_rows += s_rows
                        ad_rows += s_ad
                        _log(log_fn, f'[{sub.login_id}] 서브 완료 — 거래 {s_rows}건 (광고 {s_ad}건)')
                    except Exception as se:
                        _log(log_fn, f'[{sub.login_id}] 서브 오류: {str(se)[:120]}')
            except Exception as e:
                _log(log_fn, f'[{a.login_id}] 오류: {str(e)[:140]}')
                failed += 1
            time.sleep(3)
        # 마스터가 루프에 없거나 순서상 먼저 온 서브 계정 — 마스터 재로그인 후 수집
        if login_failed_subs:
            master_map = {a.login_id: a for a in accounts}
            processed_masters = set()
            for sub in login_failed_subs:
                mid = sub.gmarket_origin_id
                ma = master_map.get(mid)
                if not ma:
                    _log(log_fn, f'[{sub.login_id}] 마스터({mid}) 미발견 — 건너뜀')
                    failed += 1
                    continue
                if mid not in processed_masters:
                    _log(log_fn, f'[{mid}] 마스터 재로그인 (미수집 서브 처리)...')
                    driver.delete_all_cookies()
                    if not (_try_cookie_login(driver, ma) or _esm_login(driver, ma.login_id, ma.password_enc)):
                        _log(log_fn, f'[{mid}] 재로그인 실패 — 서브 건너뜀')
                        failed += sum(1 for s in login_failed_subs if s.gmarket_origin_id == mid)
                        continue
                    processed_masters.add(mid)
                _log(log_fn, f'[{sub.login_id}] 서브 수집 (재로그인 마스터 세션)...')
                try:
                    s_rows, s_ad = _collect_account_months(driver, sub.login_id, months, log_fn)
                    total_rows += s_rows
                    ad_rows += s_ad
                    _log(log_fn, f'[{sub.login_id}] 서브 완료 — 거래 {s_rows}건')
                except Exception as e:
                    _log(log_fn, f'[{sub.login_id}] 오류: {str(e)[:120]}')
                    failed += 1
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        guard.release_global_lock(platform='gmarket')
        try:
            stop_display()
        except Exception:
            pass
    _log(log_fn, f'💳 [지마켓 광고비 완료] 계정 {done} / 거래 {total_rows}건 / 광고 {ad_rows}건 / 실패 {failed}')
    return {'ok': True, 'accounts': done, 'rows': total_rows, 'ad_rows': ad_rows, 'failed': failed}

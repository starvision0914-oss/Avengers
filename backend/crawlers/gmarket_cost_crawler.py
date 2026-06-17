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

BALANCE_PAGE = 'https://www.esmplus.com/Member/Settle/IacSellBalanceManagement?menuCode=TDM134'

# 같은 origin(www.esmplus.com/Member/Settle/)에서 거래내역 API 호출
_SEARCH_JS = (
    "var cb=arguments[arguments.length-1];var p=arguments[0];var sdt=arguments[1];var edt=arguments[2];"
    # searchAccount는 #sellerId 옵션의 data-token(암호화 계정id). 평문 login_id는 '선택된' 계정만
    # 통과되고 서브계정은 HTML에러 → 토큰을 URL인코딩해 넘겨야 비선택 서브도 조회됨.
    "var body='page='+p+'&limit=500&searchAccount='+encodeURIComponent(arguments[3])+'&searchType=0&searchSDT='+sdt"
    "+'&searchEDT='+edt+'&searchKey=0&searchKeyword=&SortFeild=OrderDate&SortType=Asc';"
    "fetch('IacSellBalanceUseListSearch',{method:'POST',credentials:'include',"
    "headers:{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},body:body})"
    ".then(function(r){return r.text();}).then(function(t){cb(t);}).catch(function(e){cb('ERR:'+e);});"
)


def _get_seller_tokens(driver):
    """#sellerId 드롭다운에서 {login_id: data-token} 추출.
    ESM 거래조회(searchAccount)는 이 data-token으로 해야 비선택 서브계정도 조회됨."""
    try:
        return driver.execute_script(
            "var m={};document.querySelectorAll('#sellerId option').forEach("
            "function(o){var v=(o.value||'').trim();if(v)m[v]=o.getAttribute('data-token')||v;});return m;") or {}
    except Exception:
        return {}


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
    """차감내역 분류 — 광고비 3종(CPC/AI매출업/서버비용) + 비광고."""
    c = comment or ''
    if 'AI매출업' in c or 'AI 매출업' in c:
        return 'AI매출업'
    if '서버' in c:               # 서버비용/서버이용료
        return '서버비용'
    if 'CPC' in c:
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


def _fetch_month(driver, eid, sdt, edt, log_fn, search_val=None):
    """(rows, ok) 반환. ok=False면 수집 실패(응답이상/HTML/ERR) → 호출측에서 저장(삭제) 금지.
    정상 빈 달은 (그대로) ok=True, rows=[]. '실패'와 '진짜 0건'을 구분해 데이터 유실 방지.
    search_val: searchAccount로 넘길 값(data-token). 없으면 eid(평문, 선택된 계정만 통과)."""
    sv = search_val or eid
    rows = []
    page = 1
    while page <= 200:
        txt = driver.execute_async_script(_SEARCH_JS, page, sdt, edt, sv)
        if not txt or txt.startswith('ERR:') or not txt.strip().startswith('{'):
            _log(log_fn, f'[{eid}] {sdt}~{edt} p{page} 응답이상 — 저장 스킵(기존 보존)')
            return rows, False     # 실패: 부분수집 포함 무효 처리
        data = json.loads(txt)
        batch = data.get('data') or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 500:
            break
        page += 1
        time.sleep(0.5)
    return rows, True


def _save(eid, sdt, edt, rows):
    """월 구간 삭제후 재삽입(멱등). seq는 (날짜) 내 순번.
    rows가 비면 삭제하지 않고 기존 보존 — 거래원장은 append-only라 비어질 일이 없으므로
    빈 결과(응답이상/세션throttle로 인한 거짓 0건)로 기존 데이터를 지우지 않게 방어."""
    from apps.cpc.models import GmarketCostHistory
    from datetime import datetime
    if not rows:
        return 0
    GmarketCostHistory.objects.filter(seller_id=eid, use_date__gte=sdt, use_date__lte=edt).delete()
    objs = []
    seq_by_date = {}
    for r in rows:
        ud = r.get('UseDate')
        if not ud:
            continue
        d = datetime.strptime(ud[:10], '%Y-%m-%d').date()
        seq = seq_by_date.get(d, 0)
        seq_by_date[d] = seq + 1
        cmt = (r.get('Comment') or '')[:255]
        rel = str(r.get('OrderNo') or r.get('DeliveryNo') or r.get('PayNo') or '')[:50]
        objs.append(GmarketCostHistory(
            seller_id=eid, use_date=d, seq=seq,
            use_type=(r.get('UseType') or '')[:20],
            transaction_type=_classify(cmt),
            comment=cmt, amount=_parse_amt(r.get('UseAmnt')), related_no=rel))
    if objs:
        GmarketCostHistory.objects.bulk_create(objs, batch_size=1000)
    return len(objs)


def run_all_accounts(log_fn=None, account_filter=None, date_from=None, date_to=None):
    """지마켓 계정의 ESM 판매예치금 거래내역(광고비 포함)을 월 단위 수집."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display

    d1 = date_to or timezone.localdate()
    d0 = date_from or date(d1.year, 1, 1)
    ok, reason = guard.preflight('지마켓광고비', platform='gmarket')
    if not ok:
        _log(log_fn, f'⏭️ 지마켓 광고비 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    accounts = [a for a in qs if (not account_filter or a.login_id in account_filter)]
    months = _month_ranges(d0, d1)
    done = failed = total_rows = ad_rows = 0
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
                # 쿠키 재사용 우선 → 실패 시 풀로그인 후 쿠키 저장 (IP 안전: 로그인 횟수 최소화)
                if _try_cookie_login(driver, a):
                    _log(log_fn, f'[{a.login_id}] 쿠키 로그인')
                else:
                    if not _esm_login(driver, a.login_id, a.password_enc):
                        _log(log_fn, f'[{a.login_id}] 로그인 실패 — 건너뜀')
                        failed += 1
                        continue
                    _save_cookies(driver, a)
                driver.get(BALANCE_PAGE)
                time.sleep(4)
                # #sellerId 드롭다운에서 이 계정의 data-token 확보(서브계정도 조회되게).
                # 드롭다운이 AJAX로 늦게 차므로 토큰 보일 때까지 잠깐 폴링.
                tokens, search_val = {}, None
                for _ in range(6):
                    tokens = _get_seller_tokens(driver)
                    search_val = tokens.get(a.login_id)
                    if search_val:
                        break
                    time.sleep(1)
                if search_val and search_val != a.login_id:
                    _log(log_fn, f'[{a.login_id}] 토큰 확보({len(tokens)}계정, 서브 조회용)')
                elif not search_val:
                    _log(log_fn, f'[{a.login_id}] ⚠️ 드롭다운에 토큰 없음 — 평문으로 시도')
                acc_rows = acc_ad = 0
                for sdt, edt in months:
                    rows, ok = _fetch_month(driver, a.login_id, str(sdt), str(edt), log_fn, search_val=search_val)
                    if not ok:
                        # 수집 실패월은 삭제·저장하지 않고 기존 데이터 보존(유실 방지)
                        continue
                    n = _save(a.login_id, sdt, edt, rows)
                    acc_rows += n
                    acc_ad += sum(1 for r in rows if _classify(r.get('Comment')) in AD_TYPES)
                    _log(log_fn, f'[{a.login_id}] {sdt:%Y-%m}: {n}건 (광고 {sum(1 for r in rows if _classify(r.get("Comment")) in AD_TYPES)})')
                    time.sleep(0.5)
                total_rows += acc_rows
                ad_rows += acc_ad
                done += 1
                _log(log_fn, f'[{a.login_id}] 완료 — 거래 {acc_rows}건 (광고 {acc_ad}건)')
            except Exception as e:
                _log(log_fn, f'[{a.login_id}] 오류: {str(e)[:140]}')
                failed += 1
            time.sleep(3)
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

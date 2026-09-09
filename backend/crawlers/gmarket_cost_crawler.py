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
    """지마켓 GmktSellBalanceUseListSearch 행 → 표준 dict.
    금액은 판매예치금 발생액(SdMoney) + 광고성이머니 발생액(AdMoney) 합산 — 'AI Product AD 광고구매'류는
    SdMoney가 0이고 AdMoney에만 실제 차감액이 찍혀 예전 코드(SdMoney 우선)로는 전부 0원으로 누락됐음
    (2026-09-09 사용자 지적으로 발견). TransMoney가 이미 SdMoney+AdMoney와 정확히 일치하는 필드라
    실측(dlwodb777 9일치 238건 전수 검증, 불일치 0건)로 확인해 그대로 사용."""
    td = (r.get('TransDate') or '').strip()
    return {'d': td[:10], 'dt': td if len(td) > 10 else None,
            'use_type': r.get('SaveTypeNm') or '',
            'comment': r.get('SdCodeNm') or r.get('Comment') or '',
            'amount': int(float(r.get('TransMoney') or 0)),
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
        _dismiss_esm_popups(driver)
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
    (간헐적 공지/연락처 안내 팝업이 Home 진입을 가리는 경우 대응)
    ★ 팝업이 없는(대부분의) 경우 find_elements 3회가 전역 implicit_wait(10초)를 매번 다 채워서
    호출 1번에 최대 30초가 걸렸다(2026-08-23 실측 30.08s → 0.09s). 팝업은 있으면 즉시 렌더되므로
    이 함수 안에서만 implicit_wait를 0으로 낮췄다가 복원한다."""
    from selenium.webdriver.common.by import By
    try:
        driver.implicitly_wait(0)
    except Exception:
        pass
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
    # '고객 응대 연락처 인증 및 변경' 모달 — X버튼/닫기 클래스에 안 걸려서 화면을 계속 가리며
    # 이후 로그인 폼 조작이 전부 막혀 무한 대기처럼 보였음(rejoice987/911, 2026-07-08).
    # ARS 인증을 자동 제출하면 안 되므로 '취소'만 클릭(체크박스/확인 버튼은 건드리지 않음).
    try:
        for h in driver.find_elements(By.XPATH, "//*[contains(text(),'고객 응대 연락처 인증')]"):
            if h.is_displayed():
                for b in driver.find_elements(By.XPATH, "//button[normalize-space()='취소']"):
                    if b.is_displayed():
                        driver.execute_script("arguments[0].click();", b)
                break
    except Exception:
        pass
    finally:
        try:
            driver.implicitly_wait(10)
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
    지마켓 SdCodeNm은 소문자('cpc광고구매')라 대소문자 무시 비교.
    2026-08-24부터 'AI매출업'이 'AI Product AD 광고구매'로 명칭 변경(계정별 순차 전환,
    2026-08-28 이후 rejoice911 등에서 AI매출업 완전 소멸·AI Product AD로 대체 실측) —
    안 잡으면 광고비 집계에서 통째로 누락(기타 처리)됨. AI매출업과 동일 예산이므로 같은 분류로 합산."""
    c = comment or ''
    cl = c.lower().replace(' ', '')
    if 'ai매출업' in cl or 'aiproductad' in cl:
        return 'AI매출업'
    if '서버' in c:               # 서버비용/서버이용료
        return '서버비용'
    if 'cpc' in cl:
        return 'CPC'
    if '전시권' in c or '노출보장형' in c or '키워드플러스' in c:  # 키워드/노출 유상상품 — CPC류로 합산
        return 'CPC'
    if '전환' in c:
        return '예치금전환'
    if '정산' in c or '입금' in c or '적립' in c:
        return '정산'
    # 안전망: 위 규칙에 못 걸려도 '광고'/영문 단어 'AD'가 있으면 광고비로 집계.
    # 지마켓이 광고상품명을 바꿀 때마다(AI매출업→AI Product AD 사례) 개별 규칙 추가가 늦어
    # 그 사이 누락되는 걸 방지 — 이름이 또 바뀌어도 '광고'/'AD' 문구만 있으면 잡힘.
    if '광고' in c or 'AD' in c.upper().split():
        return 'CPC'
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


def _select_seller_ui(driver, target_login_id, log_fn=None):
    """계정선택 위젯(/html/body/div[1]/div[1]/div[3]) 클릭 → 드롭다운 목록에서 대상 계정명
    클릭 → 검색버튼 클릭. (2026-09-05, 사용자 지적) fetch()의 searchAccount 파라미터만 믿고
    UI에서 계정을 선택하지 않은 채 조회하면, 특히 마스터 세션으로 서브계정을 수집할 때 실제로
    어느 판매자 데이터가 반환되는지 서버측 세션 스코프가 보장되지 않는다 — 반드시 이 위젯으로
    명시적으로 계정을 선택한 뒤 검색해야 정확한 판매자 거래내역이 조회된다.
    단일 아이디 계정은 이 위젯 자체가 없을 수 있어(선택할 서브가 없음), 그 경우 조용히
    스킵하고 기존 fetch 방식으로 진행한다(치명적 실패로 취급하지 않음)."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        opener = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[1]/div[3]')))
        driver.execute_script("arguments[0].click();", opener)
        time.sleep(0.5)
    except Exception:
        return False   # 위젯 없음(단일아이디) — 정상, 기존 fetch로 계속

    try:
        candidates = driver.find_elements(By.XPATH, f"//*[contains(text(), '{target_login_id}')]")
        clicked = False
        for c in candidates:
            try:
                if c.is_displayed():
                    driver.execute_script("arguments[0].click();", c)
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            _log(log_fn, f'[{target_login_id}] 계정선택 목록에서 항목을 찾지 못함 — 기존 fetch로 진행')
            return False
        time.sleep(0.5)
        for by, sel in [(By.ID, 'btnSearch'), (By.XPATH, '//*[@id="btnSearch"]/img'),
                         (By.XPATH, "//button[contains(.,'검색')]"),
                         (By.XPATH, "//a[contains(.,'검색')]")]:
            try:
                btn = driver.find_element(by, sel)
                driver.execute_script("arguments[0].click();", btn)
                break
            except Exception:
                continue
        time.sleep(1.5)
        _log(log_fn, f'[{target_login_id}] 계정선택 UI로 판매자 전환 완료')
        return True
    except Exception as e:
        _log(log_fn, f'[{target_login_id}] 계정선택 UI 실패: {str(e)[:120]} — 기존 fetch로 진행')
        return False


def _get_auction_seller_id(login_id):
    """옥션 seller_id 반환 — auction_seller_id 설정 시 그 값, 없으면 login_id."""
    try:
        from apps.cpc.models import CrawlerAccount
        a = CrawlerAccount.objects.filter(platform='gmarket', login_id=login_id).values_list('auction_seller_id', flat=True).first()
        return a or login_id
    except Exception:
        return login_id


def _collect_account_months(driver, login_id, months, log_fn):
    """마스터·서브 공통 — 지마켓+옥션 월별 거래내역 수집 후 저장. (rows, ad_rows) 반환.
    ★ fetch()는 credentials:include라 쿠키가 도메인 단위로 붙고, endpoint도
    '/Member/Settle/' 하위 상대경로라 그 디렉터리 밑 아무 페이지에서나 호출해도 된다
    (2026-08-23 실측: 페이지이동 없이 즉시 fetch 0.13s). 계정당 두 번씩(지마켓+옥션) 정산페이지를
    풀 로딩하던 게 실제 지연의 대부분이었음 — 이제 이 함수 시작 시 한 번만(필요하면) 진입한다."""
    acc_rows = acc_ad = 0
    auction_sid = _get_auction_seller_id(login_id)
    if '/member/settle/' not in driver.current_url.lower():
        driver.get(GMKT_PAGE)
        time.sleep(1.5)
        _dismiss_esm_popups(driver)
    # (2026-09-05) 매 호출마다(같은 드라이버로 서브 여러 개를 연달아 처리하는 마스터세션 경로
    # 포함) UI에서 명시적으로 이 계정을 선택 — fetch()의 searchAccount 파라미터만으로는
    # 실제 조회 스코프가 보장 안 됨. 단일아이디 계정은 위젯이 없어 조용히 스킵될 수 있음.
    _select_seller_ui(driver, login_id, log_fn)
    for endpoint, market, norm in (
        ('GmktSellBalanceUseListSearch', 'gmarket', _norm_gmkt),
        ('IacSellBalanceUseListSearch', 'auction', _norm_iac),
    ):
        save_id = auction_sid if market == 'auction' else login_id
        for sdt, edt in months:
            rows, ok = _fetch_month(driver, login_id, endpoint, str(sdt), str(edt), log_fn, norm)
            if not ok:
                continue
            n = _save(save_id, market, sdt, edt, rows)
            ad = sum(1 for r in rows if _classify(r.get('comment')) in AD_TYPES)
            acc_rows += n
            acc_ad += ad
            _log(log_fn, f'[{login_id}→{save_id}] {market} {sdt:%Y-%m}: {n}건 (광고 {ad})')
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
    ok, reason = guard.preflight('지마켓광고비', platform='gmarket', wait=wait, wait_timeout=10800)
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
    # 계정당 하드 타임아웃(초) — 느린 계정 1개가 전체 배치를 지연시키는 걸 막는다(30계정×1분 예산 보장).
    # 초과 시 이 계정은 이번 회차엔 스킵되지만 GmarketCostHistory가 멱등 upsert라 다음 회차에 다시 잡힌다.
    PER_ACCOUNT_TIMEOUT = 60
    import concurrent.futures as _cf
    _executor = _cf.ThreadPoolExecutor(max_workers=1)
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
                    # 페이지로드 무한대기 방지(기본 300s) — 계정 하나가 응답없음 상태면
                    # 그대로 15~25분씩 멈춰 전체 배치를 막았음(dlrmsgh012, 2026-07-14).
                    driver.set_page_load_timeout(25)

                def _do_account(_driver=driver, _a=a):
                    _driver.delete_all_cookies()
                    if _try_cookie_login(_driver, _a):
                        _log(log_fn, f'[{_a.login_id}] 쿠키 로그인')
                    elif _esm_login(_driver, _a.login_id, _a.password_enc):
                        _log(log_fn, f'[{_a.login_id}] 풀 로그인')
                        _save_cookies(_driver, _a)
                    else:
                        return None  # 로그인 실패
                    rows, ad = _collect_account_months(_driver, _a.login_id, months, log_fn)
                    return rows, ad

                try:
                    result = _executor.submit(_do_account).result(timeout=PER_ACCOUNT_TIMEOUT)
                except _cf.TimeoutError:
                    _log(log_fn, f'[{a.login_id}] ⏱️ {PER_ACCOUNT_TIMEOUT}초 초과 — 스킵(다음 회차에 재시도)')
                    failed += 1
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = None
                    # 백그라운드에서 여전히 도는 스레드는 버려두고 다음 계정으로 계속 진행
                    continue

                if result is None:
                    # 로그인 실패 — origin_id 있으면 마스터 세션 대기, 없으면 건너뜀
                    if a.gmarket_origin_id:
                        _log(log_fn, f'[{a.login_id}] 로그인 실패 → 마스터({a.gmarket_origin_id}) 세션 대기')
                        login_failed_subs.append(a)
                    else:
                        _log(log_fn, f'[{a.login_id}] 로그인 실패 — 건너뜀')
                        failed += 1
                    continue
                acc_rows, acc_ad = result
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
                        s_rows, s_ad = _executor.submit(
                            _collect_account_months, driver, sub.login_id, months, log_fn
                        ).result(timeout=PER_ACCOUNT_TIMEOUT)
                        total_rows += s_rows
                        ad_rows += s_ad
                        _log(log_fn, f'[{sub.login_id}] 서브 완료 — 거래 {s_rows}건 (광고 {s_ad}건)')
                    except _cf.TimeoutError:
                        _log(log_fn, f'[{sub.login_id}] ⏱️ 서브 {PER_ACCOUNT_TIMEOUT}초 초과 — 스킵')
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

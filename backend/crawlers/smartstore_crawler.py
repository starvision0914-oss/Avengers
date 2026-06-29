"""
스마트스토어센터 판매 통계 + 광고비 크롤러

로그인: https://accounts.commerce.naver.com/login
판매통계 API: sell.smartstore.naver.com 내부 XHR
광고비: 스마트스토어 광고센터(NSA) 크롤링
"""
import time
import json
import logging
import re
import os
from datetime import date, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger('crawler')

LOGIN_URL = (
    'https://accounts.commerce.naver.com/login'
    '?url=https%3A%2F%2Fsell.smartstore.naver.com%2F%23%2Flogin-callback'
)
STATS_BASE = 'https://sell.smartstore.naver.com'


# ──────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────

def _parse_int(text):
    if not text:
        return 0
    cleaned = re.sub(r'[^\d\-]', '', str(text).strip())
    return int(cleaned) if cleaned else 0


# ──────────────────────────────────────────
# 로그인
# ──────────────────────────────────────────

def login_smartstore(driver, login_id, login_pw, log_fn=None):
    log = log_fn or logger.info

    log(f'[스마트] 로그인 시도: {login_id}')
    driver.get(LOGIN_URL)
    time.sleep(3)

    try:
        # ID 입력
        id_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="text" or @id="id"]'))
        )
        id_input.click()
        time.sleep(0.3)
        id_input.clear()
        id_input.send_keys(login_id)
        time.sleep(0.3)

        # PW 입력
        pw_input = driver.find_element(By.XPATH, '//input[@type="password"]')
        pw_input.click()
        time.sleep(0.3)
        pw_input.clear()
        pw_input.send_keys(login_pw)
        time.sleep(0.3)

        pw_input.send_keys(Keys.RETURN)
        time.sleep(8)

    except Exception as e:
        log(f'[스마트] 로그인 입력 실패: {e}')
        return False

    current = driver.current_url
    if 'sell.smartstore' in current or 'login-callback' in current:
        log(f'[스마트] 로그인 성공')
        # sell.smartstore.naver.com 메인으로 명시 이동 (accounts 도메인 잔류 방지)
        if 'sell.smartstore' not in current:
            driver.get('https://sell.smartstore.naver.com/#/home')
            time.sleep(5)
        else:
            time.sleep(3)
        # 모달 팝업 닫기 (스토어 전환 클릭 방해 방지)
        try:
            driver.execute_script("""
                var modals = document.querySelectorAll('[uib-modal-window], .modal.in');
                modals.forEach(function(m) { m.style.display = 'none'; });
                var backdrops = document.querySelectorAll('.modal-backdrop');
                backdrops.forEach(function(b) { b.remove(); });
                document.body.classList.remove('modal-open');
            """)
            time.sleep(0.5)
        except Exception:
            pass
        return True

    log(f'[스마트] 로그인 실패? URL: {current}')
    return False


# ──────────────────────────────────────────
# 스토어 전환 (복수 스토어 계정)
# ──────────────────────────────────────────

def switch_store(driver, store_slug, log_fn=None):
    """store_slug가 있으면 해당 스토어로 전환 후 True 반환."""
    log = log_fn or logger.info
    if not store_slug:
        return True

    try:
        # 스토어 전환 버튼 클릭
        store_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[contains(@class,"store-switch") or contains(@id,"_gnb_nav")]//li[2]/a')
            )
        )
        store_btn.click()
        time.sleep(2)

        items = driver.find_elements(By.CSS_SELECTOR, '[class*="text-title"], [class*="store-name"]')
        for item in items:
            if store_slug in item.text.strip():
                item.click()
                time.sleep(4)
                log(f'[스마트] 스토어 전환: {store_slug}')
                return True

        log(f'[스마트] 스토어 못 찾음: {store_slug}')
        return False
    except Exception as e:
        log(f'[스마트] 스토어 전환 오류: {e}')
        return True  # 단일 스토어면 전환 없이 진행


# ──────────────────────────────────────────
# GraphQL 헬퍼
# ──────────────────────────────────────────

SETTLE_PAGE_URL = 'https://sell.smartstore.naver.com/e/v3/settlemgt/sellerdailysettle'
GRAPHQL_URL = 'https://sell.smartstore.naver.com/api/graphql'


def _execute_fetch(driver, url, method='GET', body=None):
    """브라우저 컨텍스트에서 fetch 실행 — 세션 쿠키 자동 포함."""
    script = """
    var url = arguments[0], method = arguments[1], body = arguments[2];
    return fetch(url, {
        method: method,
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
        body: body ? JSON.stringify(body) : undefined,
        credentials: 'include',
    }).then(r => r.json()).catch(() => null);
    """
    try:
        result = driver.execute_script(script, url, method, body)
        return result
    except Exception:
        return None


def _cdp_enable(driver):
    try:
        driver.execute_cdp_cmd('Network.enable', {})
    except Exception:
        pass


def _cdp_pop_settle_elements(driver):
    """CDP 버퍼에서 DailySettleList 응답을 꺼내 반환 (최신 것 우선)."""
    logs = driver.get_log('performance')
    for entry in reversed(logs):
        try:
            msg = json.loads(entry['message'])['message']
            if msg.get('method') != 'Network.responseReceived':
                continue
            resp = msg['params']['response']
            if 'graphql' not in resp.get('url', ''):
                continue
            req_id = msg['params']['requestId']
            body_resp = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
            data = json.loads(body_resp.get('body', '{}'))
            dl = (data.get('data') or {}).get('DailySettleList')
            if dl and dl.get('elements'):
                return dl['elements'], dl.get('pagination') or {}
        except Exception:
            pass
    return [], {}


def _calendar_click_day(driver, day: int):
    """열려있는 react-datepicker에서 day(일) 클릭."""
    return driver.execute_script("""
        var days = Array.from(document.querySelectorAll('.react-datepicker__day'));
        var t = days.find(d =>
            parseInt(d.textContent.trim()) === arguments[0]
            && !d.className.includes('outside-month')
            && !d.className.includes('disabled')
        );
        if (t) { t.click(); return true; }
        return false;
    """, day)


def _calendar_navigate(driver, target_year: int, target_month: int):
    """캘린더를 target_year/month가 보일 때까지 앞뒤로 이동."""
    for _ in range(30):
        # 현재 표시 월을 day aria-label에서 파악
        label = driver.execute_script("""
            var day = document.querySelector(
                '.react-datepicker__day:not(.react-datepicker__day--outside-month)');
            return day ? day.getAttribute('aria-label') : null;
        """)
        if not label:
            break
        import re as _re
        m = _re.search(r'(\w+)\s+(\d+)\w*,\s+(\d{4})', label)
        if not m:
            break
        months_en = ['january','february','march','april','may','june',
                     'july','august','september','october','november','december']
        cur_month = months_en.index(m.group(1).lower()) + 1
        cur_year = int(m.group(3))

        if cur_year == target_year and cur_month == target_month:
            return True

        diff = (target_year * 12 + target_month) - (cur_year * 12 + cur_month)
        if diff < 0:
            btn = driver.execute_script(
                "return document.querySelector('.react-datepicker__navigation--previous');")
        else:
            btn = driver.execute_script(
                "return document.querySelector('.react-datepicker__navigation--next');")
        if not btn:
            break
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.3)
    return False


def _select_date_with_calendar(driver, input_index: int, target_date):
    """input_index(0=시작, 1=종료) 입력칸을 클릭해 달력을 열고 target_date 선택."""
    inputs = driver.find_elements(By.CSS_SELECTOR, 'input._Bp621VcVyg')
    if input_index >= len(inputs):
        return False
    inputs[input_index].click()
    time.sleep(1)
    _calendar_navigate(driver, target_date.year, target_date.month)
    return _calendar_click_day(driver, target_date.day)


def _extract_merchant_no_from_perf(driver):
    """performance 로그에서 merchantNo 추출."""
    try:
        logs = driver.get_log('performance')
        for entry in reversed(logs):
            msg = json.loads(entry['message'])
            method = msg.get('message', {}).get('method', '')
            if method == 'Network.requestWillBeSent':
                req = msg['message']['params'].get('request', {})
                if GRAPHQL_URL in req.get('url', ''):
                    body = req.get('postData', '')
                    if body:
                        bd = json.loads(body)
                        merchant_no = bd.get('variables', {}).get('merchantNo', '')
                        if merchant_no:
                            return merchant_no
    except Exception:
        pass
    return ''


def _extract_merchant_no_from_js(driver):
    """AngularJS rootScope 또는 window에서 merchantNo 직접 추출."""
    try:
        result = driver.execute_script("""
        try {
            var inj = angular.element(document.body).injector();
            var services = ['SellerChannelService','sellerService','SellerService',
                            'AccountService','MerchantService','channelService'];
            for (var s of services) {
                try {
                    var svc = inj.get(s);
                    if (svc && (svc.merchantNo || svc.getMerchantNo)) {
                        return String(svc.merchantNo || svc.getMerchantNo());
                    }
                } catch(e) {}
            }
            var rs = inj.get('$rootScope');
            if (rs && rs.merchantNo) return String(rs.merchantNo);
            if (rs && rs.seller && rs.seller.merchantNo) return String(rs.seller.merchantNo);
        } catch(e) {}
        // URL에서 추출 시도
        var m = location.hash.match(/merchantNo[=/]([0-9]+)/);
        if (m) return m[1];
        return null;
        """)
        return result or ''
    except Exception:
        return ''


def fetch_merchant_no(driver, account, log_fn=None):
    """merchantNo를 확보하고 DB에 저장. 이미 있으면 재사용."""
    log = log_fn or logger.info

    if account.merchant_no:
        return account.merchant_no

    log('[스마트] merchantNo 탐색 중...')

    # 1차: 정산 페이지 이동 후 performance 로그에서 추출
    try:
        driver.execute_script(
            "angular.element(document.body).injector().get('$state')"
            ".go('main.naverpay_settlemgt_sellerdailysettle')"
        )
    except Exception:
        driver.get('https://sell.smartstore.naver.com/#/naverpay/settlemgt/sellerdailysettle')
    time.sleep(6)

    merchant_no = _extract_merchant_no_from_perf(driver)

    # 2차: 주문통계 페이지에서 시도 (정산 데이터 없는 계정 대비)
    if not merchant_no:
        try:
            driver.execute_script(
                "angular.element(document.body).injector().get('$state').go('main.orderstats')"
            )
        except Exception:
            driver.get('https://sell.smartstore.naver.com/#/orderstats')
        time.sleep(5)
        merchant_no = _extract_merchant_no_from_perf(driver)

    # 3차: JavaScript로 직접 추출
    if not merchant_no:
        merchant_no = _extract_merchant_no_from_js(driver)

    if merchant_no:
        account.merchant_no = merchant_no
        account.save(update_fields=['merchant_no'])
        log(f'[스마트] merchantNo={merchant_no} 저장')
    else:
        log('[스마트] merchantNo 추출 실패')
    return merchant_no


# ──────────────────────────────────────────
# 판매 통계 (달력 UI + CDP 캡처)
# ──────────────────────────────────────────

def _parse_settle_elements(elements: list) -> list:
    """API 응답 elements → 내부 결과 리스트."""
    results = []
    for el in elements:
        ymd = el.get('settleExpectYmd') or el.get('settleBasisStartYmd') or ''
        if not ymd or len(ymd) != 8:
            continue
        try:
            settle_date = date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
        except ValueError:
            continue
        results.append({
            'date': settle_date,
            'order_count': 0,
            'sales_amount': int(el.get('paySettleAmount', 0) or 0),
            'cancel_amount': 0,
            'return_amount': 0,
            'settlement_amount': int(el.get('settleAmount', 0) or 0),
            'commission_amount': int(el.get('commissionSettleAmount', 0) or 0),
        })
    return results


def _fetch_settle_chunk(driver, chunk_start: date, chunk_end: date, log) -> list:
    """정산내역 페이지 1회 로드 → 달력 선택 → 검색 → CDP 캡처."""
    _cdp_enable(driver)
    driver.get(SETTLE_PAGE_URL)
    time.sleep(8)

    _select_date_with_calendar(driver, 0, chunk_start)
    time.sleep(0.5)
    _select_date_with_calendar(driver, 1, chunk_end)
    time.sleep(0.5)

    driver.execute_script(
        "Array.from(document.querySelectorAll('button'))"
        ".find(b=>b.textContent.trim()==='검색')?.click();"
    )
    time.sleep(6)

    elements, pagination = _cdp_pop_settle_elements(driver)
    total = int((pagination or {}).get('totalElements', 0))
    if total > len(elements):
        log(f'[스마트] 경고: {chunk_start}~{chunk_end} 총 {total}건 중 {len(elements)}건만 수집됨')
    return elements


def fetch_daily_sales(driver, start_date: date, end_date: date, log_fn=None, merchant_no=''):
    """
    SmartStore 정산내역 페이지(달력 UI)를 조작해 일별 정산 수집.
    10일 단위로 분할해 페이지네이션 없이 전체 수집.
    Returns: [{date, order_count, sales_amount, cancel_amount, return_amount, settlement_amount, commission_amount}, ...]
    """
    log = log_fn or logger.info

    if not merchant_no:
        log('[스마트] merchantNo 없음 — 판매통계 건너뜀')
        return []

    all_elements: list = []
    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(chunk_start + timedelta(days=9), end_date)
        log(f'[스마트] 정산 조회: {chunk_start} ~ {chunk_end}')
        els = _fetch_settle_chunk(driver, chunk_start, chunk_end, log)
        all_elements.extend(els)
        chunk_start = chunk_end + timedelta(days=1)

    results = _parse_settle_elements(all_elements)
    log(f'[스마트] 정산 {len(results)}건 수집 ({start_date}~{end_date})')
    return results


# ──────────────────────────────────────────
# 정산 내역 크롤링 (화면 파싱 대안)
# ──────────────────────────────────────────

def fetch_settlement(driver, year_month: str, log_fn=None):
    """
    정산관리 → 정산 내역 화면 파싱.
    year_month: 'YYYYMM'
    """
    log = log_fn or logger.info
    year = year_month[:4]
    month = year_month[4:]

    url = (
        f'https://sell.smartstore.naver.com/v2/pay-settlements/seller/orders'
        f'?settlementMonth={year}{month.zfill(2)}&page=1&size=100'
    )
    data = _execute_fetch(driver, url)
    if not data:
        log(f'[스마트] 정산 API 응답 없음: {year_month}')
        return []

    items = data.get('content', data.get('data', []))
    results = []
    for item in (items if isinstance(items, list) else []):
        results.append({
            'date': item.get('paymentDate', '')[:10],
            'sales_amount': int(item.get('paymentAmount', 0) or 0),
            'settlement_amount': int(item.get('settlementExpectedAmount', 0) or 0),
            'commission_amount': int(item.get('commissionAmount', 0) or 0),
        })

    log(f'[스마트] 정산내역 {len(results)}건 ({year_month})')
    return results


# ──────────────────────────────────────────
# 광고비 크롤링 (NSA 광고센터 billing 페이지)
# ──────────────────────────────────────────

SEARCHAD_BILLING_URL = 'https://ads.naver.com/ad-account/{ad_account_id}/billing/balance'
_NAVER_ADS_COOKIE_FILE = os.path.join(os.path.dirname(__file__), 'naver_ads_cookies.json')


def _inject_naver_ads_cookies(driver, log, login_id=None):
    """저장된 쿠키 파일에서 ads.naver.com 쿠키 주입.
    login_id: naver_ads_cookies.json의 키 (None이면 첫 번째 키 사용)."""
    if not os.path.exists(_NAVER_ADS_COOKIE_FILE):
        return False
    try:
        import json
        with open(_NAVER_ADS_COOKIE_FILE) as f:
            data = json.load(f)
        if not data:
            return False
        if login_id and login_id in data:
            cookies = data[login_id]
        else:
            cookies = list(data.values())[0]
        driver.get('https://ads.naver.com/')
        time.sleep(2)
        for c in cookies:
            try:
                driver.add_cookie(c)
            except Exception:
                pass
        log(f'[광고센터] 쿠키 주입 완료 (account={login_id or "default"})')
        return True
    except Exception as e:
        log(f'[광고센터] 쿠키 주입 실패: {e}')
        return False


def _login_searchad(driver, login_id: str, login_pw: str, log):
    """ads.naver.com 네이버 ID 로그인."""
    login_url = (
        'https://nid.naver.com/nidlogin.login'
        '?url=https%3A%2F%2Fads.naver.com%2F'
    )
    log(f'[광고센터] 로그인 시도: {login_id}')
    driver.get(login_url)
    time.sleep(3)

    try:
        id_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'id'))
        )
        id_input.click()
        time.sleep(0.3)
        id_input.clear()
        id_input.send_keys(login_id)
        time.sleep(0.3)

        pw_input = driver.find_element(By.ID, 'pw')
        pw_input.click()
        time.sleep(0.3)
        pw_input.clear()
        pw_input.send_keys(login_pw)
        time.sleep(0.3)
        pw_input.send_keys(Keys.RETURN)
        time.sleep(7)
    except Exception as e:
        log(f'[광고센터] 로그인 입력 오류: {e}')
        return False

    current = driver.current_url
    if 'nid.naver.com' in current:
        log(f'[광고센터] 로그인 실패 (URL: {current})')
        return False
    log('[광고센터] 로그인 성공')
    return True


def _parse_billing_table(driver, log) -> list:
    """ant-table에서 기간/소진액 파싱 (페이지네이션 전체 수집)."""
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.ant-table-tbody'))
        )
    except Exception:
        log('[광고센터] 테이블 로드 타임아웃')
        return []

    time.sleep(1)
    results = []

    for page_num in range(1, 50):
        rows = driver.find_elements(By.CSS_SELECTOR, '.ant-table-tbody .ant-table-row')
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, '.ant-table-cell')
            if len(cells) < 3:
                continue
            date_text = cells[0].text.strip().rstrip('.')
            spend_text = cells[2].text.strip()
            parts = date_text.split('.')
            if len(parts) != 3:
                continue
            try:
                d = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                continue
            cost = int(re.sub(r'[^\d]', '', spend_text) or 0)
            results.append({'date': d, 'cost': cost})

        # 다음 페이지 버튼 확인
        next_btn = driver.execute_script("""
            var btn = document.querySelector('.ant-pagination-next');
            if (!btn) return null;
            return btn.classList.contains('ant-pagination-disabled') ? 'disabled' : 'active';
        """)
        if next_btn != 'active':
            break
        driver.execute_script(
            "document.querySelector('.ant-pagination-next').click();"
        )
        time.sleep(1.5)

    return results


def fetch_ad_cost_billing(driver, account, since_date: date, until_date: date, log_fn=None) -> list:
    """
    searchad.naver.com billing/balance 기간별 소진내역 스크랩.
    월별로 분할 수집해 ant-table 10건 페이지 제한 우회.
    Returns: [{'date': date, 'cost': int}, ...]  cost = 소진액(VAT포함)
    """
    log = log_fn or logger.info

    if not account.naver_ad_account_id:
        log(f'[광고센터] {account.display_name}: naver_ad_account_id 미설정 — 건너뜀')
        return []

    # 계정별 쿠키 주입 (1회)
    _inject_naver_ads_cookies(driver, log, login_id=getattr(account, 'naver_ad_login_id', None))

    # 월 목록 생성
    months = []
    y, m = since_date.year, since_date.month
    while (y, m) <= (until_date.year, until_date.month):
        import calendar
        month_start = date(y, m, 1)
        month_end = date(y, m, calendar.monthrange(y, m)[1])
        chunk_start = max(month_start, since_date)
        chunk_end = min(month_end, until_date)
        months.append((chunk_start, chunk_end))
        m += 1
        if m > 12:
            m, y = 1, y + 1

    all_rows = []
    for chunk_start, chunk_end in months:
        date_range = f"{chunk_start},{chunk_end}"
        url = (
            SEARCHAD_BILLING_URL.format(ad_account_id=account.naver_ad_account_id)
            + f'?dateRange={date_range}&tab=period'
        )
        log(f'[광고센터] {account.display_name} {chunk_start.strftime("%Y-%m")} 조회')
        driver.get(url)
        time.sleep(5)

        if 'nid.naver.com' in driver.current_url or 'accounts.naver.com' in driver.current_url:
            log('[광고센터] 쿠키 만료 — naver_ads_cookies.json 갱신 필요')
            break

        rows = _parse_billing_table(driver, log)
        all_rows.extend(rows)
        time.sleep(1)

    log(f'[광고센터] {account.display_name}: {len(all_rows)}일 수집 ({since_date}~{until_date})')
    return all_rows


def fetch_ad_cost(driver, account, start_date: date, end_date: date, log_fn=None):
    """광고비 수집 — billing 페이지 스크랩."""
    return fetch_ad_cost_billing(driver, account, start_date, end_date, log_fn)


# ──────────────────────────────────────────
# 메인 크롤링 함수
# ──────────────────────────────────────────

def fetch_products(driver, log_fn=None):
    """
    스마트스토어 내부 API로 전체 상품 목록 수집.
    Returns: [{product_no, channel_product_no, name, sale_price, stock_quantity,
               status_type, seller_management_code, category_id, product_image_url}, ...]
    """
    log = log_fn or logger.info

    driver.get('https://sell.smartstore.naver.com/#/products/manage')
    time.sleep(4)

    results = []
    page = 1
    size = 100

    while True:
        url = (
            f'https://sell.smartstore.naver.com/v2/channel-products'
            f'?page={page}&size={size}'
        )
        data = _execute_fetch(driver, url)

        if not data:
            # 폴백: origin-products API 시도
            url2 = (
                f'https://sell.smartstore.naver.com/v2/products/search'
                f'?page={page}&size={size}'
            )
            data = _execute_fetch(driver, url2)

        if not data:
            log(f'[스마트] 상품 API 응답 없음 (page {page})')
            break

        contents = data.get('contents', data.get('data', data.get('content', [])))
        if not contents:
            break

        for item in contents:
            # channel-products 구조
            if 'channelProductNo' in item:
                results.append({
                    'product_no': str(item.get('originProductNo', '') or item.get('channelProductNo', '')),
                    'channel_product_no': str(item.get('channelProductNo', '') or ''),
                    'name': (item.get('name', '') or '')[:500],
                    'sale_price': int(item.get('salePrice', 0) or 0),
                    'stock_quantity': int(item.get('stockQuantity', 0) or 0),
                    'status_type': item.get('statusType', '') or '',
                    'seller_management_code': (item.get('sellerManagementCode', '') or '')[:200],
                    'category_id': str(item.get('categoryId', '') or ''),
                    'product_image_url': '',
                })
            else:
                # origin-products 구조
                ch = (item.get('channelProducts', []) or [{}])[0] if item.get('channelProducts') else {}
                img = ''
                ri = ch.get('representativeImage')
                if isinstance(ri, dict):
                    img = ri.get('url', '')
                results.append({
                    'product_no': str(item.get('originProductNo', '') or ''),
                    'channel_product_no': str(ch.get('channelProductNo', '') or ''),
                    'name': ((ch.get('name') or item.get('name') or '') or '')[:500],
                    'sale_price': int(ch.get('salePrice', 0) or 0),
                    'stock_quantity': int(ch.get('stockQuantity', 0) or 0),
                    'status_type': ch.get('statusType', '') or '',
                    'seller_management_code': (ch.get('sellerManagementCode', '') or '')[:200],
                    'category_id': str(ch.get('wholeCategoryId', '') or ''),
                    'product_image_url': img,
                })

        total_pages = data.get('totalPages', 1) or 1
        total_elements = data.get('totalElements', len(results))
        log(f'[스마트] 상품 page {page}/{total_pages} — {len(results)}/{total_elements}건')

        if page >= total_pages or len(results) >= total_elements:
            break
        page += 1
        time.sleep(1)

    log(f'[스마트] 상품 수집 완료: {len(results)}건')
    return results


def crawl_smartstore_account(driver, account, start_date: date, end_date: date, log_fn=None):
    """
    단일 계정 크롤링.
    Returns: {'sales': [...], 'ad_costs': [...]}
    """
    log = log_fn or logger.info

    if not account.login_pw:
        log(f'[스마트] 비밀번호 없음: {account.login_id} — 건너뜀')
        return None

    # 로그인
    if not login_smartstore(driver, account.login_id, account.login_pw, log):
        return None

    # 스토어 전환 (복수 스토어 계정)
    if account.store_slug and not switch_store(driver, account.store_slug, log):
        log(f'[스마트] 스토어 전환 실패: {account.store_slug}')

    # 판매 통계
    sales = fetch_daily_sales(driver, start_date, end_date, log)

    # 광고비
    ad_costs = fetch_ad_cost(driver, account, start_date, end_date, log)

    return {'sales': sales, 'ad_costs': ad_costs}

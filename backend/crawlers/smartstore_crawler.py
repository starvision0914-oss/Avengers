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

GRAPHQL_URL = 'https://sell.smartstore.naver.com/e/v3/graphql'

_GQL_DAILY_SETTLE = """
mutation findDailySettlesUsingPOST($merchantNo: String!, $data: DailySettleParamsInput) {
  DailySettleList: findDailySettlesUsingPOST(merchantNo: $merchantNo, data: $data) {
    elements {
      settleAmount
      paySettleAmount
      normalSettleAmount
      commissionSettleAmount
      settleBasisStartYmd
      settleBasisEndYmd
      settleExpectYmd
      settleCompleteYmd
      settleStatusType
      merchantNo
      __typename
    }
    pagination {
      page
      size
      totalElements
      totalPages
      __typename
    }
    __typename
  }
}
"""

def _gql_fetch(driver, operation_name, query, variables):
    """Selenium 세션에서 GraphQL mutation 실행."""
    body = json.dumps({
        'operationName': operation_name,
        'variables': variables,
        'query': query,
    })
    script = """
    var cb = arguments[arguments.length - 1];
    fetch(arguments[0], {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: arguments[1]
    })
    .then(function(r) { return r.json(); })
    .then(cb)
    .catch(function(e) { cb({error: String(e)}); });
    """
    try:
        return driver.execute_async_script(script, GRAPHQL_URL, body)
    except Exception as e:
        logger.warning('GraphQL fetch 실패: %s', e)
        return None


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
        var m = location.hash.match(/merchantNo[=\/](\d+)/);
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
# 판매 통계 (GraphQL)
# ──────────────────────────────────────────

def fetch_daily_sales(driver, start_date: date, end_date: date, log_fn=None, merchant_no=''):
    """
    스마트스토어 GraphQL로 일별 정산 데이터 수집.
    Returns: [{date, order_count, sales_amount, settlement_amount, commission_amount}, ...]
    """
    log = log_fn or logger.info

    if not merchant_no:
        log('[스마트] merchantNo 없음 — 판매통계 건너뜀')
        return []

    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    variables = {
        'merchantNo': merchant_no,
        'data': {
            'startYmd': start_str,
            'endYmd': end_str,
            'maskAccountNumber': True,
            'paging': {'page': 1, 'size': 100},
            'merchantNos': [],
            'orderingType': 'ASCENDING',
        }
    }

    data = _gql_fetch(driver, 'findDailySettlesUsingPOST', _GQL_DAILY_SETTLE, variables)
    if not data or 'error' in data:
        log(f'[스마트] GraphQL 응답 없음: {data}')
        return []

    elements = (data.get('data', {})
                    .get('DailySettleList', {})
                    .get('elements', []))

    results = []
    for el in elements:
        settle_ymd = el.get('settleExpectYmd') or el.get('settleBasisStartYmd') or ''
        if not settle_ymd or len(settle_ymd) != 8:
            continue
        try:
            settle_date = date(int(settle_ymd[:4]), int(settle_ymd[4:6]), int(settle_ymd[6:8]))
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
# 광고비 크롤링 (NSA 광고센터)
# ──────────────────────────────────────────

def fetch_ad_cost(driver, start_date: date, end_date: date, log_fn=None):
    """스마트스토어 광고비 수집 (미구현 — 빈 결과 반환)."""
    log = log_fn or logger.info
    log('[스마트] 광고비 수집 미구현 — 건너뜀')
    return []


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
    ad_costs = fetch_ad_cost(driver, start_date, end_date, log)

    return {'sales': sales, 'ad_costs': ad_costs}

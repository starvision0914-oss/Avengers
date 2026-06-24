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
import subprocess
import os
from datetime import date, timedelta

from selenium.webdriver.common.by import By
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

def _xtype(text, display_env):
    env = {**os.environ, 'DISPLAY': display_env}
    subprocess.run(['xclip', '-selection', 'clipboard'],
                   input=text.encode(), check=True, env=env)
    subprocess.run(['xdotool', 'key', 'ctrl+v'], env=env)


def _xkey(key, display_env):
    env = {**os.environ, 'DISPLAY': display_env}
    subprocess.run(['xdotool', 'key', key], env=env)


def _get_display():
    return os.environ.get('DISPLAY', ':0')


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
    display = _get_display()

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
        _xtype(login_id, display)
        time.sleep(0.3)

        # PW 입력
        pw_input = driver.find_element(By.XPATH, '//input[@type="password"]')
        pw_input.click()
        time.sleep(0.3)
        _xtype(login_pw, display)
        time.sleep(0.3)

        _xkey('Return', display)
        time.sleep(8)

    except Exception as e:
        log(f'[스마트] 로그인 입력 실패: {e}')
        return False

    current = driver.current_url
    if 'sell.smartstore' in current or 'login-callback' in current:
        log(f'[스마트] 로그인 성공')
        time.sleep(3)
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
# 판매 통계 (XHR API)
# ──────────────────────────────────────────

def _execute_fetch(driver, url, method='GET', body=None):
    """Selenium으로 XHR 실행 후 JSON 반환."""
    script = f"""
    return new Promise((resolve, reject) => {{
        fetch('{url}', {{
            method: '{method}',
            credentials: 'include',
            headers: {{'Content-Type': 'application/json'}},
            {f'body: JSON.stringify({json.dumps(body)}),' if body else ''}
        }})
        .then(r => r.json())
        .then(resolve)
        .catch(reject);
    }});
    """
    try:
        return driver.execute_async_script(
            script.replace('return new Promise', 'var cb = arguments[arguments.length-1]; new Promise')
            .replace('.then(resolve)', '.then(cb)')
            .replace('.catch(reject)', '.catch(cb)')
        )
    except Exception:
        return None


def fetch_daily_sales(driver, start_date: date, end_date: date, log_fn=None):
    """
    스마트스토어 내부 API로 일별 판매 통계 수집.
    Returns: [{date, order_count, sales_amount, cancel_amount, settlement_amount}, ...]
    """
    log = log_fn or logger.info

    # 스마트스토어센터 메인 페이지로 이동 (세션 유지)
    driver.get('https://sell.smartstore.naver.com/#/home/dashboard')
    time.sleep(3)

    results = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y%m%d')
        url = (
            f'https://sell.smartstore.naver.com/v2/seller-statistics/sellActivityStats'
            f'?startDate={date_str}&endDate={date_str}&timeUnit=day'
        )
        data = _execute_fetch(driver, url)
        if data:
            items = data.get('content', data.get('data', []))
            if isinstance(items, list):
                for item in items:
                    results.append({
                        'date': current,
                        'order_count': int(item.get('orderCount', 0) or 0),
                        'sales_amount': int(item.get('payAmount', item.get('salesAmount', 0)) or 0),
                        'cancel_amount': int(item.get('cancelAmount', 0) or 0),
                        'return_amount': int(item.get('returnAmount', 0) or 0),
                        'settlement_amount': int(item.get('settlementAmount', item.get('expectedSettlementAmount', 0)) or 0),
                        'commission_amount': int(item.get('commissionAmount', 0) or 0),
                    })
            elif isinstance(items, dict):
                results.append({
                    'date': current,
                    'order_count': int(items.get('orderCount', 0) or 0),
                    'sales_amount': int(items.get('payAmount', items.get('salesAmount', 0)) or 0),
                    'cancel_amount': int(items.get('cancelAmount', 0) or 0),
                    'return_amount': int(items.get('returnAmount', 0) or 0),
                    'settlement_amount': int(items.get('settlementAmount', items.get('expectedSettlementAmount', 0)) or 0),
                    'commission_amount': int(items.get('commissionAmount', 0) or 0),
                })
        current += timedelta(days=1)

    log(f'[스마트] 판매통계 {len(results)}건 수집 ({start_date}~{end_date})')
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
    """
    스마트스토어 광고센터(NSA) API로 광고비 수집.
    Returns: [{date, ad_type, cost, impression, click, conversion_count, conversion_amount}, ...]
    """
    log = log_fn or logger.info

    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    # NSA 광고 리포트 API
    url = (
        f'https://api.naver.com/nsa/api/v1/report/daily'
        f'?startDate={start_str}&endDate={end_str}'
    )
    data = _execute_fetch(driver, url)

    results = []
    if data and isinstance(data.get('data'), list):
        for item in data['data']:
            results.append({
                'date': date.fromisoformat(item.get('date', start_str)),
                'ad_type': 'shopping',
                'cost': int(item.get('cost', 0) or 0),
                'impression': int(item.get('impression', 0) or 0),
                'click': int(item.get('click', 0) or 0),
                'conversion_count': int(item.get('conversionCount', 0) or 0),
                'conversion_amount': int(item.get('conversionAmount', 0) or 0),
            })
    else:
        log(f'[스마트] NSA 광고비 API 미응답 — 화면 크롤링 시도')
        results = _fetch_ad_cost_screen(driver, start_date, end_date, log)

    log(f'[스마트] 광고비 {len(results)}건 수집')
    return results


def _fetch_ad_cost_screen(driver, start_date: date, end_date: date, log_fn=None):
    """NSA 광고센터 화면 크롤링 대안."""
    log = log_fn or logger.info
    results = []

    try:
        driver.get('https://nsa.naver.com/nsa2/main')
        time.sleep(5)

        # 날짜 범위 설정 후 테이블 파싱 (구조 확인 후 구현)
        log('[스마트] NSA 화면 크롤링 — 추후 DOM 구조 확인 필요')
    except Exception as e:
        log(f'[스마트] NSA 광고비 화면 크롤링 실패: {e}')

    return results


# ──────────────────────────────────────────
# 메인 크롤링 함수
# ──────────────────────────────────────────

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

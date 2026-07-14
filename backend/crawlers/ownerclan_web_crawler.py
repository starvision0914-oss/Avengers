"""오너클랜 마이페이지(웹) 스크래핑 — GraphQL API 범위 밖의 계정 전용 정보.
오너클랜머니(예치금), 주문/배송조회 현황, 구독서비스, 나만의 최저가 선점권.

로그인: ownerclan.com/V2/member/loginform.php, 필드 id=id/passwd (판매사ID/PW, GraphQL API와 동일 계정).
세션이 짧게 유지되므로(실측) 한 브라우저 세션 안에서 로그인→4개 페이지 조회를 이어서 처리.

실측 검증(2026-07-11, dlwodbs999):
  오너클랜머니: https://ownerclan.com/V2/service/reserveInfo.php  #cs_right > div > div[2] > div[1] > div[2]
  주문/배송조회: https://ownerclan.com/V2/service/orderList.php   #cs_right > div > div[3]
  구독서비스: https://ownerclan.com/V2/service/selectService.php  #selectServiceTable
  나만의 최저가상품: https://ownerclan.com/V2/service/products_only_me.php  #cart_title > div[4] > div[5]
"""
import logging
import os
import time

from django.utils import timezone

logger = logging.getLogger('crawler')

LOGIN_URL = 'https://ownerclan.com/V2/member/loginform.php'
PAGES = {
    'balance': ('https://ownerclan.com/V2/service/reserveInfo.php',
                '//*[@id="cs_right"]/div/div[2]/div[1]/div[2]'),
    'order_stats': ('https://ownerclan.com/V2/service/orderList.php',
                     '//*[@id="cs_right"]/div/div[3]'),
    'subscription': ('https://ownerclan.com/V2/service/selectService.php', None),  # 테이블 id로 직접 조회
    'lowest_price': ('https://ownerclan.com/V2/service/products_only_me.php',
                      '//*[@id="cart_title"]/div[4]/div[5]'),
}


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def _parse_order_stats(text):
    """'결제완료 배송준비 ... 반품/교환 요청 반품/교환 진행 반품/교환 완료\\n2 2 7 15 0 2 0 0 0' → dict.
    '반품/교환'은 다음 단어와 합쳐서 한 라벨로 취급(라벨 9개=값 9개로 맞춤)."""
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 2:
        return {}
    tokens = lines[0].split()
    labels = []
    i = 0
    while i < len(tokens):
        if tokens[i] == '반품/교환' and i + 1 < len(tokens):
            labels.append(f'{tokens[i]} {tokens[i + 1]}')
            i += 2
        else:
            labels.append(tokens[i])
            i += 1
    nums = lines[1].split()
    return dict(zip(labels, nums))


def _parse_lowest_price(text):
    """'누적 보유량\\n149\\n개\\n사용 가능 잔여 보유량\\n1\\n개\\n이번달 선점권\\n123\\n개' → dict."""
    parts = [p.strip() for p in text.split('\n') if p.strip()]
    result = {}
    i = 0
    while i < len(parts) - 1:
        if parts[i + 1].isdigit():
            result[parts[i]] = parts[i + 1]
            i += 3  # 라벨, 숫자, '개' 건너뜀
        else:
            i += 1
    return result


def _parse_subscription(text):
    lines = [l for l in text.splitlines() if l.strip()]
    return {'raw': lines}


def crawl_account_info(account, log_fn=None):
    """마이페이지 4개 정보를 스크래핑해 계정에 저장. 반환: 수집된 dict."""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoAlertPresentException
    from crawlers.browser import create_driver

    os.environ.setdefault('DISPLAY', ':99')
    profile_dir = f'/tmp/ownerclan_web_profile_{account.login_id}'
    os.makedirs(profile_dir, exist_ok=True)
    driver = create_driver(user_data_dir=profile_dir, kill_existing=False)
    result = {}
    try:
        driver.get(LOGIN_URL)
        time.sleep(2)
        if 'loginform' in driver.current_url:
            driver.find_element(By.ID, 'id').send_keys(account.login_id)
            driver.find_element(By.ID, 'passwd').send_keys(account.login_pw)
            driver.find_element(By.CSS_SELECTOR, 'input[type=submit]').click()
            time.sleep(3)
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
                alert.accept()
                _log(log_fn, f'[ownerclan-web:{account.login_id}] 로그인 실패(알림): {alert_text}')
                return {'error': f'로그인 실패: {alert_text}'}
            except NoAlertPresentException:
                pass
            if 'loginform' in driver.current_url:
                _log(log_fn, f'[ownerclan-web:{account.login_id}] 로그인 실패')
                return {'error': '로그인 실패'}
        _log(log_fn, f'[ownerclan-web:{account.login_id}] 로그인 성공')

        # 오너클랜머니
        url, xpath = PAGES['balance']
        driver.get(url); time.sleep(2)
        try:
            result['balance'] = driver.find_element(By.XPATH, xpath).text.strip()
            _log(log_fn, f'  오너클랜머니: {result["balance"]}')
        except Exception as e:
            _log(log_fn, f'  오너클랜머니 조회 실패: {e}')

        # 주문/배송조회
        url, xpath = PAGES['order_stats']
        driver.get(url); time.sleep(2)
        try:
            text = driver.find_element(By.XPATH, xpath).text
            result['order_stats'] = _parse_order_stats(text)
            _log(log_fn, f'  주문현황: {result["order_stats"]}')
        except Exception as e:
            _log(log_fn, f'  주문현황 조회 실패: {e}')

        # 구독서비스
        url, _ = PAGES['subscription']
        driver.get(url); time.sleep(2.5)
        try:
            text = driver.find_element(By.ID, 'selectServiceTable').text
            result['subscription'] = _parse_subscription(text)
            _log(log_fn, f'  구독서비스: {result["subscription"]}')
        except Exception as e:
            _log(log_fn, f'  구독서비스 조회 실패: {e}')

        # 나만의 최저가 상품
        url, xpath = PAGES['lowest_price']
        driver.get(url); time.sleep(2)
        try:
            text = driver.find_element(By.XPATH, xpath).text
            result['lowest_price'] = _parse_lowest_price(text)
            _log(log_fn, f'  최저가 선점권: {result["lowest_price"]}')
        except Exception as e:
            _log(log_fn, f'  최저가 선점권 조회 실패: {e}')
    finally:
        driver.quit()

    account.balance = result.get('balance', account.balance)
    account.order_stats = result.get('order_stats', account.order_stats)
    account.subscription_info = result.get('subscription', account.subscription_info)
    account.lowest_price_quota = result.get('lowest_price', account.lowest_price_quota)
    account.info_synced_at = timezone.now()
    account.save(update_fields=['balance', 'order_stats', 'subscription_info',
                                 'lowest_price_quota', 'info_synced_at'])
    return result

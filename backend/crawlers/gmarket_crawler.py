"""
지마켓 ESM+ 광고비 크롤러
- ad.esmplus.com 로그인
- CPC/AI/잔액 데이터 수집
- 쿠키 기반 세션 재사용 (24시간)
"""
import json
import logging
import time
from datetime import timedelta
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .browser import create_driver, stop_display
from .utils import parse_int

logger = logging.getLogger('crawler')

# XPath 상수
XPATHS = {
    'gmarket_balance': '//*[@id="container"]/div[1]/div[1]/div/table/tbody/tr[1]/td[2]/div/strong',
    'auction_balance': '//*[@id="container"]/div[1]/div[1]/div/table/tbody/tr[2]/td[2]/div/strong',
    'gmarket_cpc': '//*[@id="container"]/div[1]/div[1]/div/table/tbody/tr[1]/td[4]/div/strong',
    'auction_cpc': '//*[@id="container"]/div[1]/div[1]/div/table/tbody/tr[2]/td[4]/div/strong',
    'ai_usage': '//*[@id="spnGmktBillingMinusAmnt"]',
    'login_btn': '//img[@alt="로그인"]',
    'site_radio': '//input[@name="rdoSiteSelect" and @value="GMKT"]',
}

CPC_URL = 'https://ad.esmplus.com/cpc/bidmng/bidmanagement'
AI_URL = 'https://ad.esmplus.com/Remarketing/Management'
LOGIN_URL = 'https://ad.esmplus.com/'

COOKIE_TTL_HOURS = 24


def _safe_text(driver, xpath, timeout=15):
    """요소가 존재하고 텍스트가 비어있지 않을 때까지 대기"""
    try:
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                el = driver.find_element(By.XPATH, xpath)
                text = el.text.strip()
                if text and text != '0' and text != '-':
                    return text
            except Exception:
                pass
            time.sleep(0.5)
        # 타임아웃 시 마지막으로 한번 더 시도
        el = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return el.text.strip() or '0'
    except Exception:
        return '0'


def _try_cookie_login(driver, account):
    if not account.cookie_data or not account.cookie_saved_at:
        return False
    if timezone.now() - account.cookie_saved_at > timedelta(hours=COOKIE_TTL_HOURS):
        return False

    try:
        driver.get(LOGIN_URL)
        time.sleep(1)

        cookies = json.loads(account.cookie_data)
        for cookie in cookies:
            cookie.pop('sameSite', None)
            cookie.pop('expiry', None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass

        driver.get(CPC_URL)
        time.sleep(2)

        url = driver.current_url.lower()
        if 'signin' in url or 'login' in url or 'logon' in url:
            return False
        return True
    except Exception:
        return False


def _full_login(driver, login_id, password):
    driver.get(LOGIN_URL)
    time.sleep(2)

    try:
        radio = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, XPATHS['site_radio']))
        )
        radio.click()
        time.sleep(0.5)
    except Exception:
        pass

    try:
        id_field = driver.find_element(By.ID, 'SellerId')
        id_field.clear()
        id_field.send_keys(login_id)

        pw_field = driver.find_element(By.ID, 'SellerPassword')
        pw_field.clear()
        pw_field.send_keys(password)

        login_btn = driver.find_element(By.XPATH, XPATHS['login_btn'])
        login_btn.click()

        time.sleep(5)
        url = driver.current_url.lower()

        # 2단계 인증 체크
        if 'logon' in url and 'signin' in url:
            logger.warning(f'[{login_id}] 2단계 인증 필요')
            # 페이지 소스에서 인증 타입 확인
            page = driver.page_source
            if '2차 인증' in page or '추가 인증' in page or 'captcha' in page.lower():
                logger.warning(f'[{login_id}] 2단계 인증/캡차 감지')
            return False

        if 'logon' not in url and 'signin' not in url:
            return True
        return False
    except Exception as e:
        logger.error(f'로그인 실패 [{login_id}]: {e}')
        return False


def _save_cookies(driver, account):
    try:
        cookies = driver.get_cookies()
        account.cookie_data = json.dumps(cookies)
        account.cookie_saved_at = timezone.now()
        account.save(update_fields=['cookie_data', 'cookie_saved_at'])
    except Exception as e:
        logger.warning(f'쿠키 저장 실패: {e}')


def collect_one_account(driver, account, log_fn=None):
    login_id = account.login_id
    password = account.password_enc

    def log(msg):
        logger.info(f'[{login_id}] {msg}')
        if log_fn:
            log_fn(f'[{login_id}] {msg}')

    driver.delete_all_cookies()

    # 쿠키 로그인 시도
    if _try_cookie_login(driver, account):
        log('쿠키 로그인 성공')
    else:
        log('일반 로그인 시도...')
        if not _full_login(driver, login_id, password):
            return None
        log('로그인 성공')
        _save_cookies(driver, account)

    # CPC 페이지 데이터 수집
    driver.get(CPC_URL)
    time.sleep(3)

    # 잔액 요소가 로드될 때까지 대기
    gmarket_balance = parse_int(_safe_text(driver, XPATHS['gmarket_balance'], timeout=20))
    auction_balance = parse_int(_safe_text(driver, XPATHS['auction_balance']))
    gmarket_cpc_raw = parse_int(_safe_text(driver, XPATHS['gmarket_cpc']))
    auction_cpc = parse_int(_safe_text(driver, XPATHS['auction_cpc']))

    # 주요 값이 모두 0이면 페이지 로딩 실패로 판단하고 재시도
    if gmarket_balance == 0 and gmarket_cpc_raw == 0:
        log('CPC 페이지 데이터 미로드, 새로고침 후 재시도...')
        driver.refresh()
        time.sleep(5)
        gmarket_balance = parse_int(_safe_text(driver, XPATHS['gmarket_balance'], timeout=20))
        auction_balance = parse_int(_safe_text(driver, XPATHS['auction_balance']))
        gmarket_cpc_raw = parse_int(_safe_text(driver, XPATHS['gmarket_cpc']))
        auction_cpc = parse_int(_safe_text(driver, XPATHS['auction_cpc']))

    # AI 페이지 데이터 수집
    driver.get(AI_URL)
    time.sleep(2)

    ai_usage = parse_int(_safe_text(driver, XPATHS['ai_usage']))

    # AI 비용 차감 계산
    gmarket_cpc = max(gmarket_cpc_raw - ai_usage, 0)
    total_usage = gmarket_cpc + auction_cpc + ai_usage

    result = {
        'gmarket_id': login_id,
        'total_balance': gmarket_balance,
        'gmarket_cpc': gmarket_cpc,
        'auction_cpc': auction_cpc,
        'ai_usage': ai_usage,
        'total_usage': total_usage,
        'collected_at': timezone.now(),
    }

    log(f'잔액={gmarket_balance:,} CPC={gmarket_cpc:,} AI={ai_usage:,} 합계={total_usage:,}')
    return result


def _get_sub_accounts(main_login_id):
    """메인 계정의 서브 계정 목록 반환"""
    from apps.cpc.models import CrawlerAccount
    return list(CrawlerAccount.objects.filter(
        platform='gmarket', is_active=True,
        gmarket_origin_id=main_login_id
    ).exclude(login_id=main_login_id))


def _collect_sub_account(driver, sub_account, log_fn=None):
    """메인 로그인 세션에서 서브 계정 데이터 수집 (이미 로그인된 상태)"""
    login_id = sub_account.login_id

    def log(msg):
        logger.info(f'[서브:{login_id}] {msg}')
        if log_fn:
            log_fn(f'[서브:{login_id}] {msg}')

    # CPC 페이지 — 메인 로그인 세션에서 서브 데이터도 표에 포함됨
    driver.get(CPC_URL)
    time.sleep(3)

    gmarket_balance = parse_int(_safe_text(driver, XPATHS['gmarket_balance'], timeout=20))
    auction_balance = parse_int(_safe_text(driver, XPATHS['auction_balance']))
    gmarket_cpc_raw = parse_int(_safe_text(driver, XPATHS['gmarket_cpc']))
    auction_cpc = parse_int(_safe_text(driver, XPATHS['auction_cpc']))

    if gmarket_balance == 0 and gmarket_cpc_raw == 0:
        log('CPC 페이지 데이터 미로드, 새로고침 후 재시도...')
        driver.refresh()
        time.sleep(5)
        gmarket_balance = parse_int(_safe_text(driver, XPATHS['gmarket_balance'], timeout=20))
        auction_balance = parse_int(_safe_text(driver, XPATHS['auction_balance']))
        gmarket_cpc_raw = parse_int(_safe_text(driver, XPATHS['gmarket_cpc']))
        auction_cpc = parse_int(_safe_text(driver, XPATHS['auction_cpc']))

    # AI 페이지
    driver.get(AI_URL)
    time.sleep(2)
    ai_usage = parse_int(_safe_text(driver, XPATHS['ai_usage']))

    gmarket_cpc = max(gmarket_cpc_raw - ai_usage, 0)
    total_usage = gmarket_cpc + auction_cpc + ai_usage

    result = {
        'gmarket_id': login_id,
        'total_balance': gmarket_balance,
        'gmarket_cpc': gmarket_cpc,
        'auction_cpc': auction_cpc,
        'ai_usage': ai_usage,
        'total_usage': total_usage,
        'collected_at': timezone.now(),
    }

    log(f'잔액={gmarket_balance:,} CPC={gmarket_cpc:,} AI={ai_usage:,} 합계={total_usage:,}')
    return result


def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, GmarketDepositSnapshot, CrawlerLog

    accounts = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    if account_filter:
        accounts = accounts.filter(login_id__in=account_filter)
    else:
        # 서브 계정은 제외 (메인 로그인 시 같이 수집)
        accounts = accounts.exclude(
            is_multi_id=True,
        ) | accounts.filter(
            is_multi_id=True, gmarket_origin_id__isnull=True,
        ) | accounts.filter(
            is_multi_id=True, gmarket_origin_id='',
        ) | accounts.filter(
            is_multi_id=True, gmarket_origin_id__in=['', None],
        )
        # 위 복잡한 쿼리 대신 간단히 리스트로 필터
        accounts = [a for a in CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
                     if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

    if not accounts:
        msg = '활성 지마켓 계정이 없습니다.'
        logger.info(msg)
        if log_fn:
            log_fn(msg)
        return {'collected': 0, 'failed': 0}

    collected, failed = 0, 0
    driver = None

    try:
        driver = create_driver()

        for account in accounts:
            if account.crawling_status == '차단됨':
                if log_fn: log_fn(f'[GM:{account.login_id}] 차단됨 - 건너뜀')
                continue

            # 메인 계정 수집
            for attempt in range(3):
                try:
                    result = collect_one_account(driver, account, log_fn)
                    if result:
                        GmarketDepositSnapshot.objects.create(**result)
                        account.fail_count = 0
                        account.crawling_status = '정상'
                        account.last_crawled_at = timezone.now()
                        account.save()
                        collected += 1

                        CrawlerLog.objects.create(
                            platform='gmarket', level='success',
                            message=f'수집 완료: 합계={result["total_usage"]:,}원',
                            account_id=account.login_id
                        )

                        # 서브 계정 수집 (같은 로그인 세션 재사용)
                        sub_accounts = _get_sub_accounts(account.login_id)
                        for sub in sub_accounts:
                            try:
                                sub_result = _collect_sub_account(driver, sub, log_fn)
                                if sub_result:
                                    GmarketDepositSnapshot.objects.create(**sub_result)
                                    sub.fail_count = 0
                                    sub.crawling_status = '정상'
                                    sub.last_crawled_at = timezone.now()
                                    sub.save()
                                    collected += 1
                                    CrawlerLog.objects.create(
                                        platform='gmarket', level='success',
                                        message=f'서브계정 수집 완료: 합계={sub_result["total_usage"]:,}원',
                                        account_id=sub.login_id
                                    )
                            except Exception as e:
                                logger.error(f'[서브:{sub.login_id}] 수집 실패: {e}')
                                if log_fn:
                                    log_fn(f'[서브:{sub.login_id}] 수집 실패: {e}')

                        break
                    else:
                        raise Exception('수집 결과 없음')
                except Exception as e:
                    if attempt == 2:
                        account.fail_count += 1
                        if account.fail_count >= 30:
                            account.crawling_status = '차단됨'
                        account.save()
                        failed += 1

                        CrawlerLog.objects.create(
                            platform='gmarket', level='error',
                            message=f'수집 실패: {str(e)}',
                            account_id=account.login_id
                        )
                        logger.error(f'[{account.login_id}] 3회 시도 실패: {e}')
                    else:
                        time.sleep(2)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        stop_display()

    summary = f'지마켓 수집 완료: 성공={collected} 실패={failed}'
    logger.info(summary)
    if log_fn:
        log_fn(summary)

    return {'collected': collected, 'failed': failed}

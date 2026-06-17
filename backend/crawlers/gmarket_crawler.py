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
    """요소가 존재하고 숫자가 포함된 텍스트가 로드될 때까지 대기.

    페이지 초기 렌더링 시 셀렉터에는 단위(예: "원")만 들어있고 숫자가 비어있는
    경우가 있어, 숫자(0~9)가 한 글자라도 포함된 시점까지 기다린다.
    """
    try:
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                el = driver.find_element(By.XPATH, xpath)
                text = el.text.strip()
                if text and any(c.isdigit() for c in text):
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

    # 잔액이 0이면 페이지 로딩 실패로 판단하고 최대 2회 재시도
    for retry in range(2):
        if gmarket_balance != 0:
            break
        log(f'CPC 페이지 잔액 미로드, 새로고침 후 재시도 ({retry + 1}/2)...')
        driver.refresh()
        time.sleep(8)
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

    for retry in range(2):
        if gmarket_balance != 0:
            break
        log(f'CPC 페이지 잔액 미로드, 새로고침 후 재시도 ({retry + 1}/2)...')
        driver.refresh()
        time.sleep(8)
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


def _send_telegram_alert(message):
    """긴급 알림을 텔레그램으로 발송"""
    try:
        from apps.cpc.models import TelegramConfig, TelegramRecipient
        import urllib.request
        import json as _json
        cfg = TelegramConfig.objects.first()
        if not cfg or not cfg.bot_token:
            return
        for r in TelegramRecipient.objects.filter(is_active=True):
            data = _json.dumps({'chat_id': r.chat_id, 'text': message}).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage',
                data=data, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


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
    consecutive_login_failures = 0
    LOGIN_FAIL_ABORT_THRESHOLD = 3
    _last_sig = None   # 직전 저장 계정의 (잔액,CPC,AI,옥션) — 세션오염(동일데이터 복제) 탐지용

    for account in accounts:
        if account.crawling_status == '차단됨':
            if log_fn: log_fn(f'[GM:{account.login_id}] 차단됨 - 건너뜀')
            continue

        # 연속 3회 로그인 실패 시 즉시 중단 + 텔레그램 알림
        if consecutive_login_failures >= LOGIN_FAIL_ABORT_THRESHOLD:
            msg = f'⛔ 지마켓 연속 {LOGIN_FAIL_ABORT_THRESHOLD}회 접속 실패 — 서버 문제 의심, 크롤링 중단'
            logger.error(msg)
            if log_fn: log_fn(msg)
            CrawlerLog.objects.create(platform='gmarket', level='error', message=msg, account_id='SYSTEM')
            _send_telegram_alert(f'🚨 [지마켓 크롤러 긴급]\n\n{msg}\n\n로그인 시도를 중단했습니다.\n해결 후 다시 실행해주세요.')
            break

        driver = None
        # 사용자 룰: 로그인/수집 실패 시 1회 재시도 (총 2회 시도) 후 다음 계정
        result = None
        last_exc = None
        for attempt in range(2):
            try:
                if driver:
                    try: driver.quit()
                    except: pass
                driver = create_driver()
                result = collect_one_account(driver, account, log_fn)
                if result:
                    last_exc = None
                    consecutive_login_failures = 0
                    break
                else:
                    last_exc = Exception(f'수집 결과 없음 (시도 {attempt+1}/2)')
                    if log_fn: log_fn(f'[GM:{account.login_id}] 빈 결과 — 재시도 {attempt+1}/2')
            except Exception as e:
                last_exc = e
                if log_fn: log_fn(f'[GM:{account.login_id}] 시도 {attempt+1}/2 실패: {str(e)[:100]}')
        if last_exc and not result:
            consecutive_login_failures += 1
        try:
            if last_exc and not result:
                raise last_exc
            if result:
                _sig = (result.get('total_balance'), result.get('gmarket_cpc'),
                        result.get('ai_usage'), result.get('auction_cpc'))
                # 직전 계정과 완전히 동일한 데이터 = 로그인 실패로 직전 세션을 읽은 오염 → 저장 제외
                if _sig == _last_sig and any(v for v in _sig):
                    raise Exception('직전 계정과 동일 데이터 — 세션오염(로그인 실패) 판단, 저장 제외')
                _last_sig = _sig
                GmarketDepositSnapshot.objects.create(**result)
                # 누적 차단 정책: 성공해도 fail_count 리셋하지 않음 (관리자 수동해제로만 0)
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
                            # 누적 차단 정책: 성공해도 fail_count 리셋하지 않음
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
            else:
                raise Exception('수집 결과 없음')

        except Exception as e:
            account.fail_count += 1
            if account.fail_count >= 30:
                account.crawling_status = '차단됨'
            account.save()
            failed += 1
            CrawlerLog.objects.create(
                platform='gmarket', level='error',
                message=f'수집 실패: {str(e)[:200]}',
                account_id=account.login_id
            )
            logger.error(f'[{account.login_id}] 실패: {e}')
        finally:
            if driver:
                try: driver.quit()
                except: pass

    stop_display()

    summary = f'지마켓 수집 완료: 성공={collected} 실패={failed}'
    logger.info(summary)
    if log_fn:
        log_fn(summary)

    return {'collected': collected, 'failed': failed}

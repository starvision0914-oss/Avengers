"""도매마트(domemart.co.kr) L코드 판매상태(판매중/품절) 조회.
로그인+검색을 단일 브라우저 세션으로 유지(세션이 스크립트 재실행 간엔 유지 안 됨 확인됨).
사람이 쓰는 속도로 코드 하나씩 조회(랜덤 지연) — 대량 벌크조회 기능 없음.
"""
import logging
import random
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawlers.browser import create_driver

logger = logging.getLogger(__name__)

LOGIN_URL = 'https://www.domemart.co.kr/shop/login.php'
HOME_URL = 'http://www.domemart.co.kr/shop/index.php'
SEARCH_XPATH = '/html/body/div[4]/div/div[1]/div/div[2]/div/table/tbody/tr/td[2]/form/table/tbody/tr/td[2]/input'
LOGIN_ID = 'rejoice888'
LOGIN_PW = '@dlwodbs0'

_COUNT_RE = re.compile(r'총\s*([0-9,]+)개의\s*상품')


def is_logged_out(driver):
    return 'login.php' in driver.current_url


def do_login(driver):
    driver.get(LOGIN_URL)
    time.sleep(2)
    driver.find_element(By.NAME, 'MB_ID').clear()
    driver.find_element(By.NAME, 'MB_ID').send_keys(LOGIN_ID)
    pw = driver.find_element(By.NAME, 'MB_PW')
    pw.clear()
    pw.send_keys(LOGIN_PW)
    pw.send_keys(Keys.RETURN)
    time.sleep(3)
    try:
        driver.switch_to.alert.accept()
    except NoAlertPresentException:
        pass


def check_code(driver, code, retries=2):
    """반환: {'code','count','has_soldout_word'} 또는 {'code','error':True}
    검색창(mall_keyword)은 검색결과 페이지(mall.php)에도 그대로 남아있어(실측 2026-08-22)
    매번 홈으로 돌아갈 필요 없이 결과 페이지에서 바로 이어서 검색 가능 — 최초 1회/재로그인 후에만 홈 이동."""
    for attempt in range(retries):
        try:
            fields = driver.find_elements(By.NAME, 'mall_keyword')
            if not fields or is_logged_out(driver):
                if is_logged_out(driver):
                    logger.info('로그아웃 감지 — 재로그인')
                    do_login(driver)
                driver.get(HOME_URL)
                time.sleep(random.uniform(0.8, 1.5))
                fields = driver.find_elements(By.NAME, 'mall_keyword')
            el = fields[0]
            el.clear()
            el.send_keys(code)
            el.send_keys(Keys.RETURN)
            # staleness_of: 옛 검색창 DOM이 사라지는(=새 페이지로 실제 전환된) 순간을 감지.
            # page_source 길이비교보다 가볍고(전체 HTML 전송 불필요) 우연히 길이가 같아
            # 오탐할 위험도 없음 — 서버렌더링(mall.php)이라 전환 즉시 새 본문도 이미 완성돼있음.
            # 검증(2026-08-22): 여러 코드에서 count/품절 값 fast=safe 완전 일치 확인.
            try:
                WebDriverWait(driver, 3, poll_frequency=0.1).until(EC.staleness_of(el))
            except Exception:
                pass
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            if is_logged_out(driver) or ('아이디' in body_text[:50] and '비밀번호' in body_text[:80]):
                logger.info('%s: 검색중 로그아웃됨 — 재시도', code)
                do_login(driver)
                continue
            m = _COUNT_RE.search(body_text)
            count = int(m.group(1).replace(',', '')) if m else None
            has_soldout_word = '품절' in body_text
            return {'code': code, 'count': count, 'has_soldout_word': has_soldout_word}
        except Exception as e:
            logger.warning('%s: 오류(%d/%d) %s', code, attempt + 1, retries, str(e)[:100])
            time.sleep(2)
    return {'code': code, 'count': None, 'error': True}


def result_to_status(result):
    """check_code() 결과 → 'in_stock'/'soldout'/'not_found'"""
    if result.get('error'):
        return None
    count = result.get('count')
    if not count:
        return 'not_found'
    if result.get('has_soldout_word'):
        return 'soldout'
    return 'in_stock'


def new_driver(user_data_dir='/tmp/domemart_profile_run'):
    return create_driver(user_data_dir=user_data_dir, kill_existing=False)

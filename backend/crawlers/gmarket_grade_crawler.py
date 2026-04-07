"""지마켓 셀러 등급 크롤러 - esmplus.com 내 판매 정보"""
import re
import time
import logging
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import create_driver, stop_display
from .utils import parse_int

logger = logging.getLogger('crawler')
LOGIN_URL = 'https://signin.esmplus.com/login'

def _parse_max_items(text):
    cleaned = re.sub(r'[^\d]', '', str(text or ''))
    return int(cleaned) if cleaned else None

def _login(driver, login_id, password):
    driver.get(LOGIN_URL)
    time.sleep(2)
    try:
        driver.find_element(By.CSS_SELECTOR, '.button__tab--gmarket').click()
        time.sleep(0.5)
        driver.find_element(By.ID, 'typeMemberInputId01').clear()
        driver.find_element(By.ID, 'typeMemberInputId01').send_keys(login_id)
        driver.find_element(By.ID, 'typeMemberInputPassword01').clear()
        driver.find_element(By.ID, 'typeMemberInputPassword01').send_keys(password)
        for btn in driver.find_elements(By.TAG_NAME, 'button'):
            if '로그인' in (btn.text or ''):
                btn.click()
                break
        time.sleep(3)
        return 'signin' not in driver.current_url.lower()
    except Exception as e:
        logger.error(f'[GM등급:{login_id}] 로그인 실패: {e}')
        return False

def _close_popups(driver):
    try:
        driver.execute_script("""
            document.querySelectorAll('.popup, .modal, .layer, [class*="popup"], [class*="modal"]')
                .forEach(e => e.remove());
        """)
    except Exception:
        pass

def _collect_grades(driver, login_id, log_fn=None):
    results = []
    def log(m):
        if log_fn: log_fn(f'[GM등급:{login_id}] {m}')

    try:
        time.sleep(3)
        _close_popups(driver)

        # 내 판매 정보 섹션 찾기
        try:
            section = driver.find_element(By.XPATH, "//h3[contains(text(),'내 판매 정보')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", section)
            time.sleep(1)
        except Exception:
            log('내 판매 정보 섹션 못 찾음')
            return results

        # 드롭다운에서 G마켓 셀러 목록 추출
        try:
            dropdown_btns = driver.find_elements(By.CSS_SELECTOR, 'ul[role="listbox"] li button[role="option"]')
            gmarket_sellers = []
            for btn in dropdown_btns:
                text = btn.text.strip()
                if text.startswith('G') or btn.find_elements(By.CSS_SELECTOR, '.text--gmarket'):
                    sid = text.replace('선택됨', '').strip()
                    if sid.startswith('G'):
                        sid = sid[1:]
                    gmarket_sellers.append((btn, sid))
        except Exception:
            gmarket_sellers = []

        if not gmarket_sellers:
            # 싱글 셀러: 직접 추출
            try:
                items = driver.find_elements(By.CSS_SELECTOR, '.list__info-sale .list-item')
                if len(items) >= 4:
                    grade = items[0].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                    max_items = _parse_max_items(items[1].find_element(By.CSS_SELECTOR, '.text__info').text)
                    approval = items[2].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                    expiry = items[3].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                    results.append({
                        'gmarket_id': login_id, 'seller_id': login_id,
                        'seller_grade': grade, 'max_item_count': max_items,
                        'approval_status': approval, 'contact_expiry': expiry,
                        'collected_at': timezone.now(),
                    })
                    log(f'{login_id}: 등급={grade} 최대수량={max_items}')
            except Exception as e:
                log(f'싱글 셀러 추출 실패: {e}')
            return results

        # 멀티 셀러: 드롭다운 클릭
        for btn, sid in gmarket_sellers:
            try:
                btn.click()
                time.sleep(2)
                grade, max_items, approval, expiry = '', None, '', ''
                for _ in range(10):
                    items = driver.find_elements(By.CSS_SELECTOR, '.list__info-sale .list-item')
                    if len(items) >= 4:
                        grade = items[0].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                        max_items = _parse_max_items(items[1].find_element(By.CSS_SELECTOR, '.text__info').text)
                        if grade and max_items is not None:
                            approval = items[2].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                            expiry = items[3].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                            break
                    time.sleep(2)

                results.append({
                    'gmarket_id': login_id, 'seller_id': sid,
                    'seller_grade': grade, 'max_item_count': max_items,
                    'approval_status': approval, 'contact_expiry': expiry,
                    'collected_at': timezone.now(),
                })
                log(f'{sid}: 등급={grade} 최대수량={max_items}')
            except Exception as e:
                log(f'{sid} 실패: {e}')
    except Exception as e:
        log(f'등급 수집 오류: {e}')
    return results

def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, GmarketSellerGrade, CrawlerLog
    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    if not qs.exists():
        if log_fn: log_fn('활성 지마켓 계정 없음')
        return {'collected': 0, 'failed': 0}

    all_grades, driver = [], None
    try:
        driver = create_driver()
        for acct in qs:
            if acct.crawling_status == '차단됨':
                if log_fn: log_fn(f'[GM등급:{acct.login_id}] 차단됨 - 건너뜀')
                continue

            try:
                driver.delete_all_cookies()
                if _login(driver, acct.login_id, acct.password_enc):
                    grades = _collect_grades(driver, acct.login_id, log_fn)
                    all_grades.extend(grades)
                else:
                    if log_fn: log_fn(f'[GM등급:{acct.login_id}] 로그인 실패')
            except Exception as e:
                if log_fn: log_fn(f'[GM등급:{acct.login_id}] 오류: {e}')
    finally:
        if driver:
            try: driver.quit()
            except: pass
        stop_display()

    for g in all_grades:
        GmarketSellerGrade.objects.create(**g)

    CrawlerLog.objects.create(platform='gmarket', level='info', message=f'등급 수집: {len(all_grades)}건')
    if log_fn: log_fn(f'지마켓 등급 수집 완료: {len(all_grades)}건')
    return {'collected': len(all_grades), 'failed': 0}

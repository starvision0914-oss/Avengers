"""11번가 셀러 등급 크롤러 - soffice.11st.co.kr"""
import re
import time
import logging
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import create_driver, create_headless_driver, stop_display

logger = logging.getLogger('crawler')
LOGIN_URL = 'https://login.11st.co.kr/auth/front/selleroffice/login.tmall'
GRADE_URL = 'https://soffice.11st.co.kr/view/5004'

def _login(driver, login_id, password):
    driver.get(LOGIN_URL)
    time.sleep(2)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'loginName'))).clear()
        driver.find_element(By.ID, 'loginName').send_keys(login_id)
        driver.find_element(By.ID, 'passWord').clear()
        driver.find_element(By.ID, 'passWord').send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        time.sleep(3)
        if 'otpLoginForm' in driver.current_url:
            return False
        return 'soffice.11st.co.kr' in driver.current_url
    except Exception as e:
        logger.error(f'[11st등급:{login_id}] 로그인 실패: {e}')
        return False

def _close_popups(driver):
    for sel in ['.popup-close', '.btn-close', '.layer-close']:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            try: el.click()
            except: pass
    for btn in driver.find_elements(By.TAG_NAME, 'button'):
        if btn.text.strip() in ('닫기', 'close', '확인'):
            try: btn.click()
            except: pass
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except: pass

def _collect_grade(driver, login_id, seller_name='', log_fn=None):
    def log(m):
        if log_fn: log_fn(f'[11st등급:{login_id}] {m}')

    driver.get(GRADE_URL)
    time.sleep(3)
    _close_popups(driver)

    grade, grade_img_src, required_sales, grade_message = None, '', None, ''

    try:
        iframe = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@id,'5004')]"))
        )
        driver.switch_to.frame(iframe)
        time.sleep(2)

        # 등급 이미지에서 등급 번호 추출
        try:
            img = driver.find_element(By.XPATH, '//*[@id="gradeB_c"]/img')
            grade_img_src = img.get_attribute('src') or ''
            m = re.search(r'seller_grade(\d+)', grade_img_src)
            if m:
                grade = int(m.group(1))
        except Exception:
            pass

        # 필요 매출액
        try:
            el = driver.find_element(By.XPATH,
                '//*[@id="form1"]/div[10]/div/div[7]/table/tbody/tr/td[4]/table/tbody/tr[2]/td/b')
            val = re.sub(r'[^\d]', '', el.text)
            if val and int(val) > 1000:
                required_sales = int(val)
        except Exception:
            # fallback: 모든 b 태그에서 가장 큰 숫자
            try:
                for b in driver.find_elements(By.TAG_NAME, 'b'):
                    val = re.sub(r'[^\d]', '', b.text)
                    if val and int(val) > 100000:
                        if required_sales is None or int(val) > required_sales:
                            required_sales = int(val)
            except Exception:
                pass

        # 등급 메시지
        try:
            for el in driver.find_elements(By.TAG_NAME, 'span') + driver.find_elements(By.TAG_NAME, 'td'):
                text = el.text.strip()
                if '등급' in text and any(kw in text for kw in ['하향', '유지', '조정', '판매활동']):
                    grade_message = text[:255]
                    break
        except Exception:
            pass

        driver.switch_to.default_content()
    except Exception as e:
        log(f'등급 추출 실패: {e}')
        try: driver.switch_to.default_content()
        except: pass

    log(f'등급={grade} 필요매출={required_sales} 메시지={grade_message[:30]}')
    return {
        'eleven_id': login_id, 'seller_name': seller_name,
        'grade': grade, 'grade_img_src': grade_img_src,
        'required_sales': required_sales, 'grade_message': grade_message,
        'collected_at': timezone.now(),
    }

def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, ElevenSellerGrade, CrawlerLog
    qs = CrawlerAccount.objects.filter(platform='11st', is_active=True)
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    if not qs.exists():
        if log_fn: log_fn('활성 11번가 계정 없음')
        return {'collected': 0, 'failed': 0}

    results, driver = [], None
    try:
        driver = create_driver()
        for acct in qs:
            try:
                driver.delete_all_cookies()
                if _login(driver, acct.login_id, acct.password):
                    result = _collect_grade(driver, acct.login_id, acct.seller_name, log_fn)
                    if result:
                        results.append(result)
                else:
                    if log_fn: log_fn(f'[11st등급:{acct.login_id}] 로그인 실패/OTP')
            except Exception as e:
                if log_fn: log_fn(f'[11st등급:{acct.login_id}] 오류: {e}')
    finally:
        if driver:
            try: driver.quit()
            except: pass
        stop_display()

    for r in results:
        ElevenSellerGrade.objects.create(**r)

    CrawlerLog.objects.create(platform='11st', level='info', message=f'등급 수집: {len(results)}건')
    if log_fn: log_fn(f'11번가 등급 수집 완료: {len(results)}건')
    return {'collected': len(results), 'failed': 0}

"""지마켓 AI 광고 상태 크롤러 - ad.esmplus.com/Remarketing/Management"""
import time
import logging
from datetime import date as date_cls
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import create_driver, stop_display

logger = logging.getLogger('crawler')

LOGIN_URL = 'https://ad.esmplus.com/Member/SignIn/LogOn'
AI_MGMT_URL = 'https://ad.esmplus.com/Remarketing/Management'


def _login(driver, login_id, password):
    driver.get(LOGIN_URL)
    time.sleep(2)
    try:
        try:
            tab = driver.find_element(By.XPATH, '//*[@id="login_seller"]/ul/li[2]/label')
            tab.click()
            time.sleep(0.3)
        except Exception:
            pass
        driver.find_element(By.ID, 'SellerId').clear()
        driver.find_element(By.ID, 'SellerId').send_keys(login_id)
        driver.find_element(By.ID, 'SellerPassword').clear()
        driver.find_element(By.ID, 'SellerPassword').send_keys(password)
        try:
            driver.find_element(By.XPATH, '//*[@id="lnkSellerLogin"]/img').click()
        except Exception:
            driver.find_element(By.XPATH, '//img[@alt="로그인"]').click()
        WebDriverWait(driver, 15).until(lambda d: 'SignIn' not in d.current_url and 'LogOn' not in d.current_url)
        time.sleep(2)
        return True
    except Exception as e:
        logger.error(f'[GM-AI:{login_id}] 로그인 실패: {e}')
        return False


def _collect_ai_status(driver, login_id, log_fn=None):
    def log(m):
        if log_fn: log_fn(f'[GM-AI:{login_id}] {m}')

    driver.get(AI_MGMT_URL)
    time.sleep(3)

    results = []
    try:
        tables = driver.find_elements(By.CSS_SELECTOR, 'div.remarketing_table table')
        if not tables:
            tables = driver.find_elements(By.TAG_NAME, 'table')

        for table in tables:
            rows = table.find_elements(By.TAG_NAME, 'tr')
            for row in rows:
                try:
                    sid = row.get_attribute('data-sellerid')
                    if not sid:
                        continue
                    group_no = row.get_attribute('data-groupno') or ''
                    onoff = row.get_attribute('data-onoff') or '0'
                    start_date_raw = row.get_attribute('data-startdate') or ''
                    end_date_raw = row.get_attribute('data-enddate') or ''

                    start_date = start_date_raw[:10] if start_date_raw and '0001-01-01' not in start_date_raw else ''
                    end_date = end_date_raw[:10] if end_date_raw and '0001-01-01' not in end_date_raw else ''

                    cols = row.find_elements(By.TAG_NAME, 'td')
                    group_name = cols[1].text.strip() if len(cols) > 1 else ''
                    operation_status = cols[4].text.strip().replace('\n', ' ') if len(cols) > 4 else ''
                    budget_mgmt = cols[8].text.strip() if len(cols) > 8 else ''

                    button_status = 'ON' if onoff == '1' else 'OFF'
                    today = date_cls.today()

                    if button_status == 'OFF':
                        actual_status = 'OFF'
                        actual_reason = 'OFF'
                    else:
                        if start_date:
                            sd = date_cls.fromisoformat(start_date)
                            if sd > today:
                                actual_status = 'OFF'
                                actual_reason = f'시작일대기({start_date})'
                            else:
                                actual_status = 'ON'
                                actual_reason = '정상ON'
                        else:
                            actual_status = 'ON'
                            actual_reason = '정상ON'

                    results.append({
                        'gmarket_id': login_id,
                        'seller_id': sid,
                        'group_name': group_name,
                        'button_status': button_status,
                        'actual_status': actual_status,
                        'actual_reason': actual_reason,
                        'start_date': start_date,
                        'end_date': end_date,
                        'operation_status': operation_status,
                        'budget_mgmt': budget_mgmt,
                    })
                    log(f'{sid}: {actual_status} ({actual_reason})')
                except Exception as e:
                    continue
    except Exception as e:
        log(f'AI 상태 수집 오류: {e}')

    return results


def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, GmarketAiAdSummary, CrawlerLog

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    qs = qs.exclude(crawling_status='차단됨')

    if not qs.exists():
        if log_fn: log_fn('활성 지마켓 계정 없음')
        return {'collected': 0, 'failed': 0}

    all_results, driver = [], None
    try:
        driver = create_driver()
        for acct in qs:
            try:
                driver.delete_all_cookies()
                if _login(driver, acct.login_id, acct.password_enc):
                    results = _collect_ai_status(driver, acct.login_id, log_fn)
                    all_results.extend(results)
                else:
                    if log_fn: log_fn(f'[GM-AI:{acct.login_id}] 로그인 실패')
            except Exception as e:
                if log_fn: log_fn(f'[GM-AI:{acct.login_id}] 오류: {e}')
    finally:
        if driver:
            try: driver.quit()
            except: pass
        stop_display()

    for r in all_results:
        existing = GmarketAiAdSummary.objects.filter(
            seller_id=r['seller_id'], group_name__contains='G마켓'
        ).first()
        if existing:
            for k, v in r.items():
                setattr(existing, k, v)
            existing.save()
        else:
            GmarketAiAdSummary.objects.create(**r)

    CrawlerLog.objects.create(platform='gmarket', level='info', message=f'AI 상태 수집: {len(all_results)}건')
    if log_fn: log_fn(f'지마켓 AI 수집 완료: {len(all_results)}건')
    return {'collected': len(all_results), 'failed': 0}

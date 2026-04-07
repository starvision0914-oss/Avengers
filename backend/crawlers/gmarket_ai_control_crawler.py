"""지마켓 AI 광고 ON/OFF 제어 - ad.esmplus.com API"""
import json
import time
import logging
from datetime import date, timedelta
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import create_driver, stop_display

logger = logging.getLogger('crawler')

AI_MGMT_URL = 'https://ad.esmplus.com/Remarketing/Management'
SET_ONOFF_API = '/Remarketing/Management/SetCpcRemarketingGroupOnOffAsync'
SET_EXPOSURE_API = '/Remarketing/Management/SetCpcRemarketingGroupExposureAsync'


def _login(driver, login_id, password):
    driver.get('https://ad.esmplus.com/')
    time.sleep(3)
    try:
        try:
            radio = driver.find_element(By.XPATH, '//input[@name="rdoSiteSelect" and @value="GMKT"]')
            radio.click()
            time.sleep(0.5)
        except:
            pass
        driver.find_element(By.ID, 'SellerId').clear()
        driver.find_element(By.ID, 'SellerId').send_keys(login_id)
        driver.find_element(By.ID, 'SellerPassword').clear()
        driver.find_element(By.ID, 'SellerPassword').send_keys(password)
        try:
            driver.find_element(By.XPATH, '//img[@alt="로그인"]').click()
        except:
            driver.find_element(By.XPATH, '//*[@id="lnkSellerLogin"]/img').click()
        time.sleep(5)
        url = driver.current_url.lower()
        return 'logon' not in url and 'signin' not in url
    except Exception as e:
        logger.error(f'[AI제어:{login_id}] 로그인 실패: {e}')
        return False


def _call_esm_api(driver, api_path, payload):
    """ESM+ 내부 API 호출 (jQuery AJAX)"""
    js = f"""
    var result = null;
    $.ajax({{
        type: 'POST', async: false,
        url: '{api_path}',
        contentType: 'application/json;charset=utf-8',
        data: JSON.stringify(arguments[0]),
        dataType: 'json'
    }}).done(function(rtn) {{ result = rtn; }})
      .fail(function(xhr) {{ result = {{ResultCode: -1, Message: xhr.statusText}}; }});
    return result;
    """
    return driver.execute_script(js, payload)


def _get_group_info(driver):
    """관리 페이지에서 그룹 정보 추출"""
    driver.get(AI_MGMT_URL)
    time.sleep(3)

    groups = []
    tables = driver.find_elements(By.CSS_SELECTOR, 'div.remarketing_table table')
    if not tables:
        tables = driver.find_elements(By.TAG_NAME, 'table')

    for table in tables:
        for row in table.find_elements(By.TAG_NAME, 'tr'):
            sid = row.get_attribute('data-sellerid')
            if not sid:
                continue
            group_no = row.get_attribute('data-groupno')
            onoff = row.get_attribute('data-onoff') or '0'
            start_raw = row.get_attribute('data-startdate') or ''
            start_date = start_raw[:10] if start_raw and '0001-01-01' not in start_raw else ''

            cols = row.find_elements(By.TAG_NAME, 'td')
            group_name = cols[1].text.strip() if len(cols) > 1 else ''

            groups.append({
                'seller_id': sid,
                'group_no': group_no,
                'group_name': group_name,
                'button_status': 'ON' if onoff == '1' else 'OFF',
                'start_date': start_date,
            })
    return groups


def set_ai_onoff(driver, group_no, action, start_date='', end_date=''):
    """AI ON/OFF 설정
    action: 'on', 'off', 'on-date'
    """
    if action == 'off':
        user_status = 0
    else:
        user_status = 1
        if not start_date:
            # 내일부터 시작
            start_date = (date.today() + timedelta(days=1)).isoformat()

    payload = {
        'groupSetList': [{
            'RemarketingGroupNo': int(group_no),
            'UserOnOffStatus': user_status,
            'StartDate': start_date,
            'EndDate': end_date,
        }]
    }
    result = _call_esm_api(driver, SET_ONOFF_API, payload)
    return result


def control_account(driver, login_id, action, source='manual', log_fn=None):
    """한 계정의 모든 AI 그룹 ON/OFF 제어"""
    def log(m):
        logger.info(f'[AI제어:{login_id}] {m}')
        if log_fn:
            log_fn(f'[AI제어:{login_id}] {m}')

    groups = _get_group_info(driver)
    if not groups:
        log('AI 그룹 없음')
        return []

    results = []
    for g in groups:
        group_no = g['group_no']
        before = g['button_status']

        if action == 'off' and before == 'OFF':
            log(f'{g["seller_id"]} ({g["group_name"]}): 이미 OFF')
            continue
        if action == 'on' and before == 'ON':
            log(f'{g["seller_id"]} ({g["group_name"]}): 이미 ON')
            continue

        api_result = set_ai_onoff(driver, group_no, action)
        success = api_result and api_result.get('ResultCode') == 0 if api_result else False
        after = 'ON' if action != 'off' else 'OFF'

        log(f'{g["seller_id"]} ({g["group_name"]}): {before}→{after} {"성공" if success else "실패"}')
        results.append({
            'seller_id': g['seller_id'],
            'group_name': g['group_name'],
            'before': before,
            'after': after if success else before,
            'success': success,
        })

    return results


def run_control(action, source='manual', log_fn=None, account_filter=None):
    """전체 계정 AI ON/OFF 제어"""
    from apps.cpc.models import CrawlerAccount, GmarketAiAdHistory, CrawlerLog

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)

    all_results, driver = [], None
    try:
        driver = create_driver()
        for acct in qs:
            try:
                driver.delete_all_cookies()
                if not _login(driver, acct.login_id, acct.password_enc):
                    if log_fn:
                        log_fn(f'[AI제어:{acct.login_id}] 로그인 실패')
                    continue

                results = control_account(driver, acct.login_id, action, source, log_fn)
                for r in results:
                    GmarketAiAdHistory.objects.create(
                        gmarket_id=acct.login_id,
                        seller_id=r['seller_id'],
                        group_name=r['group_name'],
                        event_time=timezone.now(),
                        history_type=f'AI {action.upper()}',
                        detail=f'{r["before"]}→{r["after"]} ({"성공" if r["success"] else "실패"})',
                    )
                all_results.extend(results)

                CrawlerLog.objects.create(
                    platform='gmarket', level='success',
                    message=f'AI {action}: {len(results)}건',
                    account_id=acct.login_id
                )
            except Exception as e:
                if log_fn:
                    log_fn(f'[AI제어:{acct.login_id}] 오류: {e}')
                CrawlerLog.objects.create(
                    platform='gmarket', level='error',
                    message=str(e), account_id=acct.login_id
                )
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        stop_display()

    if log_fn:
        log_fn(f'AI {action} 완료: {len(all_results)}건')
    return {'results': all_results, 'count': len(all_results)}

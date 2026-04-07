"""지마켓 프라임 광고 입찰기간 변경 크롤러"""
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
CPP_URL = 'https://ad.esmplus.com/cpp/management'

def _login(driver, login_id, password):
    driver.get('https://ad.esmplus.com/Member/SignIn/LogOn')
    time.sleep(2)
    try:
        driver.find_element(By.ID, 'SellerId').clear()
        driver.find_element(By.ID, 'SellerId').send_keys(login_id)
        driver.find_element(By.ID, 'SellerPassword').clear()
        driver.find_element(By.ID, 'SellerPassword').send_keys(password)
        try:
            driver.find_element(By.XPATH, '//img[@alt="로그인"]').click()
        except:
            driver.find_element(By.XPATH, '//*[@id="lnkSellerLogin"]/img').click()
        WebDriverWait(driver, 15).until(lambda d: 'SignIn' not in d.current_url and 'LogOn' not in d.current_url)
        time.sleep(2)
        return True
    except Exception as e:
        logger.error(f'로그인 실패 [{login_id}]: {e}')
        return False

def _get_next_sunday():
    today = date.today()
    days = (6 - today.weekday()) % 7
    if days == 0:
        days = 7
    return today + timedelta(days=days)

def control_one(driver, login_id, log_fn=None):
    def log(m):
        if log_fn: log_fn(f'[프라임:{login_id}] {m}')

    driver.get(CPP_URL)
    time.sleep(3)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="tbBidList"]/tr[1]'))
        )
    except:
        log('키워드 없음')
        return {'success': True, 'keyword_count': 0, 'skipped': True}

    rows = driver.find_elements(By.XPATH, '//*[@id="tbBidList"]/tr')
    keyword_count = len(rows)
    log(f'키워드 {keyword_count}개')

    if keyword_count == 0:
        return {'success': True, 'keyword_count': 0, 'skipped': True}

    # 전체 선택
    try:
        driver.find_element(By.ID, 'chkAll').click()
        time.sleep(0.5)
    except:
        log('전체선택 실패')
        return {'success': False, 'keyword_count': keyword_count}

    # 입찰기간 변경 버튼
    try:
        driver.find_element(By.ID, 'btnBidPeriodUpdateLayer').click()
        time.sleep(1)
    except:
        log('입찰기간 변경 버튼 실패')
        return {'success': False, 'keyword_count': keyword_count}

    # 다음 주 일요일 설정
    target = _get_next_sunday()
    try:
        driver.execute_script(f"""
            $('#txtPeriodStartDate').datepicker('setDate', new Date({target.year}, {target.month - 1}, {target.day}));
        """)
        time.sleep(0.5)
    except Exception as e:
        log(f'날짜 설정 실패: {e}')
        return {'success': False, 'keyword_count': keyword_count}

    # 변경 실행
    try:
        driver.find_element(By.ID, 'btnBidPeriodUpdate').click()
        for _ in range(5):
            try:
                WebDriverWait(driver, 15).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                time.sleep(0.5)
            except:
                break
    except:
        pass

    time.sleep(2)
    bid_start = target.isoformat()
    bid_end = (target + timedelta(days=6)).isoformat()
    log(f'입찰기간 변경: {bid_start} ~ {bid_end}')

    # 검증
    driver.refresh()
    time.sleep(5)
    keywords = []
    target_str = target.strftime('%Y.%m.%d')
    try:
        rows = driver.find_elements(By.XPATH, '//*[@id="tbBidList"]/tr')
        for row in rows:
            tds = row.find_elements(By.TAG_NAME, 'td')
            kw_name = ''
            period = ''
            for ci in [4, 3, 2]:
                if ci < len(tds) and tds[ci].text.strip():
                    kw_name = tds[ci].text.strip()
                    break
            for ci in [18, 17, 16, 15]:
                if ci < len(tds):
                    txt = tds[ci].text.strip()
                    if '20' in txt and '.' in txt:
                        period = txt
                        break
                    btns = tds[ci].find_elements(By.TAG_NAME, 'button')
                    for btn in btns:
                        bt = btn.text.strip()
                        if '20' in bt and '.' in bt:
                            period = bt
                            break
                    if period:
                        break
            keywords.append({'name': kw_name, 'period': period})
    except:
        pass

    success = any(target_str in kw.get('period', '') for kw in keywords)
    return {
        'success': success,
        'keyword_count': keyword_count,
        'bid_start': bid_start,
        'bid_end': bid_end,
        'keywords': keywords,
    }

def run_all_accounts(log_fn=None, account_filter=None, source='manual'):
    from apps.cpc.models import CrawlerAccount, CppBidHistory, CrawlerLog
    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)

    results, driver = [], None
    try:
        driver = create_driver()
        for acct in qs:
            try:
                driver.delete_all_cookies()
                if not _login(driver, acct.login_id, acct.password_enc):
                    continue
                result = control_one(driver, acct.login_id, log_fn)
                if result and not result.get('skipped'):
                    CppBidHistory.objects.create(
                        gmarket_id=acct.login_id,
                        keyword_count=result.get('keyword_count', 0),
                        bid_start_date=result.get('bid_start'),
                        bid_end_date=result.get('bid_end'),
                        source=source,
                        success=result.get('success', False),
                        detail=json.dumps(result.get('keywords', []), ensure_ascii=False),
                    )
                results.append(result)
                CrawlerLog.objects.create(platform='gmarket', level='success',
                    message=f'프라임: {result.get("keyword_count")}개 키워드', account_id=acct.login_id)
            except Exception as e:
                if log_fn: log_fn(f'[프라임:{acct.login_id}] 실패: {e}')
                CrawlerLog.objects.create(platform='gmarket', level='error', message=str(e), account_id=acct.login_id)
    finally:
        if driver:
            try: driver.quit()
            except: pass
        stop_display()
    if log_fn: log_fn(f'프라임 완료: {len(results)}건')
    return {'collected': len(results), 'failed': 0}

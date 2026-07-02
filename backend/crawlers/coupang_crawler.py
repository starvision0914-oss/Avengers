"""쿠팡 Wing 로그인 + 부가세신고 매출자료 크롤링.

ai100(betona1/ai100) 참조 이식. 원본은 별도 'tax' DB + 하드코딩된 로켓그로스 계정
목록을 썼지만, 여기서는 Avengers 단일 DB 원칙에 맞춰 CoupangAccount/CoupangVatSales로
옮기고 로켓그로스 여부는 CoupangAccount.is_rocket_growth 필드로 관리한다.

로그인: Keycloak OAuth(xauth.coupang.com) — input.send_keys()가 봇탐지에 걸려
xclip+xdotool로 클립보드 붙여넣기 방식을 쓴다(ai100에서 검증된 우회법).
"""
import os
import re
import subprocess
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

LOGIN_URL = 'https://wing.coupang.com/'
WING_VAT_URL = 'https://wing.coupang.com/tenants/finance/wing/contentsurl/proportion-sales'
ROCKET_VAT_URL = 'https://wing.coupang.com/tenants/rfm/settlements/vat-report?category=GOLDFISH'


def _parse_int(text):
    if not text:
        return 0
    cleaned = re.sub(r'[^\d\-]', '', text.strip())
    return int(cleaned) if cleaned else 0


def _xtype(text):
    """xclip + xdotool로 클립보드 붙여넣기 (input.send_keys()는 봇탐지에 걸림)."""
    env = {**os.environ}
    subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode(), check=True, env=env)
    subprocess.run(['xdotool', 'key', 'ctrl+v'], env=env, check=True)


def _try_cookie_login(driver, account):
    """저장된 쿠키로 로그인 시도. 성공 시 True."""
    if not account.cookie_data:
        return False
    import json
    driver.get(LOGIN_URL)
    time.sleep(1)
    try:
        cookies = json.loads(account.cookie_data)
        for c in cookies:
            c.pop('sameSite', None)
            c.pop('expiry', None)
            try:
                driver.add_cookie(c)
            except Exception:
                pass
        driver.get(LOGIN_URL)
        time.sleep(3)
        if 'wing.coupang.com' in driver.current_url and 'xauth' not in driver.current_url:
            return True
    except Exception:
        pass
    return False


def _save_cookies(driver, account):
    import json
    from django.utils import timezone
    try:
        cookies = driver.get_cookies()
        if cookies:
            account.cookie_data = json.dumps(cookies)
            account.cookie_saved_at = timezone.now()
            account.save(update_fields=['cookie_data', 'cookie_saved_at'])
    except Exception:
        pass


def login_coupang_wing(driver, login_id, login_pw, log_fn=print):
    """쿠팡 Wing OAuth 로그인 (xdotool 클립보드 붙여넣기)."""
    log_fn(f'[쿠팡:{login_id}] 로그인 시도')
    driver.get(LOGIN_URL)
    time.sleep(5)

    try:
        WebDriverWait(driver, 15).until(
            lambda d: 'xauth.coupang.com' in d.current_url or 'wing.coupang.com' in d.current_url)
    except TimeoutException:
        log_fn(f'[쿠팡:{login_id}] 로그인 페이지 로딩 타임아웃: {driver.current_url}')
        return False

    if 'wing.coupang.com' in driver.current_url and 'xauth' not in driver.current_url:
        log_fn(f'[쿠팡:{login_id}] 이미 로그인됨')
        return True

    try:
        id_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'username')))
        id_input.click()
        time.sleep(0.3)
        _xtype(login_id)
        time.sleep(0.3)

        pw_input = driver.find_element(By.ID, 'password')
        pw_input.click()
        time.sleep(0.3)
        _xtype(login_pw)
        time.sleep(0.3)

        driver.find_element(By.ID, 'kc-login').click()
        time.sleep(8)
    except NoSuchElementException:
        log_fn(f'[쿠팡:{login_id}] Keycloak 셀렉터 실패, input type으로 재시도')
        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="email"]')
            if inputs:
                inputs[0].click(); time.sleep(0.3); _xtype(login_id); time.sleep(0.3)
            pw_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]')
            if pw_inputs:
                pw_inputs[0].click(); time.sleep(0.3); _xtype(login_pw); time.sleep(0.3)
            subprocess.run(['xdotool', 'key', 'Return'], env={**os.environ})
            time.sleep(8)
        except Exception as e:
            log_fn(f'[쿠팡:{login_id}] 로그인 입력 실패: {e}')
            return False

    try:
        driver.switch_to.alert.accept()
    except Exception:
        pass

    try:
        WebDriverWait(driver, 15).until(
            lambda d: 'wing.coupang.com' in d.current_url and 'xauth' not in d.current_url)
    except TimeoutException:
        log_fn(f'[쿠팡:{login_id}] 로그인 리다이렉트 타임아웃: {driver.current_url}')
        return False

    log_fn(f'[쿠팡:{login_id}] 로그인 성공')
    return True


def _set_period_and_search(driver, start_ym, end_ym, log_fn=print):
    start_year, start_month = start_ym[:4], str(int(start_ym[4:]))
    end_year, end_month = end_ym[:4], str(int(end_ym[4:]))

    selects = driver.find_elements(By.TAG_NAME, 'select')
    if len(selects) < 4:
        log_fn(f'[쿠팡] select {len(selects)}개 — 기간 설정 불가')
        return False

    try:
        Select(selects[0]).select_by_value(start_year); time.sleep(0.3)
        Select(selects[1]).select_by_value(start_month); time.sleep(0.3)
        Select(selects[2]).select_by_value(end_year); time.sleep(0.3)
        Select(selects[3]).select_by_value(end_month); time.sleep(0.5)
    except Exception as e:
        log_fn(f'[쿠팡] 기간 설정 실패: {e}')
        return False

    for btn in driver.find_elements(By.TAG_NAME, 'button'):
        try:
            if btn.text.strip() == '검색' and btn.is_displayed():
                btn.click()
                time.sleep(8)
                return True
        except Exception:
            continue
    log_fn('[쿠팡] 검색 버튼 못 찾음')
    return False


def _parse_vat_table(driver, log_fn=print):
    results = []
    tables = driver.find_elements(By.TAG_NAME, 'table')
    if not tables:
        return results
    for row in tables[0].find_elements(By.TAG_NAME, 'tr'):
        tds = row.find_elements(By.TAG_NAME, 'td')
        if len(tds) < 5:
            continue
        period_text = tds[0].text.strip()
        if '합계' in period_text or period_text == '합':
            continue
        m = re.match(r'(\d{4})-(\d{1,2})', period_text) or re.search(r'(\d{4})[-년.]?\s*(\d{1,2})', period_text)
        if not m:
            continue
        results.append({
            'year': int(m.group(1)), 'month': int(m.group(2)),
            'credit_card': _parse_int(tds[1].text),
            'cash_receipt': _parse_int(tds[2].text),
            'etc_payment': _parse_int(tds[3].text),
            'total_sales': _parse_int(tds[4].text),
        })
    return results


def _save_vat_rows(account, sale_type, rows):
    from apps.coupang.models import CoupangVatSales
    saved = 0
    for d in rows:
        CoupangVatSales.objects.update_or_create(
            account=account, year=d['year'], month=d['month'], sale_type=sale_type,
            defaults={
                'credit_card': d['credit_card'], 'cash_receipt': d['cash_receipt'],
                'etc_payment': d['etc_payment'], 'total_sales': d['total_sales'],
            },
        )
        saved += 1
    return saved


def crawl_coupang_vat(driver, account, start_ym, end_ym, log_fn=print):
    """CoupangAccount 1개: 판매자윙(+로켓그로스) 부가세 크롤링."""
    all_results = {'판매자윙': [], '로켓그로스': []}

    if not _try_cookie_login(driver, account):
        if not login_coupang_wing(driver, account.login_id, account.login_pw, log_fn):
            return all_results
        _save_cookies(driver, account)

    time.sleep(2)

    log_fn(f'[쿠팡:{account.login_id}] 판매자윙 부가세 조회')
    driver.get(WING_VAT_URL)
    time.sleep(8)
    if _set_period_and_search(driver, start_ym, end_ym, log_fn):
        wing_rows = _parse_vat_table(driver, log_fn)
        if wing_rows:
            all_results['판매자윙'] = wing_rows
            saved = _save_vat_rows(account, '판매자윙', wing_rows)
            log_fn(f'[쿠팡:{account.login_id}] 판매자윙 {saved}건 저장')
        else:
            log_fn(f'[쿠팡:{account.login_id}] 판매자윙 데이터 없음')
    else:
        log_fn(f'[쿠팡:{account.login_id}] 판매자윙 기간/검색 실패')

    if account.is_rocket_growth:
        log_fn(f'[쿠팡:{account.login_id}] 로켓그로스 부가세 조회')
        navigated = False
        try:
            for el in driver.find_elements(
                    By.XPATH, "//*[contains(text(), '로켓그로스') and contains(text(), '부가세')]"):
                if el.is_displayed():
                    driver.execute_script('arguments[0].click();', el)
                    time.sleep(8)
                    navigated = True
                    break
        except Exception:
            pass
        if not navigated:
            driver.get(ROCKET_VAT_URL)
            time.sleep(8)
            navigated = 'vat-report' in driver.current_url or 'settlements' in driver.current_url

        if navigated and _set_period_and_search(driver, start_ym, end_ym, log_fn):
            rg_rows = _parse_vat_table(driver, log_fn)
            if rg_rows:
                all_results['로켓그로스'] = rg_rows
                saved = _save_vat_rows(account, '로켓그로스', rg_rows)
                log_fn(f'[쿠팡:{account.login_id}] 로켓그로스 {saved}건 저장')
            else:
                log_fn(f'[쿠팡:{account.login_id}] 로켓그로스 데이터 없음')
        else:
            log_fn(f'[쿠팡:{account.login_id}] 로켓그로스 접근/검색 실패')

    from django.utils import timezone
    account.last_crawled_at = timezone.now()
    account.save(update_fields=['last_crawled_at'])

    return all_results

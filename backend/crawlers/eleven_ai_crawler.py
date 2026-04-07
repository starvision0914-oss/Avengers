"""11번가 Adoffice AI 캠페인 크롤러 - adoffice.11st.co.kr"""
import re
import time
import logging
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException
from .browser import create_driver, stop_display
from .utils import parse_int

logger = logging.getLogger('crawler')

ADOFFICE_URL = 'https://adoffice.11st.co.kr'
LOGOUT_URL = 'https://auth.adoffice.11st.co.kr/logout/submit/advertiser'

JS_PARSE_CAMPAIGNS = """
var rows = document.querySelectorAll('table tbody tr');
var result = [];
for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length < 4) continue;
    var nameCell = cells[1];
    var spans = nameCell.querySelectorAll('span');
    var isAi = false;
    for (var s = 0; s < spans.length; s++) {
        if (spans[s].textContent.trim() === 'AI') { isAi = true; break; }
    }
    var links = nameCell.querySelectorAll('a');
    var name = links.length ? links[0].textContent.trim() : nameCell.textContent.trim();
    if (isAi && name.indexOf('AI\\n') === 0) name = name.substring(3).trim();
    if (isAi && name.indexOf('AI ') === 0) name = name.substring(3).trim();
    var onoffCell = cells[2];
    var dots = onoffCell.querySelectorAll("div[class*='css-']");
    var onoff = false;
    if (dots.length) {
        var bg = getComputedStyle(dots[0]).backgroundColor;
        onoff = bg.indexOf('220, 106') >= 0;
    }
    var status = cells[3].textContent.trim();
    var texts = [];
    for (var c = 4; c < cells.length; c++) texts.push(cells[c].textContent.trim());
    result.push({name: name, is_ai: isAi, onoff: onoff, status: status, perf: texts});
}
return result;
"""

JS_PARSE_AI_DETAIL = """
var body = document.body.textContent;
var result = {daily_budget: null, target_roas: null, exposure_period: null, onoff: null};
var sw = document.querySelector('span.MuiSwitch-switchBase');
if (sw) result.onoff = sw.className.indexOf('Mui-checked') >= 0 ? 'ON' : 'OFF';
var m = body.match(/캠페인 일 예산\\s*\\n?\\s*([\\d,]+)원/);
if (m) result.daily_budget = parseInt(m[1].replace(/,/g, ''));
m = body.match(/목표광고수익률\\s*\\n?\\s*([\\d,]+)%/);
if (m) result.target_roas = parseInt(m[1].replace(/,/g, ''));
m = body.match(/노출기간\\s*\\n?\\s*(.+)/);
if (m) result.exposure_period = m[1].trim();
return result;
"""

PERF_COLUMNS = [
    'impressions', 'clicks', 'ctr', 'avg_rank', 'avg_cpc', 'total_cost',
    'total_conversions', 'cost_per_conversion', 'total_conv_amount',
    'total_conv_rate', 'total_roas',
    'direct_conversions', 'direct_conv_rate', 'direct_conv_amount',
    'direct_cost_per_conv', 'direct_roas',
    'indirect_conversions', 'indirect_cost_per_conv', 'indirect_conv_amount',
    'indirect_conv_rate', 'indirect_roas',
    'registered_at',
]

FLOAT_COLS = {
    'ctr', 'avg_rank', 'avg_cpc', 'total_conv_rate', 'total_roas',
    'direct_conv_rate', 'direct_roas', 'direct_cost_per_conv',
    'indirect_cost_per_conv', 'indirect_conv_rate', 'indirect_roas',
    'cost_per_conversion',
}


def _parse_num(text, is_float=False):
    if not text:
        return None
    cleaned = re.sub(r'[^\d.\-]', '', str(text))
    if not cleaned or cleaned == '-':
        return None
    try:
        return float(cleaned) if is_float else int(float(cleaned))
    except (ValueError, TypeError):
        return None


def _dismiss_popups(driver):
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except NoAlertPresentException:
        pass
    for sel in ["div.MuiDialog-root button", "div.MuiModal-root button", "button[aria-label='닫기']"]:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            try: el.click(); time.sleep(0.3)
            except: pass


def _do_login(driver, login_id, password):
    driver.get(ADOFFICE_URL)
    time.sleep(3)
    _dismiss_popups(driver)

    try:
        url = driver.current_url
        if 'adoffice.11st.co.kr' in url and 'login' not in url.lower():
            return True
    except:
        pass

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'memId')))
        driver.find_element(By.ID, 'memId').clear()
        driver.find_element(By.ID, 'memId').send_keys(login_id)
        driver.find_element(By.ID, 'memPwd').clear()
        driver.find_element(By.ID, 'memPwd').send_keys(password)
        btn = driver.find_element(By.ID, 'loginbutton')
        driver.execute_script("arguments[0].click();", btn)
        WebDriverWait(driver, 20).until(
            lambda d: 'adoffice.11st.co.kr' in d.current_url and 'login' not in d.current_url.lower()
        )
        time.sleep(2)
        _dismiss_popups(driver)
        return True
    except Exception as e:
        logger.error(f'[11st-AI:{login_id}] 로그인 실패: {e}')
        return False


def _navigate_to_campaigns(driver):
    try:
        focus = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//span[contains(@class,'MuiListItemText-primary') and contains(text(),'포커스클릭')]"))
        )
        driver.execute_script("arguments[0].click();", focus)
        time.sleep(1)
        items = driver.find_elements(By.XPATH, "//span[text()='광고관리']")
        for item in items:
            if item.is_displayed():
                driver.execute_script("arguments[0].click();", item)
                break
        WebDriverWait(driver, 15).until(EC.url_contains('/cpc/focus/campaigns'))
        time.sleep(3)
        return True
    except Exception as e:
        logger.error(f'캠페인 페이지 이동 실패: {e}')
        return False


def _collect_campaigns(driver, login_id, log_fn=None):
    def log(m):
        if log_fn: log_fn(f'[11st-AI:{login_id}] {m}')

    results = []
    try:
        campaigns = driver.execute_script(JS_PARSE_CAMPAIGNS)
        if not campaigns:
            log('캠페인 없음')
            return results

        now = timezone.now()
        for camp in campaigns:
            data = {
                'eleven_id': login_id,
                'campaign_name': camp['name'],
                'is_ai': camp['is_ai'],
                'onoff': camp['onoff'],
                'status': camp['status'],
                'collected_at': now,
            }

            perf = camp.get('perf', [])
            for i, col_name in enumerate(PERF_COLUMNS):
                if i < len(perf):
                    val = perf[i]
                    if col_name == 'registered_at':
                        data['campaign_registered_at'] = val
                    else:
                        is_float = col_name in FLOAT_COLS
                        db_col = 'total_roas_pct' if col_name == 'total_roas' else col_name
                        data[db_col] = _parse_num(val, is_float)

            # AI 캠페인이면 상세 페이지에서 budget/roas 추출
            if camp['is_ai']:
                try:
                    links = driver.find_elements(By.XPATH, f"//a[contains(text(),'{camp['name']}')]")
                    for link in links:
                        if link.is_displayed():
                            driver.execute_script("arguments[0].click();", link)
                            time.sleep(3)
                            if '/campaigns/ai/' in driver.current_url:
                                detail = driver.execute_script(JS_PARSE_AI_DETAIL)
                                if detail:
                                    if detail.get('daily_budget'): data['daily_budget'] = detail['daily_budget']
                                    if detail.get('target_roas'): data['target_roas'] = detail['target_roas']
                                    if detail.get('exposure_period'): data['exposure_period'] = detail['exposure_period']
                                driver.back()
                                time.sleep(2)
                            break
                except Exception as e:
                    log(f'AI 상세 추출 실패: {e}')

            results.append(data)
            status = 'ON' if camp['onoff'] else 'OFF'
            ai_tag = '[AI]' if camp['is_ai'] else ''
            log(f'{ai_tag} {camp["name"]}: {status} cost={data.get("total_cost", 0)}')
    except Exception as e:
        log(f'캠페인 수집 오류: {e}')

    return results


def _logout(driver):
    try:
        driver.get(LOGOUT_URL)
        time.sleep(2)
    except:
        pass


def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, St11AdofficeCampaign, CrawlerLog

    qs = CrawlerAccount.objects.filter(platform='11st', is_active=True)
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    qs = qs.exclude(crawling_status='차단됨')

    if not qs.exists():
        if log_fn: log_fn('활성 11번가 계정 없음')
        return {'collected': 0, 'failed': 0}

    all_results, driver = [], None
    try:
        driver = create_driver()
        for acct in qs:
            try:
                _logout(driver)
                driver.delete_all_cookies()

                if not _do_login(driver, acct.login_id, acct.password_enc):
                    if log_fn: log_fn(f'[11st-AI:{acct.login_id}] 로그인 실패')
                    continue

                if not _navigate_to_campaigns(driver):
                    continue

                results = _collect_campaigns(driver, acct.login_id, log_fn)
                all_results.extend(results)
            except Exception as e:
                if log_fn: log_fn(f'[11st-AI:{acct.login_id}] 오류: {e}')
    finally:
        if driver:
            try: driver.quit()
            except: pass
        stop_display()

    for r in all_results:
        St11AdofficeCampaign.objects.create(**r)

    CrawlerLog.objects.create(platform='11st', level='info', message=f'AI 캠페인 수집: {len(all_results)}건')
    if log_fn: log_fn(f'11번가 AI 수집 완료: {len(all_results)}건')
    return {'collected': len(all_results), 'failed': 0}

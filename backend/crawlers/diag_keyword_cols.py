"""진단: 키워드 탭 결과표의 헤더/셀 실제 구조 덤프(컬럼 매핑 교정용). 읽기전용."""
import time


def run(login_id='rejoice666', product_no='2786152076', log_fn=print):
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display
    from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
    from crawlers.gmarket_keyword_crawler import _select_keyword_tab, _select_seller_gmarket, REPORT_URL
    from crawlers.gmarket_ad_report_crawler import _set_period_thismonth
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    a = CrawlerAccount.objects.get(platform='gmarket', login_id=login_id)
    ok, reason = guard.preflight('키워드컬럼진단', platform='gmarket')
    if not ok:
        log_fn(f'⏭️ {reason}'); return
    driver = None
    try:
        driver = create_driver(kill_existing=True)
        if not (_try_cookie_login(driver, a) or
                (_full_login(driver, login_id, a.password_enc) and (_save_cookies(driver, a) or True))):
            log_fn('로그인 실패'); return
        driver.get(REPORT_URL); time.sleep(5)
        _select_keyword_tab(driver)
        _set_period_thismonth(driver)
        try:
            driver.execute_script("ReportList.GetTotalSearch();"); time.sleep(3)
        except Exception:
            pass
        _select_seller_gmarket(driver)
        si = driver.find_element(By.ID, 'searchText')
        si.clear(); si.send_keys(product_no); time.sleep(0.8); si.send_keys(Keys.RETURN); time.sleep(4)
        # 헤더
        ths = driver.find_elements(By.CSS_SELECTOR, "#spanKeywordSearchData table thead th")
        log_fn(f'=== 헤더 {len(ths)}칸 ===')
        for i, th in enumerate(ths):
            log_fn(f'  th[{i}] = "{th.text.strip()}"')
        # 첫 데이터 행
        rows = driver.find_elements(By.CSS_SELECTOR, "#spanKeywordSearchData table tbody tr")
        log_fn(f'=== 행 {len(rows)}개 ===')
        for ri, row in enumerate(rows[:3]):
            tds = row.find_elements(By.CSS_SELECTOR, "td")
            log_fn(f'  row[{ri}] {len(tds)}칸: ' + ' | '.join(f'[{i}]{td.text.strip()}' for i, td in enumerate(tds)))
    finally:
        try:
            if driver: driver.quit()
        except Exception:
            pass
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass

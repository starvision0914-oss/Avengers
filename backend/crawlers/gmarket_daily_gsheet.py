"""지마켓 '일자별' 광고비 리포트(CPC + AI) → 계정별 구글시트 업로드.

원래 스탠드얼론 스크립트가 하던 일을 Avengers 크롤 세션에 통합:
  - 상품별 광고비 크롤(같은 ESM 로그인)에서 일자별 리포트도 같이 다운로드
  - CPC=cpc/report/dailyReport, AI=Remarketing/Report (일자별)
  - AI/CPC 서로 다른 스프레드시트, 워크시트명=계정ID
  - 기간: 매월 1일=전월 / 그 외=당월. 누락 날짜는 빈행으로 채움 + 합계행

⚠️ 서버 서비스계정(credentials.json 이메일)이 두 스프레드시트에 '편집자'로 공유돼야 함.
"""
import os
import time
import calendar
import logging
from datetime import date, timedelta

import pandas as pd

from crawlers import gsheet_upload
from crawlers.gmarket_ad_report_crawler import (
    DL, _clear_dl, _wait_dl, _set_period_thismonth, _set_period_month,
)

logger = logging.getLogger(__name__)

AI_KEY = '1vqer9yv5h0wGvH7a1hyT9f3WSaVVmhyx2wUltfkSOQc'    # AI매출업(일자별)
CPC_KEY = '10YWiqQcDdzij_eTmoTFPN9hGe2h3xsWlkIaKG4p4m80'   # CPC(일자별)

DAILY = {
    'cpc': {
        'url': 'https://ad.esmplus.com/cpc/report/dailyReport',
        'search_js': 'ReportList.GetTotalSearch();',
        'search_xpath': '//*[@id="dvSearchControl"]/table/tbody/tr[1]/td[2]/button/span',
        'down_js': "ReportList.ExcelDown('Day');",   # 일자별=Day (상품별 Good / 월별 Mon)
        'down_xpath': "//button[contains(@class,'btn_result_download')][contains(@onclick,'Day')]",
        'key': CPC_KEY,
    },
    'ai': {
        'url': 'https://ad.esmplus.com/Remarketing/Report',
        'tab_xpath': '//*[@id="reportsTab2"]',   # 일자별 탭 (기본은 월별이라 반드시 클릭)
        'search_js': 'RemarketingReport.Display.SearchMain();',
        'search_xpath': '//*[@id="dvSearchControl"]/table/tbody/tr[1]/td[2]/div/button/span',
        'down_js': "RemarketingReport.ExcelDown.ExcelDown('daily');",   # 일별=daily (월별 monthly)
        'down_xpath': '//*[@id="reportsPanel2"]/div[1]/div/button/span',
        'key': AI_KEY,
    },
}


def _log(fn, m):
    logger.info(m)
    if fn:
        fn(m)


def target_period(today=None):
    """1일=전월 / 그 외=당월 → (year, month)."""
    today = today or date.today()
    if today.day == 1:
        return (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    return today.year, today.month


def _try_click_xpath(driver, xpath):
    from selenium.webdriver.common.by import By
    els = driver.find_elements(By.XPATH, xpath)
    if els:
        driver.execute_script("arguments[0].click();", els[0])
        return True
    return False


def _do_search(driver, cfg):
    try:
        driver.execute_script(cfg['search_js'])
        return True
    except Exception:
        return _try_click_xpath(driver, cfg['search_xpath'])


def _do_download(driver, cfg):
    """JS 다운로드 시도 → 실패 시 버튼 XPath 클릭. 다운로드 파일경로 반환."""
    _clear_dl()
    js_ok = True
    try:
        driver.execute_script(cfg['down_js'])
    except Exception:
        js_ok = False
    f = _wait_dl(20)
    if not f and not js_ok:
        if _try_click_xpath(driver, cfg['down_xpath']):
            f = _wait_dl(35)
    elif not f:   # JS는 됐는데 파일 안 옴 → 버튼도 시도
        if _try_click_xpath(driver, cfg['down_xpath']):
            f = _wait_dl(35)
    return f


def _download_daily(driver, login_id, ad_type, year, month, log_fn):
    cfg = DAILY[ad_type]
    today = date.today()
    is_current = (year == today.year and month == today.month)
    driver.get(cfg['url'])
    time.sleep(6)
    # 일자별 탭 클릭(AI는 기본이 월별이라 반드시 일자별 탭으로 전환)
    if cfg.get('tab_xpath'):
        if _try_click_xpath(driver, cfg['tab_xpath']):
            _log(log_fn, f'  [{login_id}/{ad_type}] 일자별 탭 클릭')
            time.sleep(3)
    if is_current:
        _set_period_thismonth(driver)
    else:
        _set_period_month(driver, year, month)
    if not _do_search(driver, cfg):
        _log(log_fn, f'  [{login_id}/{ad_type}] 조회 실패')
        return None
    time.sleep(8)
    f = _do_download(driver, cfg)
    if not f or os.path.getsize(f) < 100:
        _log(log_fn, f'  [{login_id}/{ad_type}] ❌ 일자별 다운로드 실패')
        return None
    return f


def _build_daily_matrix(path, year, month):
    """일자별 엑셀 → [헤더] + [날짜행(누락=빈행)] + [합계행]. 첫 열=날짜."""
    df = pd.read_excel(path)
    if df.empty or len(df.columns) < 2:
        return None
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    numcols = list(df.columns[1:])
    for c in numcols:
        df[c] = pd.to_numeric(
            df[c].astype(str).str.replace("'", "", regex=False).str.replace(",", "", regex=False),
            errors='coerce')
    last_day = calendar.monthrange(year, month)[1]
    all_dates = pd.date_range(start=date(year, month, 1), end=date(year, month, last_day))
    full = (pd.DataFrame(index=all_dates)
            .join(df.set_index(date_col), how='left')
            .reset_index().rename(columns={'index': date_col}))

    header = [str(date_col)] + [str(c) for c in numcols]
    data = [header]
    sums = {c: 0.0 for c in numcols}
    for _, r in full.iterrows():
        d = r[date_col]
        row = [d.strftime('%Y-%m-%d') if pd.notnull(d) else '']
        for c in numcols:
            v = r[c]
            if pd.notnull(v):
                row.append(str(int(v)) if float(v).is_integer() else str(v))
                sums[c] += float(v)
            else:
                row.append('')
        data.append(row)
    totals = ['합계'] + [str(int(sums[c])) if float(sums[c]).is_integer() else str(sums[c]) for c in numcols]
    data.append(totals)
    return data


def run_for_account(login_id, log_fn=None, gsheet=True, year=None, month=None,
                    driver=None, ss_cpc=None, ss_ai=None):
    """한 계정의 CPC+AI 일자별 다운로드 → 시트 업로드. driver/ss가 주어지면 재사용(세션 통합)."""
    if year is None or month is None:
        year, month = target_period()
    own_driver = driver is None
    res = {}
    if own_driver:
        from apps.cpc.models import CrawlerAccount
        from crawlers.browser import create_driver, stop_display
        from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
        a = CrawlerAccount.objects.filter(platform='gmarket', login_id=login_id).first()
        if not a:
            return {'login': False, 'error': '계정없음'}
        driver = create_driver(download_dir=DL, kill_existing=True)
        try:
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
        except Exception:
            pass
        if not (_try_cookie_login(driver, a) or
                (_full_login(driver, a.login_id, a.password_enc) and (_save_cookies(driver, a) or True))):
            try: driver.quit()
            except Exception: pass
            return {'login': False}
        if gsheet and ss_cpc is None:
            ss_cpc = gsheet_upload.open_spreadsheet(CPC_KEY)
            ss_ai = gsheet_upload.open_spreadsheet(AI_KEY)
    try:
        for ad_type, ss in (('cpc', ss_cpc), ('ai', ss_ai)):
            try:
                f = _download_daily(driver, login_id, ad_type, year, month, log_fn)
                if not f:
                    res[ad_type] = {'ok': False}
                    continue
                data = _build_daily_matrix(f, year, month)
                if not data:
                    res[ad_type] = {'ok': False, 'error': '빈데이터'}
                    continue
                if gsheet:
                    ok = gsheet_upload.upload_rows(data, login_id, ss, log=lambda m: _log(log_fn, m))
                    res[ad_type] = {'ok': ok, 'rows': len(data) - 2}
                else:
                    _log(log_fn, f'  [{login_id}/{ad_type}] {len(data) - 2}일 (업로드 생략) 헤더={data[0]}')
                    res[ad_type] = {'ok': True, 'rows': len(data) - 2, 'header': data[0]}
            except Exception as e:
                _log(log_fn, f'  [{login_id}/{ad_type}] 오류 {str(e)[:140]}')
                res[ad_type] = {'ok': False, 'error': str(e)[:140]}
    finally:
        if own_driver:
            try: driver.quit()
            except Exception: pass
            from crawlers.browser import stop_display
            try: stop_display()
            except Exception: pass
    return res


def run_all_accounts(log_fn=None, account_filter=None, gsheet=True, year=None, month=None):
    """전 대표계정 일자별 → 시트. (단독 실행용 — 락 획득/해제 포함)"""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display
    from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
    if year is None or month is None:
        year, month = target_period()

    ok, reason = guard.preflight('지마켓일자별gsheet', platform='gmarket')
    if not ok:
        _log(log_fn, f'⏭️ 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    accts = list(qs.order_by('display_order', 'login_id'))
    if not account_filter:
        accts = [a for a in accts if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]
    _log(log_fn, f'[gmkt-daily-gsheet] {year}-{month:02d} 계정 {len(accts)}개 / gsheet={gsheet}')

    ss_cpc = ss_ai = None
    if gsheet:
        ss_cpc = gsheet_upload.open_spreadsheet(CPC_KEY)
        ss_ai = gsheet_upload.open_spreadsheet(AI_KEY)

    summary = {}
    driver = None
    try:
        for a in accts:
            if guard.is_blocked(platform='gmarket')[0]:
                _log(log_fn, '⛔ 차단 감지 — 중단'); break
            driver = create_driver(download_dir=DL, kill_existing=True)
            try:
                driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
            except Exception:
                pass
            try:
                if not (_try_cookie_login(driver, a) or
                        (_full_login(driver, a.login_id, a.password_enc) and (_save_cookies(driver, a) or True))):
                    _log(log_fn, f'[{a.login_id}] 로그인 실패 — 건너뜀')
                    summary[a.login_id] = {'login': False}
                    continue
                summary[a.login_id] = run_for_account(
                    a.login_id, log_fn=log_fn, gsheet=gsheet, year=year, month=month,
                    driver=driver, ss_cpc=ss_cpc, ss_ai=ss_ai)
            finally:
                try: driver.quit()
                except Exception: pass
                driver = None
            time.sleep(3)
    finally:
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass
    return summary

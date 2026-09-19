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
    # 광고 집행 자체가 없는 계정은 '검색결과 : 총 0건'으로 정상 표시 → 다운로드해도 0바이트라
    # 항상 '다운로드 실패'로 오판됐었다(2026-08-20 확인). 업로드할 데이터가 없을 뿐 정상 상태.
    import re
    from selenium.webdriver.common.by import By
    if re.search(r'총\s*0\s*건', driver.find_element(By.TAG_NAME, 'body').text):
        _log(log_fn, f'  [{login_id}/{ad_type}] 일자별 광고 집행 0건(정상)')
        return 'ZERO'
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


_DEFAULT_HEADER = ['날짜', '노출수', '클릭수', '광고비', '전환수', '전환금액']


def _build_zero_matrix(ss, login_id, year, month):
    """광고 집행 0건(정상)인 달 — 예전엔 업로드 자체를 건너뛰어 시트가 지난 값에서 멈춰
    보였음(2026-09-03 사용자 지적). 기존 워크시트 헤더(계정마다 컬럼 구성이 다름)를 그대로
    재사용해 전 날짜를 0으로 채워 올린다 — 시트가 없으면 기본 6컬럼 헤더로 새로 만듦."""
    header = None
    if ss is not None:
        try:
            header = ss.worksheet(login_id).row_values(1)
        except Exception:
            header = None
    if not header or len(header) < 2:
        header = _DEFAULT_HEADER
    numcols = header[1:]
    last_day = calendar.monthrange(year, month)[1]
    data = [header]
    for d in range(1, last_day + 1):
        data.append([date(year, month, d).strftime('%Y-%m-%d')] + ['0'] * len(numcols))
    data.append(['합계'] + ['0'] * len(numcols))
    return data


def _build_auction_matrix(login_id, cost_type, year, month):
    """옥션 거래원장(GmarketCostHistory market='auction') 비용만으로 [헤더,날짜행...,합계행]
    매트릭스를 만든다(2026-09-19 사용자 요청 — 옥션과 지마켓 집계를 완전히 분리해달라는 요청에
    따라, 예전처럼 지마켓 시트 '총비용'에 합산하지 않고 계정별 '{login_id}_옥션' 탭에 따로
    올린다). cost_type: 'CPC' 또는 'AI매출업'. 데이터가 없어도 0으로 채운 전체 날짜를 반환
    (매일 새로 만드는 멱등 스냅샷)."""
    from django.db.models import Sum
    from apps.cpc.models import GmarketCostHistory
    me = calendar.monthrange(year, month)[1]
    by_date = {}
    for r in (GmarketCostHistory.objects
              .filter(seller_id=login_id, market='auction', transaction_type=cost_type,
                      use_date__gte=date(year, month, 1), use_date__lte=date(year, month, me))
              .values('use_date').annotate(s=Sum('amount'))):
        v = abs(r['s'] or 0)
        if v:
            by_date[r['use_date']] = v
    header = ['날짜', '총비용']
    data = [header]
    total = 0
    for day in range(1, me + 1):
        d = date(year, month, day)
        v = by_date.get(d, 0)
        total += v
        data.append([d.strftime('%Y-%m-%d'), str(int(v))])
    data.append(['합계', str(int(total))])
    return data


def _upload_auction_tab(login_id, cost_type, ss, year, month, log_fn=None):
    """_build_auction_matrix 결과를 계정별 '{login_id}_옥션' 워크시트에 업로드. 실패해도
    예외를 밖으로 던지지 않음(본수집 비차단)."""
    try:
        data = _build_auction_matrix(login_id, cost_type, year, month)
        ok = gsheet_upload.upload_rows(data, f'{login_id}_옥션', ss, log=lambda m: _log(log_fn, m))
        return {'ok': ok, 'rows': len(data) - 2}
    except Exception as e:
        _log(log_fn, f'  [{login_id}/옥션-{cost_type}] 업로드 오류 {str(e)[:120]}')
        return {'ok': False, 'error': str(e)[:120]}


def _merge_newadcenter_live(driver, data, login_id, year, month, log_fn=None):
    """신규 광고센터(adcenter.esmplus.com)는 구광고센터(ad.esmplus.com)와 완전히 별도
    시스템이라 dailyReport 화면엔 이 캠페인들이 전혀 안 잡힘 — /report 페이지의
    '일별×날짜별' 상세리포트(계정 전체 총액, CPC/AI 구분 없음)를 직접 조회해서 CPC
    시트의 '총비용'에 합산한다(2026-09-11 신설, 2026-09-17부터는 AI 시트 자체가 이 데이터로
    대체됨 — fetch_daily_report_xlsx 참고. 지마켓끼리의 합산이라 옥션/지마켓 분리 대상 아님).
    가능구간: 이번달 1일~어제(전월 없음, 캘린더가 현재 표시 중인 달 안에서만 클릭
    가능해서 — 1일에 실행되면 어제=전월이라 클릭 불가 → 스킵). 최대 3개월 전까지도
    조회는 가능하나 여기선 당월치만 씀. 반환: 추가된 총액."""
    from datetime import date, timedelta
    from django.utils import timezone
    from apps.cpc.models import CrawlerAccount
    from crawlers.gmarket_new_adcenter_control import fetch_daily_report

    today = timezone.localdate()
    if (year, month) != (today.year, today.month):
        return 0
    since_date, until_date = date(year, month, 1), today - timedelta(days=1)
    if since_date > until_date:
        return 0

    acct = CrawlerAccount.objects.filter(platform='gmarket', login_id=login_id).first()
    if not acct:
        return 0
    by_date = fetch_daily_report(driver, login_id, acct.password_enc, since_date, until_date, log_fn)
    if not by_date:
        return 0

    hdr = data[0]
    if '총비용' not in hdr:
        return 0
    ci = hdr.index('총비용')
    added = 0
    for row in data[1:]:
        if not row or str(row[0]).strip() == '합계':
            continue
        dt = str(row[0])[:10]
        if dt in by_date and ci < len(row):
            cur = int(str(row[ci]).replace(',', '') or 0) if row[ci] else 0
            row[ci] = str(cur + by_date[dt]); added += by_date[dt]
    if added:
        for row in data[1:]:
            if row and str(row[0]).strip() == '합계' and ci < len(row):
                cur = int(str(row[ci]).replace(',', '') or 0) if row[ci] else 0
                row[ci] = str(cur + added)
    return added


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
            # 2026-09-17 사용자 확정: 9월부터 AI 워크시트는 구광고센터(ad.esmplus.com)
            # Remarketing/Report 대신 신규광고센터(adcenter.esmplus.com) 일자별 리포트로
            # 대체 — 8월까지 쌓인 구형식 데이터는 그대로 두고, 이 아래부터는 새로 채워진다.
            # '종합' 시트가 D열(광고비)/J열(매출액)을 IMPORTRANGE로 참조해서 컬럼 위치를
            # 그대로 보존해야 하므로 fetch_daily_report_xlsx()가 이미 그렇게 재배치해서 줌.
            if ad_type == 'ai':
                try:
                    from apps.cpc.models import CrawlerAccount as _CA
                    from crawlers.gmarket_new_adcenter_control import fetch_daily_report_xlsx as _fetch_newad
                    from crawlers.gmarket_new_adcenter_control import NEWAD_DL as _NEWAD_DL
                    from datetime import date as _date, timedelta as _td
                    _acc = _CA.objects.filter(platform='gmarket', login_id=login_id).first()
                    _since, _until = _date.today().replace(day=1), _date.today() - _td(days=1)
                    if _acc and _since <= _until:
                        # fetch_daily_report_xlsx()는 다운로드된 엑셀을 NEWAD_DL에서 찾는데,
                        # 이 driver는 위에서 CDP 다운로드 경로를 DL(옛 광고센터용)로 잡아둔
                        # 채로 재사용돼 둘이 어긋나 있었다 — 실제 파일은 DL에 떨어지는데
                        # fetch_daily_report_xlsx는 NEWAD_DL만 20초씩 3번 폴링하다 타임아웃
                        # 나서 매 계정·매일 "데이터없음"으로 잡혔다(2026-09-19 실측 확인,
                        # 로그엔 전 계정 100% "엑셀 다운로드 실패(3회 재시도 후)"). 여기서
                        # 호출 직전에 CDP 경로를 NEWAD_DL로 맞춰준다.
                        try:
                            driver.execute_cdp_cmd(
                                'Page.setDownloadBehavior',
                                {'behavior': 'allow', 'downloadPath': _NEWAD_DL})
                        except Exception:
                            pass
                        data = _fetch_newad(driver, login_id, _acc.password_enc, _since, _until, log_fn=log_fn)
                        try:
                            driver.execute_cdp_cmd(
                                'Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
                        except Exception:
                            pass
                    else:
                        data = None
                    if not data:
                        res['ai'] = {'ok': False, 'error': '신규광고센터 데이터없음'}
                        continue
                    if gsheet:
                        ok = gsheet_upload.upload_rows(data, login_id, ss, log=lambda m: _log(log_fn, m))
                        res['ai'] = {'ok': ok, 'rows': len(data) - 1}
                    else:
                        res['ai'] = {'ok': True, 'rows': len(data) - 1, 'header': data[0]}
                except Exception as e:
                    _log(log_fn, f'  [{login_id}/ai] 신규광고센터 오류 {str(e)[:140]}')
                    res['ai'] = {'ok': False, 'error': str(e)[:140]}
                if gsheet:
                    res['auction_ai'] = _upload_auction_tab(login_id, 'AI매출업', ss, year, month, log_fn)
                continue
            try:
                f = _download_daily(driver, login_id, ad_type, year, month, log_fn)
                if not f:
                    res[ad_type] = {'ok': False}
                    continue
                if f == 'ZERO':
                    data = _build_zero_matrix(ss, login_id, year, month)
                else:
                    data = _build_daily_matrix(f, year, month)
                    if not data:
                        res[ad_type] = {'ok': False, 'error': '빈데이터'}
                        continue
                # 2026-09-19 사용자 요청: 옥션과 지마켓 집계를 완전히 분리 — 더 이상 지마켓
                # '총비용'에 옥션 거래원장을 합산하지 않고, 계정별 '{login_id}_옥션' 탭에
                # 따로 올린다(아래 gsheet 업로드 직후 처리).
                # 신규광고센터(adcenter.esmplus.com, 지마켓 전용)는 구리포트 화면에 안 잡히는
                # 별도 시스템이라 CPC 시트 '총비용'에 계속 합산(지마켓끼리라 분리 대상 아님).
                if ad_type == 'cpc':
                    try:
                        _newad_add = _merge_newadcenter_live(driver, data, login_id, year, month, log_fn)
                        if _newad_add:
                            _log(log_fn, f'  [{login_id}/{ad_type}] 신규광고센터 +{_newad_add:,}원 합산')
                    except Exception as _e:
                        _log(log_fn, f'  [{login_id}/{ad_type}] 신규광고센터 합산 오류 {str(_e)[:80]}')
                if gsheet:
                    ok = gsheet_upload.upload_rows(data, login_id, ss, log=lambda m: _log(log_fn, m))
                    res[ad_type] = {'ok': ok, 'rows': len(data) - 2}
                    if ad_type == 'cpc':
                        res['auction_cpc'] = _upload_auction_tab(login_id, 'CPC', ss, year, month, log_fn)
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

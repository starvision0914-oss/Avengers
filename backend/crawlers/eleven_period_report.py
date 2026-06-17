"""11번가 adoffice '기간별 보고서'(일자별 27컬럼) → 계정별 구글시트 업로드.

페이지 /sellers/{sn}/cpc/focus/report/period 로 직접 이동 → 당월/전월 선택 → 조회 → 다운로드
(검증된 UI 방식). 받은 CSV(UTF-16·탭, 27컬럼: 합계+날짜별)에서 **누락된 날짜는 빈행('-')으로
삽입**해 해당 월 전체 날짜를 채운 뒤 시트에 업로드.

기간: 매월 1일 실행=전월 / 그 외=당월. (auto)
"""
import os
import glob
import time
import csv as _csv
import io
import calendar
import datetime as dt
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .browser import DEFAULT_UA, _ensure_display, _kill_stale_chrome, _STEALTH_JS
from .eleven_product_roas import _login

logger = logging.getLogger('crawler')
ADOFFICE = 'https://adoffice.11st.co.kr'
DL_DIR = '/tmp/adoffice_period_dl'

XP_DROPDOWN = '//*[@id="root"]/div/div[2]/div[2]/div[1]/form/div[1]/div[2]/div/div[1]/div'
XP_QUERY = '//*[@id="root"]/div/div[2]/div[2]/div[1]/form/div[2]/button[2]'
XP_DOWNLOAD = '//*[@id="root"]/div/div[2]/div[2]/div[2]/div[2]/button[2]'


def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    os.makedirs(DL_DIR, exist_ok=True)
    _kill_stale_chrome(); time.sleep(1); _ensure_display()
    o = Options()
    for x in ('--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--window-size=1680,950',
              '--disable-extensions', '--ignore-certificate-errors',
              '--disable-blink-features=AutomationControlled', '--lang=ko-KR'):
        o.add_argument(x)
    o.add_argument(f'--user-agent={DEFAULT_UA}')
    o.add_experimental_option('excludeSwitches', ['enable-automation'])
    o.add_experimental_option('prefs', {'download.default_directory': DL_DIR,
                                        'download.prompt_for_download': False,
                                        'download.directory_upgrade': True, 'safebrowsing.enabled': True})
    d = webdriver.Chrome(options=o)
    d.set_page_load_timeout(60); d.implicitly_wait(5)
    try:
        d.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': _STEALTH_JS})
    except Exception:
        pass
    return d


def _click(driver, xp, t=15):
    el = WebDriverWait(driver, t).until(EC.element_to_be_clickable((By.XPATH, xp)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el); time.sleep(0.4)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)


def _read_csv(fp):
    raw = None
    for enc in ('utf-16', 'utf-8-sig', 'cp949'):
        try:
            raw = open(fp, encoding=enc).read(); break
        except Exception:
            continue
    if raw is None:
        return []
    rows = list(_csv.reader(io.StringIO(raw), delimiter='\t'))
    if rows and len(rows[0]) < 3:        # 탭이 아니면 콤마 폴백
        rows = list(_csv.reader(io.StringIO(raw)))
    return rows


def collect_period_rows(driver, sn, period_text, log):
    """기간별 페이지에서 period_text(당월/전월) 보고서 다운로드 → rows(list of list) 반환."""
    for f in glob.glob(DL_DIR + '/*'):
        try: os.remove(f)
        except Exception: pass
    driver.get(f'{ADOFFICE}/sellers/{sn}/cpc/focus/report/period'); time.sleep(6)
    _click(driver, XP_DROPDOWN, 12); time.sleep(0.5)
    _click(driver, f'//li[@role="option" and normalize-space()="{period_text}"]', 8); time.sleep(0.5)
    _click(driver, XP_QUERY, 12); time.sleep(3)
    _click(driver, XP_DOWNLOAD, 12)
    fp = None
    for _ in range(40):
        files = glob.glob(DL_DIR + '/*.csv')
        if files:
            fp = max(files, key=os.path.getmtime); break
        time.sleep(1)
    if not fp:
        raise Exception('다운로드 파일 없음(조회결과 없음 가능)')
    rows = _read_csv(fp)
    if not rows or '날짜' not in (rows[0][0] if rows[0] else ''):
        raise Exception(f'보고서 형식 이상: 헤더={rows[0] if rows else None}')
    return rows


def fill_missing_dates(rows, d0, d1):
    """rows(헤더+합계+날짜별)에서 d0~d1 사이 누락 날짜를 빈행('-')으로 삽입.
    결과: [헤더, 합계(있으면), d0행, d0+1행, ... d1행]."""
    header = rows[0]
    ncol = len(header)
    summary = None
    by_date = {}
    for r in rows[1:]:
        if not r:
            continue
        key = (r[0] or '').strip()
        if key == '합계':
            summary = r
        elif key:
            by_date[key] = r
    out = [header]
    if summary:
        out.append(summary)
    cur = d0
    while cur <= d1:
        k = cur.strftime('%Y-%m-%d')
        out.append(by_date.get(k, [k] + ['-'] * (ncol - 1)))
        cur += dt.timedelta(days=1)
    return out


def _period_for(today):
    """매월 1일=전월 / 그 외=당월. (period_text, d0, d1, label) 반환."""
    if today.day == 1:
        last_prev = today - dt.timedelta(days=1)
        d0 = last_prev.replace(day=1)
        d1 = last_prev
        return '전월', d0, d1, f'{d0:%Y-%m}'
    d0 = today.replace(day=1)
    d1 = today - dt.timedelta(days=1)            # adoffice는 어제까지 제공
    if d1 < d0:                                   # 매월 1일이 아닌데 d1<d0인 경우 방지(=오늘이 1일 아님 보장됐으나 안전)
        d1 = d0
    return '당월', d0, d1, f'{d0:%Y-%m}'


def collect_period_for_account(driver, login_id, password_enc, period_text, d0, d1, sheet, log):
    """이미 만들어진(로그인된) driver로 기간별 보고서 다운로드+구글시트 업로드.
    _login 멱등(이미 로그인이면 세션 재사용) → 상품ROAS 크롤과 로그인 1회 공유 가능."""
    sn = _login(driver, login_id, password_enc)
    if not sn:
        raise Exception('adoffice 로그인 실패')
    rows = collect_period_rows(driver, sn, period_text, log)
    filled = fill_missing_dates(rows, d0, d1)
    filled = [[('' if str(c).strip() == '-' else c) for c in r] for r in filled]
    log(f'[{login_id}] 기간별 {len(filled)}행 (헤더+합계+{(d1 - d0).days + 1}일)')
    if sheet is not None:
        from .gsheet_upload import upload_rows
        upload_rows(filled, login_id, sheet, log)
    return len(filled)


def run_all_accounts(log_fn=None, account_filter=None, gsheet=True):
    from apps.cpc.models import CrawlerAccount
    from apps.cpc.eleven_block_guard import exclude_perma_banned
    from django.utils import timezone

    def log(m):
        logger.info(m)
        if log_fn:
            log_fn(m)

    period_text, d0, d1, label = _period_for(timezone.localdate())
    log(f'기간별 보고서 수집: {period_text} ({d0}~{d1})')

    sheet = None
    if gsheet:
        from . import gsheet_upload as _gs
        if _gs.is_configured():
            try:
                sheet = _gs.open_spreadsheet()
                log('구글시트 연결 OK')
            except Exception as e:
                log(f'구글시트 연결 실패: {str(e)[:120]}')
        else:
            log('구글시트 미설정 — 업로드 생략')

    qs = exclude_perma_banned(CrawlerAccount.objects.filter(platform='11st', is_active=True))
    accounts = [a for a in qs if (not account_filter or a.login_id in account_filter)]
    if not account_filter:
        # 크론(전체) 실행 시: 해당 기간 광고비 0인 계정(광고 안 돌림)은 제외 → 빈 시트 방지, 시간 절약
        from apps.cpc.models import St11ProductDaily
        from django.db.models import Sum
        active = {r['eleven_id'] for r in St11ProductDaily.objects.filter(
            stat_date__gte=d0, stat_date__lte=d1).values('eleven_id').annotate(c=Sum('cost'))
            if (r['c'] or 0) > 0}
        before = len(accounts)
        accounts = [a for a in accounts if a.login_id in active]
        log(f'광고활성 필터: {before}→{len(accounts)}계정 (광고비0 제외)')
    log(f'대상 {len(accounts)}계정')

    ok = fail = 0
    for a in accounts:
        driver = None
        try:
            driver = _make_driver()
            sn = _login(driver, a.login_id, a.password_enc)
            if not sn:
                raise Exception('adoffice 로그인 실패')
            rows = collect_period_rows(driver, sn, period_text, log)
            filled = fill_missing_dates(rows, d0, d1)
            # '-'(데이터 없음 표시) → 빈 칸으로
            filled = [[('' if str(c).strip() == '-' else c) for c in r] for r in filled]
            log(f'[{a.login_id}] {len(filled)}행 (헤더+합계+{ (d1-d0).days+1 }일)')
            if sheet is not None:
                from .gsheet_upload import upload_rows
                upload_rows(filled, a.login_id, sheet, log)
            ok += 1
        except Exception as e:
            fail += 1
            log(f'[{a.login_id}] 실패: {str(e)[:140]}')
        finally:
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass
        time.sleep(2)
    log(f'완료: 성공={ok} 실패={fail} (기간 {label})')
    return {'ok': ok, 'fail': fail, 'period': label}

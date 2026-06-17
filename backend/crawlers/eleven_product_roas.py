"""11번가 adoffice 다운로드보고서(캠페인>상품>키워드 + 총전환) → 상품코드별 ROAS 수집.
순수 API 사용: 생성요청 → 목록 폴링(DOWNLOADABLE) → CSV 다운로드 → 상품번호 집계 → DB 저장."""
import csv as _csv
import io
import json
import logging
import re
import time

from django.utils import timezone

from .browser import DEFAULT_UA, _ensure_display, _kill_stale_chrome, _STEALTH_JS

logger = logging.getLogger('crawler')
ADOFFICE = 'https://adoffice.11st.co.kr'
API = 'https://apis.adoffice.11st.co.kr'

_GET = ("const done=arguments[arguments.length-1];"
        "fetch(arguments[0],{credentials:'include',headers:{'Accept':'*/*','sellerId':arguments[1]}})"
        ".then(r=>r.text()).then(t=>done(t)).catch(e=>done('ERR:'+e));")
_POST = ("const done=arguments[arguments.length-1];"
         "fetch(arguments[0],{method:'POST',credentials:'include',headers:{'Accept':'application/json','sellerId':arguments[1]}})"
         ".then(function(r){var s=r.status;return r.text().then(function(t){done('['+s+']'+t);});}).catch(function(e){done('ERR:'+e);});")
_DEL = ("const done=arguments[arguments.length-1];"
        "fetch(arguments[0],{method:'DELETE',credentials:'include',headers:{'Accept':'application/json','sellerId':arguments[1]}})"
        ".then(function(r){done('['+r.status+']');}).catch(function(e){done('ERR:'+e);});")


def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    _kill_stale_chrome(); time.sleep(1); _ensure_display()
    o = Options()
    for x in ('--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--window-size=1680,950',
              '--disable-extensions', '--ignore-certificate-errors',
              '--disable-blink-features=AutomationControlled', '--lang=ko-KR'):
        o.add_argument(x)
    o.add_argument(f'--user-agent={DEFAULT_UA}')
    o.add_experimental_option('excludeSwitches', ['enable-automation'])
    d = webdriver.Chrome(options=o)
    d.set_page_load_timeout(60); d.implicitly_wait(5)
    try:
        d.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': _STEALTH_JS})
    except Exception:
        pass
    return d


def _login(driver, login_id, pw):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    driver.get(ADOFFICE); time.sleep(3)
    if 'login' in driver.current_url.lower():
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, 'memId')))
        driver.find_element(By.ID, 'memId').send_keys(login_id)
        driver.find_element(By.ID, 'memPwd').send_keys(pw or '')
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, 'loginbutton'))
        WebDriverWait(driver, 25).until(lambda x: 'login' not in x.current_url.lower())
        time.sleep(3)
    m = re.search(r'/sellers/(\d+)/', driver.current_url)
    return m.group(1) if m else None


def _parse_int(v):
    try:
        return int(float(str(v).replace(',', '').strip() or 0))
    except Exception:
        return 0


def _aggregate_by_product(csv_text):
    """CSV(키워드 단위 행) → 상품번호별 집계 dict."""
    rdr = _csv.reader(io.StringIO(csv_text))
    rows = list(rdr)
    if not rows:
        return {}
    header = [h.strip() for h in rows[0]]
    idx = {name: i for i, name in enumerate(header)}
    ci_prod = idx.get('상품번호')
    ci_camp = idx.get('캠페인명')
    ci_imp = idx.get('노출수'); ci_clk = idx.get('클릭수')
    ci_cost = idx.get('총비용'); ci_conv = idx.get('총전환수'); ci_amt = idx.get('총전환금액')
    if ci_prod is None or ci_cost is None:
        return {}
    agg = {}
    for r in rows[1:]:
        if len(r) <= ci_prod:
            continue
        pno = (r[ci_prod] or '').strip()
        if not pno:
            continue
        a = agg.setdefault(pno, {'campaign': '', 'imp': 0, 'clk': 0, 'cost': 0, 'conv': 0, 'amt': 0, 'kw': 0})
        if not a['campaign'] and ci_camp is not None and len(r) > ci_camp:
            a['campaign'] = (r[ci_camp] or '')[:255]
        a['imp'] += _parse_int(r[ci_imp]) if ci_imp is not None else 0
        a['clk'] += _parse_int(r[ci_clk]) if ci_clk is not None else 0
        a['cost'] += _parse_int(r[ci_cost])
        a['conv'] += _parse_int(r[ci_conv]) if ci_conv is not None else 0
        a['amt'] += _parse_int(r[ci_amt]) if ci_amt is not None else 0
        a['kw'] += 1
    return agg


def collect_account(driver, login_id, pw, daterange, period_label, log, gsheet=None):
    """단일 계정: 보고서 생성→다운로드→상품번호 집계→저장. (저장건수, 상품수) 반환.
    gsheet: 열린 스프레드시트 객체(있으면 받은 CSV를 계정별 워크시트에도 업로드)."""
    from apps.cpc.models import St11ProductRoas
    sn = _login(driver, login_id, pw)
    if not sn:
        raise Exception('adoffice 로그인 실패(sellerNo 미검출)')
    driver.set_script_timeout(120)
    files_url = f'{API}/advertiser/reports/v1/bulkdownload/files'
    # 생성 전 기존 보고서 모두 삭제 → 10개 제한 해소 + 다운로드 대상 모호성 제거
    try:
        old = json.loads(driver.execute_async_script(_GET, files_url, sn)).get('content') or []
        for c in old:
            driver.execute_async_script(_DEL, f"{files_url}/{c['id']}", sn)
        if old:
            log(f'[{login_id}] 기존 보고서 {len(old)}개 삭제')
    except Exception:
        pass
    log(f'[{login_id}] sellerNo={sn} 보고서 생성요청...')
    rname = f'auto_{login_id}_{daterange.replace(",", "_")}'
    gen = (f'{API}/advertiser/reports/v1/bulkdownload/files?dateRange={daterange}&dateInterval=monthly'
           f'&reportName={rname}&downloadReportType=FOCUS&reportScope=PRODUCT_KEYWORD'
           f'&metricTypes=BASIC,TOTAL_CONVERSION')
    res = driver.execute_async_script(_POST, gen, sn)
    if not res.startswith('[200'):
        raise Exception(f'생성요청 실패: {res[:80]}')
    try:
        new_id = json.loads(res[res.index('{'):]).get('id')
    except Exception:
        new_id = None
    # 폴링: 방금 생성한 보고서가 DOWNLOADABLE 될 때까지
    files_url = f'{API}/advertiser/reports/v1/bulkdownload/files'
    target = None
    for i in range(20):
        time.sleep(12)
        try:
            obj = json.loads(driver.execute_async_script(_GET, files_url, sn))
        except Exception:
            continue
        items = obj.get('content') or []
        cand = [c for c in items if c.get('status') == 'DOWNLOADABLE'
                and (new_id is None or c.get('id') == new_id
                     or c.get('requestFileName') == rname)]
        if cand:
            target = cand[0]; break
        log(f'[{login_id}] 생성 대기 {(i+1)*12}s...')
    if not target:
        raise Exception('보고서 생성 타임아웃(DOWNLOADABLE 안 됨)')
    fid = target['id']
    log(f'[{login_id}] 다운로드 (id={fid})...')
    csv_text = driver.execute_async_script(_GET, f'{API}/advertiser/reports/v1/bulkdownload/files/{fid}', sn)
    if not csv_text or csv_text.startswith('ERR:'):
        raise Exception(f'다운로드 실패: {str(csv_text)[:80]}')
    agg = _aggregate_by_product(csv_text)
    # 저장 (해당 계정+기간 교체)
    now = timezone.now()
    St11ProductRoas.objects.filter(eleven_id=login_id, period=period_label).delete()
    objs = []
    for pno, a in agg.items():
        roas = round(a['amt'] / a['cost'] * 100, 2) if a['cost'] else 0
        objs.append(St11ProductRoas(
            eleven_id=login_id, product_no=pno, period=period_label,
            campaign_name=a['campaign'], impressions=a['imp'], clicks=a['clk'],
            cost=a['cost'], conversions=a['conv'], conv_amount=a['amt'],
            roas_pct=roas, keyword_count=a['kw'], collected_at=now))
    St11ProductRoas.objects.bulk_create(objs, batch_size=500)
    log(f'[{login_id}] 상품 {len(objs)}개 저장 (기간 {period_label})')
    # 구글시트 업로드는 여기서 안 함 — 시트엔 '기간별 보고서'(일자별 27컬럼)를
    # crawl_11st_period_gsheet 가 올림. 상품별 데이터를 시트에 올리면 형식이 안 맞음.
    return len(objs), len(agg)


def run_all_accounts(log_fn=None, account_filter=None, daterange=None, period_label=None, gsheet=False):
    from apps.cpc.models import CrawlerAccount

    def log(m):
        logger.info(m)
        if log_fn:
            log_fn(m)

    # (선택) 구글시트 업로드 — 계정 루프 전에 스프레드시트 1회 오픈(재인증 방지)
    sheet = None
    if gsheet:
        from . import gsheet_upload as _gs
        if _gs.is_configured():
            try:
                sheet = _gs.open_spreadsheet()
                log('구글시트 연결 OK — 계정별 보고서 업로드 활성화')
            except Exception as e:
                log(f'구글시트 연결 실패(업로드 생략): {str(e)[:120]}')
        else:
            log('구글시트 미설정(GSHEET_CREDENTIALS/GSHEET_11ST_KEY) — 업로드 생략')

    # 기본: 최근 한달(롤링) — adoffice는 '전일까지'만 제공하므로 어제 기준 최근 30일.
    if not daterange:
        from datetime import timedelta
        end = timezone.localdate() - timedelta(days=1)      # 어제
        start = end - timedelta(days=29)                    # 30일치
        daterange = f'{start:%Y%m%d},{end:%Y%m%d}'
        period_label = '최근한달'                            # 누적관리용 고정 라벨(매 수집 시 교체)
    if not period_label:
        period_label = '최근한달'

    from apps.cpc.eleven_block_guard import exclude_perma_banned
    qs = exclude_perma_banned(CrawlerAccount.objects.filter(platform='11st', is_active=True))
    accounts = [a for a in qs if (not account_filter or a.login_id in account_filter)]
    log(f'상품 ROAS 수집 시작: {len(accounts)}계정, 기간 {period_label} ({daterange}) — 영구정지 제외')

    collected = failed = 0
    for idx, a in enumerate(accounts, 1):
        driver = None
        try:
            driver = _make_driver()   # 계정마다 새 세션 (세션 재사용으로 인한 데이터 혼선 방지)
            n, _ = collect_account(driver, a.login_id, a.password_enc, daterange, period_label, log, gsheet=sheet)
            collected += 1
        except Exception as e:
            failed += 1
            log(f'[{a.login_id}] 수집 실패: {str(e)[:120]}')
        finally:
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass
        time.sleep(2)
    log(f'상품 ROAS 수집 완료: 성공={collected} 실패={failed}')
    return {'collected': collected, 'failed': failed, 'period': period_label}

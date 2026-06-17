"""11번가 adoffice 일별 상품코드별 광고지표 수집 (순수 API).
(계정,상품,날짜) 단위 누적 — 70일 제한은 청크 분할로 우회. 중복 없음(범위 교체 저장)."""
import csv as _csv
import io
import json
import logging
import time
from datetime import date, datetime, timedelta

from django.utils import timezone

from .eleven_product_roas import (_make_driver, _login, _GET, _POST, _DEL, _parse_int, API)

logger = logging.getLogger('crawler')


def _chunks(d0: date, d1: date, max_days=69):
    out = []
    s = d0
    while s <= d1:
        e = min(s + timedelta(days=max_days - 1), d1)
        out.append((s, e))
        s = e + timedelta(days=1)
    return out


def _parse_daily(csv_text, agg, kagg):
    """CSV(키워드×일자) → 상품(agg: (상품,날짜)) + 키워드(kagg: (상품,키워드,날짜)) 동시 집계."""
    rdr = _csv.reader(io.StringIO(csv_text))
    rows = list(rdr)
    if not rows:
        return
    h = [c.strip() for c in rows[0]]
    idx = {n: i for i, n in enumerate(h)}
    ci_d = idx.get('일자'); ci_p = idx.get('상품번호'); ci_camp = idx.get('캠페인명')
    ci_kw = idx.get('키워드명')
    ci_imp = idx.get('노출수'); ci_clk = idx.get('클릭수')
    ci_cost = idx.get('총비용'); ci_conv = idx.get('총전환수'); ci_amt = idx.get('총전환금액')
    if ci_d is None or ci_p is None or ci_cost is None:
        return
    for r in rows[1:]:
        if len(r) <= ci_p:
            continue
        pno = (r[ci_p] or '').strip()
        dstr = (r[ci_d] or '').strip()
        if not pno or not dstr or len(dstr) != 8:
            continue
        camp = (r[ci_camp] or '')[:255] if ci_camp is not None and len(r) > ci_camp else ''
        imp = _parse_int(r[ci_imp]) if ci_imp is not None else 0
        clk = _parse_int(r[ci_clk]) if ci_clk is not None else 0
        cost = _parse_int(r[ci_cost])
        conv = _parse_int(r[ci_conv]) if ci_conv is not None else 0
        amt = _parse_int(r[ci_amt]) if ci_amt is not None else 0
        # 상품 단위
        a = agg.setdefault((pno, dstr), {'campaign': '', 'imp': 0, 'clk': 0, 'cost': 0, 'conv': 0, 'amt': 0})
        if not a['campaign']:
            a['campaign'] = camp
        a['imp'] += imp; a['clk'] += clk; a['cost'] += cost; a['conv'] += conv; a['amt'] += amt
        # 키워드 단위 (키워드명 있는 행만)
        kw = (r[ci_kw] or '').strip()[:255] if ci_kw is not None and len(r) > ci_kw else ''
        if kw:
            k = kagg.setdefault((pno, kw, dstr), {'campaign': '', 'imp': 0, 'clk': 0, 'cost': 0, 'conv': 0, 'amt': 0})
            if not k['campaign']:
                k['campaign'] = camp
            k['imp'] += imp; k['clk'] += clk; k['cost'] += cost; k['conv'] += conv; k['amt'] += amt


def _gen_and_download(driver, sn, d0s, d1s, log):
    """한 청크(일별) 생성→폴링→CSV 반환."""
    files = f'{API}/advertiser/reports/v1/bulkdownload/files'
    # 기존 보고서 삭제(10개 제한·모호성 제거)
    try:
        for c in (json.loads(driver.execute_async_script(_GET, files, sn)).get('content') or []):
            driver.execute_async_script(_DEL, f"{files}/{c['id']}", sn)
    except Exception:
        pass
    gen = (f'{files}?dateRange={d0s},{d1s}&dateInterval=daily&reportName=auto_{d0s}_{d1s}'
           f'&downloadReportType=FOCUS&reportScope=PRODUCT_KEYWORD&metricTypes=BASIC,TOTAL_CONVERSION')
    res = driver.execute_async_script(_POST, gen, sn)
    if not res.startswith('[200'):
        raise Exception(f'생성요청 실패: {res[:80]}')
    fid = None
    # 5초 간격 폴링. NODATA(데이터없음)/실패면 즉시 종료(헛기다림 방지), 생성중이면 대기.
    for i in range(96):   # 대형계정(수만 상품) 생성 지연 대비 (~8분)
        time.sleep(5)
        try:
            items = json.loads(driver.execute_async_script(_GET, files, sn)).get('content') or []
        except Exception:
            continue
        dl = [c for c in items if c.get('status') == 'DOWNLOADABLE']
        if dl:
            fid = dl[0]['id']; break
        statuses = {c.get('status') for c in items}
        # 데이터 없음/실패 상태만 남으면 즉시 종료 (이 기간 상품광고 데이터 없음 → 실패 아님)
        if statuses and statuses <= {'NODATA', 'NO_DATA', 'FAILED', 'ERROR', 'EXPIRED'}:
            return None
    if not fid:
        raise Exception('생성 타임아웃(대형계정 가능성)')
    csv_text = driver.execute_async_script(_GET, f'{files}/{fid}', sn)
    if not csv_text or csv_text.startswith('ERR'):
        raise Exception('다운로드 실패')
    return csv_text


def collect_account(driver, login_id, pw, d0: date, d1: date, log):
    from apps.cpc.models import St11ProductDaily, St11KeywordDaily
    sn = _login(driver, login_id, pw)
    if not sn:
        raise Exception('adoffice 로그인 실패')
    driver.set_script_timeout(180)
    agg = {}; kagg = {}
    nodata_chunks = 0
    for (cs, ce) in _chunks(d0, d1):
        log(f'[{login_id}] {cs}~{ce} 일별 수집...')
        csv_text = _gen_and_download(driver, sn, cs.strftime('%Y%m%d'), ce.strftime('%Y%m%d'), log)
        if csv_text is None:
            nodata_chunks += 1      # 이 청크는 데이터 없음(NODATA) — 건너뜀(실패 아님)
            continue
        _parse_daily(csv_text, agg, kagg)
    now = timezone.now()
    # 상품 단위 저장 (cost>0)
    pobjs = []
    for (pno, dstr), a in agg.items():
        if a['cost'] <= 0:
            continue
        pobjs.append(St11ProductDaily(
            eleven_id=login_id, product_no=pno,
            stat_date=datetime.strptime(dstr, '%Y%m%d').date(),
            campaign_name=a['campaign'], impressions=a['imp'], clicks=a['clk'],
            cost=a['cost'], conversions=a['conv'], conv_amount=a['amt'], collected_at=now))
    # 키워드 단위 저장 (cost>0)
    kobjs = []
    for (pno, kw, dstr), a in kagg.items():
        if a['cost'] <= 0:
            continue
        kobjs.append(St11KeywordDaily(
            eleven_id=login_id, product_no=pno, keyword=kw,
            stat_date=datetime.strptime(dstr, '%Y%m%d').date(),
            campaign_name=a['campaign'], impressions=a['imp'], clicks=a['clk'],
            cost=a['cost'], conversions=a['conv'], conv_amount=a['amt'], collected_at=now))
    # 범위 교체 저장 (중복 0)
    St11ProductDaily.objects.filter(eleven_id=login_id, stat_date__gte=d0, stat_date__lte=d1).delete()
    St11ProductDaily.objects.bulk_create(pobjs, batch_size=1000)
    St11KeywordDaily.objects.filter(eleven_id=login_id, stat_date__gte=d0, stat_date__lte=d1).delete()
    St11KeywordDaily.objects.bulk_create(kobjs, batch_size=1000)
    log(f'[{login_id}] 상품 {len(pobjs)}행 / 키워드 {len(kobjs)}행 저장 ({d0}~{d1})'
        + (f' / NODATA청크 {nodata_chunks}개' if nodata_chunks else ''))
    return len(pobjs)


def run_all_accounts(log_fn=None, account_filter=None, date_from=None, date_to=None, with_gsheet=False):
    from apps.cpc.models import CrawlerAccount

    def log(m):
        logger.info(m)
        if log_fn:
            log_fn(m)

    d1 = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else (timezone.localdate() - timedelta(days=1))
    d0 = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else date(d1.year, 1, 1)

    # 구글시트 통합: 같은 adoffice 세션(로그인 1회)에서 기간별 보고서까지 받아 시트 업로드
    sheet = None
    g_period = g_d0 = g_d1 = None
    _mk_driver = _make_driver   # 기본: 상품 API수집용 드라이버
    if with_gsheet:
        # 기간별 보고서는 브라우저 파일다운로드 방식 → 다운로드 설정된 드라이버 필요(상품 API수집도 정상)
        from .eleven_period_report import _period_for, _make_driver as _mk_dl
        _mk_driver = _mk_dl
        g_period, g_d0, g_d1, _glabel = _period_for(timezone.localdate())
        from . import gsheet_upload as _gs
        if _gs.is_configured():
            try:
                sheet = _gs.open_spreadsheet()
                log(f'구글시트 연결 OK · 기간 {g_period}({g_d0}~{g_d1})')
            except Exception as e:
                log(f'구글시트 연결 실패: {str(e)[:120]}')
        else:
            log('구글시트 미설정 — 업로드 생략')
    from apps.cpc.eleven_block_guard import exclude_perma_banned
    qs = exclude_perma_banned(CrawlerAccount.objects.filter(platform='11st', is_active=True))
    accounts = [a for a in qs if (not account_filter or a.login_id in account_filter)]
    log(f'일별 상품ROAS 수집: {len(accounts)}계정, {d0}~{d1} ({len(_chunks(d0, d1))}청크) — 영구정지 제외')

    try:
        from apps.cpc.eleven_block_guard import is_blocked, preflight, release_global_lock
    except Exception:
        def is_blocked():
            return False, 0, None
        def preflight(name):
            return True, 'ok'
        def release_global_lock():
            pass

    # 사전점검: 차단/접속불가/다른크롤 동시실행이면 시작 안 함 (IP 차단 방지)
    ok, reason = preflight('상품ROAS')
    if not ok:
        log(f'⏭️ 상품ROAS 수집 건너뜀 — {reason}')
        return {'collected': 0, 'failed': 0, 'skipped': reason}

    def _wait_if_blocked():
        # 11번가 글로벌 차단 중이면 해제까지 대기 (사람처럼 페이싱 · 추가 차단 방지)
        while True:
            blocked, remain, until = is_blocked()
            if not blocked:
                return
            log(f'⛔ 11번가 차단 중 — {remain}s 대기 ({until:%H:%M:%S} 해제)')
            time.sleep(min(remain + 10, 300))

    collected = failed = 0
    fail_list = []
    ATTEMPTS = 3   # 생성 타임아웃·로그인 일시실패는 재시도로 자동 회복
    try:
        for a in accounts:
            _wait_if_blocked()
            ok = False
            for attempt in range(1, ATTEMPTS + 1):
                driver = None
                try:
                    driver = _mk_driver()
                    collect_account(driver, a.login_id, a.password_enc, d0, d1, log)
                    # 같은 세션에서 기간별 보고서+구글시트 (로그인 1회 공유). 당월 광고비 있는 계정만 업로드.
                    if with_gsheet and sheet is not None:
                        try:
                            from apps.cpc.models import St11ProductDaily
                            from django.db.models import Sum
                            mc = St11ProductDaily.objects.filter(
                                eleven_id=a.login_id, stat_date__gte=g_d0, stat_date__lte=g_d1
                            ).aggregate(c=Sum('cost'))['c'] or 0
                            if mc > 0:
                                from .eleven_period_report import collect_period_for_account
                                collect_period_for_account(driver, a.login_id, a.password_enc,
                                                           g_period, g_d0, g_d1, sheet, log)
                        except Exception as ge:
                            log(f'[{a.login_id}] 구글시트 실패(상품수집은 성공): {str(ge)[:120]}')
                    ok = True
                    break
                except Exception as e:
                    log(f'[{a.login_id}] 수집 실패(시도 {attempt}/{ATTEMPTS}): {str(e)[:120]}')
                    time.sleep(5)
                finally:
                    try:
                        if driver:
                            driver.quit()
                    except Exception:
                        pass
            if ok:
                collected += 1
            else:
                failed += 1
                fail_list.append(a.login_id)
            time.sleep(2)
    finally:
        release_global_lock()   # 전역 락 해제(동시 크롤 금지 유지)
    log(f'일별 상품ROAS 수집 완료: 성공={collected} 실패={failed}' + (f' / 실패계정={fail_list}' if fail_list else ''))
    return {'collected': collected, 'failed': failed, 'failed_accounts': fail_list, 'from': str(d0), 'to': str(d1)}

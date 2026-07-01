"""지마켓 상품별 광고비(CPC + AI매출업) 리포트 크롤 → GmarketProductAdCost 저장.

흐름(라이브 검증 2026-06-12, rejoice666):
  1. ad.esmplus.com 로그인(gmarket_crawler 쿠키/풀로그인 재사용)
  2. CPC: cpc/report/groupReport → 상품별 탭 → calendar '이번달' → 조회 → ExcelDown('Good')
     AI : Remarketing/Report/GroupReport → 상품별 탭(#reportsTab2) → calendar → 조회 → ExcelDown('goods')
  3. 다운로드 엑셀 파싱 → (login_id, ad_type, year, month) 범위 삭제 후 bulk_create (멱등·중복방지)
안전: eleven_block_guard 통합 락(preflight, platform='gmarket'). 동시 크롤 금지.
현재 '이번달(TM)' 프리셋 사용(당월 1일~오늘). 과거월은 추후 직접입력 지원.
"""
import os, glob, re, time, logging
from datetime import date
from django.utils import timezone

logger = logging.getLogger('crawler')
DL = '/tmp/avengers_adreport_dl'

REPORTS = {
    'cpc': {
        'url': 'https://ad.esmplus.com/cpc/report/groupReport',
        'tab': ('js', "SelTab.SetReportListTab('I');"),
        'search': "ReportList.GetTotalSearch();",
        'down': "ReportList.ExcelDown('Good');",
    },
    'ai': {
        'url': 'https://ad.esmplus.com/Remarketing/Report/GroupReport',
        'tab': ('id', 'reportsTab2'),
        'search': "RemarketingReport.Display.SearchMain();",
        'down': "RemarketingReport.ExcelDown.ExcelDown('goods');",
    },
}


def _log(fn, m):
    logger.info(m)
    if fn:
        fn(m)


def _clear_dl():
    os.makedirs(DL, exist_ok=True)
    for f in glob.glob(DL + '/*'):
        try: os.remove(f)
        except Exception: pass


def _set_period_thismonth(driver):
    from selenium.webdriver.common.by import By
    for sel in ['#dvSearchControl i.icon_calendar', 'i.icon_calendar', '#displayDate']:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            driver.execute_script("arguments[0].click();", els[0]); break
    time.sleep(1.5)
    pre = driver.find_elements(By.CSS_SELECTOR, "a[data-type='TM']")   # 이번달
    if pre:
        driver.execute_script("arguments[0].click();", pre[0]); time.sleep(1)
    try:
        driver.execute_script("CalendarLayer.ApplyCalendarDate();")
    except Exception:
        btn = driver.find_elements(By.CSS_SELECTOR, "button.btn_apply")
        if btn:
            driver.execute_script("arguments[0].click();", btn[0])
    time.sleep(1.5)
    sd = driver.execute_script("var e=document.getElementById('searchSDT');return e?(e.innerText||e.textContent||''):'';")
    ed = driver.execute_script("var e=document.getElementById('searchEDT');return e?(e.innerText||e.textContent||''):'';")
    return (sd or '').strip()[:10], (ed or '').strip()[:10]


def _set_period_month(driver, year, month):
    """특정 (year, month)을 '직접 입력(M)'으로 설정. 과거 완료월용.
    메커니즘(라이브 검증 2026-06-12): 캘린더 아이콘→a[data-type=M]→CalendarLayer.SetDate(시작,종료)→ApplyCalendarDate.
    ApplyCalendarDate가 #displayDate(시작~종료)를 읽어 #searchSDT/#searchEDT(span)에 반영.
    제약: maxDate=-1D(어제까지) → 종료일은 어제로 클램프. minDate=-182D(PP셀러)/-732D(일반)."""
    import calendar
    from datetime import timedelta
    from selenium.webdriver.common.by import By
    yesterday = timezone.localdate() - timedelta(days=1)
    last_day = calendar.monthrange(year, month)[1]
    start = f'{year}-{month:02d}-01'
    end_d = date(year, month, last_day)
    if end_d > yesterday:        # 현재월 등 미래 종료일 방지(어제까지만 선택 가능)
        end_d = yesterday
    end = end_d.strftime('%Y-%m-%d')
    # 직접 연결: #displayDate(선택기간 원본) → ApplyCalendarDate가 ~로 잘라 #searchSDT/#searchEDT에 기록
    # → 조회는 searchSDT/searchEDT를 읽음. datepicker 날짜클릭 불필요(라이브 검증 2026-06-12).
    driver.execute_script(
        r"""
        var s=arguments[0], e=arguments[1];
        // 직접입력(최근) 모드 활성화(있으면)
        var m=document.querySelector("a[data-type='M']"); if(m){ try{m.click();}catch(_){} }
        var dd=document.getElementById('displayDate'); if(dd){ dd.value = s + ' ~ ' + e; }
        try{ if(window.CalendarLayer && CalendarLayer.ApplyCalendarDate) CalendarLayer.ApplyCalendarDate(); }catch(_){}
        // 보장: searchSDT/searchEDT 직접 기록
        var sd=document.getElementById('searchSDT'); if(sd) sd.innerHTML = s;
        var ed=document.getElementById('searchEDT'); if(ed) ed.innerHTML = e;
        """, start, end)
    time.sleep(1.0)
    sd = driver.execute_script("var e=document.getElementById('searchSDT');return e?(e.innerText||e.textContent||''):'';")
    ed = driver.execute_script("var e=document.getElementById('searchEDT');return e?(e.innerText||e.textContent||''):'';")
    return (sd or '').strip()[:10], (ed or '').strip()[:10]


def _wait_dl(timeout=35):
    for _ in range(timeout * 2):
        fs = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
        if fs:
            time.sleep(1); return sorted(fs, key=os.path.getmtime)[-1]
        time.sleep(0.5)
    return None


def _read_rows(path):
    if path.lower().endswith('.xls'):
        import xlrd
        sh = xlrd.open_workbook(path).sheet_by_index(0)
        return [[('' if v is None else str(v)) for v in sh.row_values(r)] for r in range(sh.nrows)]
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return [['' if c is None else str(c) for c in r] for r in wb.active.iter_rows(values_only=True)]


def _num(s):
    try:
        return int(re.sub(r'[^\d-]', '', str(s)) or 0)
    except Exception:
        return 0


def _dec(s):
    try:
        return float(re.sub(r'[^\d.\-]', '', str(s)) or 0)
    except Exception:
        return 0.0


def _hidx(hdr, *subs):
    for i, c in enumerate(hdr):
        for s in subs:
            if s in c:
                return i
    return None


def _parse(ad_type, rows, login_id, year, month, sdt, edt):
    """엑셀 rows → GmarketProductAdCost 인스턴스 리스트."""
    from apps.cpc.models import GmarketProductAdCost
    # 헤더 행 탐색
    h = 0
    for i, r in enumerate(rows[:8]):
        if '상품번호' in ' '.join(r):
            h = i; break
    hdr = rows[h]
    i_pno = _hidx(hdr, '상품번호')
    i_seller = _hidx(hdr, '판매자 ID', '판매자ID')
    i_group = _hidx(hdr, '그룹명')
    i_site = _hidx(hdr, '사이트')
    i_imp = _hidx(hdr, '노출수')
    i_clk = _hidx(hdr, '클릭수')
    i_acc = _hidx(hdr, '평균클릭비용')
    i_cost = _hidx(hdr, '총비용', '광고비')
    i_ord = _hidx(hdr, '광고상품기준-구매수', '구매수')
    i_amt = _hidx(hdr, '광고상품기준-구매금액', '구매금액')
    i_rate = _hidx(hdr, '전환율')
    i_roas = _hidx(hdr, '광고수익률')
    now = timezone.now()
    out = {}
    for r in rows[h + 1:]:
        if i_pno is None or i_pno >= len(r):
            continue
        pno = re.sub(r'\D', '', r[i_pno] or '')
        if not pno:
            continue
        def g(i): return r[i] if (i is not None and i < len(r)) else ''
        seller = (g(i_seller) or login_id).strip() if i_seller is not None else login_id
        # AI매출업 리포트의 판매자ID는 'G {id}'/'A {id}' 접두로 옴 → 순수 login_id로 정규화(서브 분리/조회용)
        seller = re.sub(r'^[GA]\s+', '', seller)
        obj = GmarketProductAdCost(
            login_id=login_id, seller_id=seller[:50], ad_type=ad_type, product_no=pno[:50],
            year=year, month=month,
            period_start=sdt or None, period_end=edt or None,
            group_name=(g(i_group) or '')[:255], site=(g(i_site) or '')[:10],
            impressions=_num(g(i_imp)), clicks=_num(g(i_clk)), avg_click_cost=_num(g(i_acc)),
            cost=_num(g(i_cost)), orders=_num(g(i_ord)), conv_amount=_num(g(i_amt)),
            conv_rate=_dec(g(i_rate)), roas=_dec(g(i_roas)), collected_at=now)
        # 같은 상품번호 중복행은 합산(혹시 다중행) — 유니크키 보호
        if pno in out:
            e = out[pno]
            e.clicks += obj.clicks; e.cost += obj.cost; e.impressions += obj.impressions
            e.orders += obj.orders; e.conv_amount += obj.conv_amount
        else:
            out[pno] = obj
    return list(out.values())


def _select_seller_on_page(driver, target_seller, log_fn=None):
    """ESM 광고센터 페이지의 셀러 드롭다운으로 계정 전환 시도. 성공하면 True."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select
    for sel_id in ['SellerId', 'sellerId']:
        els = driver.find_elements(By.ID, sel_id)
        if not els:
            continue
        try:
            sel = Select(els[0])
            opts = [o.get_attribute('value') for o in sel.options]
            if target_seller not in opts:
                _log(log_fn, f'  셀러 드롭다운에 {target_seller} 없음 (목록: {opts})')
                return False
            sel.select_by_value(target_seller)
            time.sleep(1)
            _log(log_fn, f'  셀러 전환 → {target_seller} (#SellerId)')
            return True
        except Exception as e:
            _log(log_fn, f'  셀러 전환 실패 (#{sel_id}): {str(e)[:80]}')
    return False


def crawl_account(driver, login_id, year, month, log_fn=None, sub_login_ids=None, seller_override=None):
    """한 계정의 CPC+AI 상품별 광고비 크롤 → 저장. 결과 dict 반환.
    sub_login_ids: 공유ESM 서브계정 login_id 집합 — Excel 행의 seller_id가 여기 해당하면 해당 login_id로 저장.
    seller_override: 마스터 세션에서 특정 셀러로 전환해 크롤 (rejoice235/236 등).
    현재월=이번달(TM) 프리셋, 과거월=직접입력(M)+SetDate."""
    from selenium.webdriver.common.by import By
    from apps.cpc.models import GmarketProductAdCost
    today = timezone.localdate()
    is_current = (year == today.year and month == today.month)
    sub_ids = set(sub_login_ids or [])
    save_login_id = seller_override or login_id  # 저장할 login_id (서브계정 override 시 서브 id)
    res = {}
    for ad_type, cfg in REPORTS.items():
        try:
            _clear_dl()
            driver.get(cfg['url']); time.sleep(6)
            # seller_override: 마스터 세션에서 서브계정으로 전환
            if seller_override:
                if not _select_seller_on_page(driver, seller_override, log_fn):
                    _log(log_fn, f'  [{seller_override}/{ad_type}] ⚠️ 셀러 드롭다운 미발견, 페이지 재로드 후 재시도')
                    driver.get(cfg['url']); time.sleep(6)
                    if not _select_seller_on_page(driver, seller_override, log_fn):
                        _log(log_fn, f'  [{seller_override}/{ad_type}] ❌ 셀러 전환 실패 — 스킵')
                        res[ad_type] = {'ok': False, 'error': 'seller_switch_failed'}
                        continue
            kind, val = cfg['tab']
            if kind == 'js':
                driver.execute_script(val)
            else:
                driver.execute_script("arguments[0].click();", driver.find_element(By.ID, val))
            time.sleep(3)
            sdt, edt = _set_period_thismonth(driver) if is_current else _set_period_month(driver, year, month)
            driver.execute_script(cfg['search']); time.sleep(8)
            _clear_dl()
            driver.execute_script(cfg['down'])
            f = _wait_dl(35)
            if not f or os.path.getsize(f) < 100:
                _log(log_fn, f'  [{login_id}/{ad_type}] ❌ 다운로드 실패({f})')
                res[ad_type] = {'ok': False, 'products': 0, 'cost': 0}
                continue
            rows = _read_rows(f)
            objs = _parse(ad_type, rows, save_login_id, year, month, sdt, edt)
            # 공유ESM: seller_id가 서브계정 login_id면 login_id 재매핑 (seller_override 없을 때만)
            if sub_ids and not seller_override:
                for o in objs:
                    if o.seller_id in sub_ids:
                        o.login_id = o.seller_id
            # 멱등 저장: 영향받는 모든 login_id별 (login_id, ad_type, year, month) 삭제 후 재삽입
            from django.db import transaction
            objs_by_lid = {}
            for o in objs:
                objs_by_lid.setdefault(o.login_id, []).append(o)
            with transaction.atomic():
                affected_lids = {save_login_id} | (sub_ids if sub_ids and not seller_override else set())
                for lid in affected_lids:
                    GmarketProductAdCost.objects.filter(login_id=lid, ad_type=ad_type, year=year, month=month).delete()
                for lid, lid_objs in objs_by_lid.items():
                    GmarketProductAdCost.objects.bulk_create(lid_objs, batch_size=500)
            tot = sum(o.cost for o in objs)
            by_lid = {lid: sum(o.cost for o in los) for lid, los in objs_by_lid.items()}
            detail = ', '.join(f'{lid}:{c:,}' for lid, c in sorted(by_lid.items()))
            _log(log_fn, f'  [{login_id}/{ad_type}] {sdt}~{edt} 상품 {len(objs)}개 / {detail} 저장')
            res[ad_type] = {'ok': True, 'products': len(objs), 'cost': tot, 'period': f'{sdt}~{edt}'}
        except Exception as e:
            _log(log_fn, f'  [{login_id}/{ad_type}] 오류 {str(e)[:120]}')
            res[ad_type] = {'ok': False, 'error': str(e)[:120]}
    return res


def run(login_ids=None, year=None, month=None, periods=None, log_fn=None, with_keywords=False,
        with_gsheet=False):
    """periods: [(year,month), ...] 여러 달 순회(한 로그인으로). 미지정시 (year,month) 또는 당월.
    각 계정 로그인 1회로 모든 달을 크롤(IP 부담 최소화). 멱등 저장이라 재실행 안전.
    with_keywords=True면 계정 광고비 수집 후 같은 세션에서 그 계정 ROAS≥200 상품의 CPC 키워드까지 수집(로그인 1회).
    with_gsheet=True면 같은 세션에서 '일자별' 리포트(CPC/AI)도 다운로드해 계정별 구글시트 업로드(1일=전월/그외=당월)."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display
    from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies

    # 일자별 구글시트 준비(스프레드시트 1회 오픈 — 공유/인증 실패 시 비활성화하고 계속)
    ss_cpc = ss_ai = None
    daily_gsheet = gtarget = None
    if with_gsheet:
        try:
            from crawlers.gmarket_daily_gsheet import (
                run_for_account as daily_gsheet, target_period as gtarget, CPC_KEY, AI_KEY)
            from crawlers import gsheet_upload
            ss_cpc = gsheet_upload.open_spreadsheet(CPC_KEY)
            ss_ai = gsheet_upload.open_spreadsheet(AI_KEY)
        except Exception as e:
            _log(log_fn, f'[일자별 gsheet] 초기화 실패 → 업로드 비활성화: {str(e)[:120]}')
            with_gsheet = False

    today = timezone.localdate()
    if not periods:
        periods = [(year or today.year, month or today.month)]
    # 미래월 제거 + 정렬(과거→현재)
    periods = sorted({(y, m) for (y, m) in periods if (y, m) <= (today.year, today.month)})
    ok, reason = guard.preflight('지마켓상품광고비', platform='gmarket', wait=True, wait_timeout=1800)
    if not ok:
        _log(log_fn, f'⏭️ 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    all_accts = list(CrawlerAccount.objects.filter(platform='gmarket', is_active=True).order_by('display_order', 'login_id'))
    # 공유ESM 서브계정 login_id 맵: master_login_id → [sub_login_id, ...]
    sub_map = {}
    for a in all_accts:
        if a.gmarket_origin_id and a.gmarket_origin_id != a.login_id:
            sub_map.setdefault(a.gmarket_origin_id, []).append(a.login_id)
    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    if login_ids:
        qs = qs.filter(login_id__in=login_ids)
    accts = list(qs.order_by('display_order', 'login_id'))
    # 공유ESM 서브계정 제외(대표 크롤 시 seller_id 기반으로 서브 데이터 자동 분리 저장)
    if not login_ids:
        accts = [a for a in accts if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]
        _log(log_fn, f'[대표계정 {len(accts)}개] 공유ESM 서브({list(sub_map.keys())}) 포함 크롤')
    summary = {}
    driver = None
    try:
        for a in accts:
            blocked, _, _ = guard.is_blocked(platform='gmarket')
            if blocked:
                _log(log_fn, '⛔ 차단 감지 — 중단'); break
            _log(log_fn, f'[{a.login_id}] {len(periods)}개월 상품별 광고비 크롤: '
                         + ', '.join(f'{y}-{m:02d}' for y, m in periods))
            try:
                driver = create_driver(download_dir=DL, kill_existing=True)
                try:
                    driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
                except Exception:
                    pass
                if not (_try_cookie_login(driver, a) or
                        (_full_login(driver, a.login_id, a.password_enc) and (_save_cookies(driver, a) or True))):
                    _log(log_fn, f'[{a.login_id}] 로그인 실패 — 건너뜀')
                    summary[a.login_id] = {'login': False}
                    continue
                acct_res = {}
                subs = sub_map.get(a.login_id)
                if subs:
                    _log(log_fn, f'  [{a.login_id}] 서브계정 포함 수집: {subs}')
                for (y, m) in periods:
                    if guard.is_blocked(platform='gmarket')[0]:
                        _log(log_fn, '⛔ 차단 감지 — 중단'); break
                    _log(log_fn, f'  ── {a.login_id} {y}-{m:02d} ──')
                    acct_res[f'{y}-{m:02d}'] = crawl_account(driver, a.login_id, y, m, log_fn, sub_login_ids=subs)
                    time.sleep(2)   # 사람처럼 페이싱
                # 통합: 같은 세션(로그인 재사용)에서 이 계정 ROAS≥200 상품 CPC 키워드 수집.
                # 광고비 저장 후 실행하므로 방금 수집한 당월 GmarketProductAdCost로 ROAS≥200 판정.
                if with_keywords:
                    try:
                        from apps.cpc.models import GmarketProductAdCost
                        from django.db.models import Sum as _Sum
                        from crawlers.gmarket_keyword_crawler import crawl_account_keywords
                        ky, km = today.year, today.month   # 키워드는 당월 기준
                        grp = (GmarketProductAdCost.objects.filter(login_id=a.login_id, year=ky, month=km, ad_type='cpc')
                               .values('product_no').annotate(c=_Sum('cost'), v=_Sum('conv_amount')).filter(c__gt=0))
                        pnos = [g['product_no'] for g in grp
                                if (g['v'] or 0) > 0 and (g['v'] * 100.0 / g['c']) >= 200]
                        if pnos:
                            _log(log_fn, f'  [{a.login_id}] 🔑 ROAS≥200 키워드 수집 대상 {len(pnos)}개')
                            acct_res['keywords'] = crawl_account_keywords(driver, a.login_id, pnos, ky, km, log_fn)
                        else:
                            _log(log_fn, f'  [{a.login_id}] ROAS≥200 상품 없음 — 키워드 스킵')
                    except Exception as e:
                        # 키워드 실패는 광고비 저장에 영향 없음(에러 격리)
                        _log(log_fn, f'  [{a.login_id}] 키워드 수집 오류(광고비는 저장됨): {str(e)[:120]}')
                # 같은 세션에서 '일자별' 리포트(CPC/AI) 다운로드 → 계정별 구글시트 업로드 (에러 격리)
                if with_gsheet and ss_cpc is not None:
                    try:
                        gy, gm = gtarget()
                        acct_res['daily_gsheet'] = daily_gsheet(
                            a.login_id, log_fn=log_fn, gsheet=True, year=gy, month=gm,
                            driver=driver, ss_cpc=ss_cpc, ss_ai=ss_ai)
                    except Exception as e:
                        _log(log_fn, f'  [{a.login_id}] 일자별 gsheet 오류(광고비는 저장됨): {str(e)[:120]}')
                # 마스터 세션에서 서브계정 셀러 전환 크롤 (rejoice235/236 등 마스터 Excel 미포함 서브)
                subs_need_switch = sub_map.get(a.login_id, [])
                from apps.cpc.models import GmarketProductAdCost as _G
                for sub_lid in subs_need_switch:
                    if login_ids and sub_lid not in login_ids:
                        continue
                    if any(_G.objects.filter(login_id=sub_lid, year=y, month=m).exists() for y, m in periods):
                        _log(log_fn, f'  [{sub_lid}] 마스터 Excel 포함 — 셀러전환 불필요')
                        continue
                    _log(log_fn, f'  [{sub_lid}] 마스터 세션 셀러 전환 크롤 시도')
                    sub_res = {}
                    for (y, m) in periods:
                        if guard.is_blocked(platform='gmarket')[0]:
                            break
                        sub_res[f'{y}-{m:02d}'] = crawl_account(
                            driver, a.login_id, y, m, log_fn, seller_override=sub_lid)
                        time.sleep(2)
                        # 셀러전환 후 저장된 sub_lid 상품이 마스터와 90%+ 겹치면 중복 → 삭제
                        master_pnos = set(_G.objects.filter(login_id=a.login_id, year=y, month=m)
                                          .values_list('product_no', flat=True))
                        sub_pnos = set(_G.objects.filter(login_id=sub_lid, year=y, month=m)
                                       .values_list('product_no', flat=True))
                        if sub_pnos and master_pnos:
                            overlap = len(sub_pnos & master_pnos) / len(sub_pnos)
                            if overlap >= 0.9:
                                deleted = _G.objects.filter(login_id=sub_lid, year=y, month=m).delete()[0]
                                _log(log_fn, f'  [{sub_lid}] 마스터와 {overlap:.0%} 겹침 → 중복 {deleted}건 삭제')
                                sub_res[f'{y}-{m:02d}'] = {'dup_deleted': deleted}
                    summary[sub_lid] = sub_res
                summary[a.login_id] = acct_res
            finally:
                if driver:
                    try: driver.quit()
                    except Exception: pass
                    driver = None
        # 마스터 세션 셀러전환도 실패한 서브계정 → 독립 로그인 최종 폴백
        from apps.cpc.models import GmarketProductAdCost as _G
        for master_lid, sub_lids in sub_map.items():
            for sub_lid in sub_lids:
                if login_ids and sub_lid not in login_ids:
                    continue
                if any(_G.objects.filter(login_id=sub_lid, year=y, month=m).exists() for y, m in periods):
                    continue  # 이미 수집됨
                sub_acct = next((a for a in all_accts if a.login_id == sub_lid), None)
                if not sub_acct:
                    continue
                if guard.is_blocked(platform='gmarket')[0]:
                    _log(log_fn, '⛔ 차단 감지 — 중단'); break
                _log(log_fn, f'[{sub_lid}] 독립 로그인 최종 폴백 시도')
                try:
                    driver = create_driver(download_dir=DL, kill_existing=True)
                    try:
                        driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
                    except Exception:
                        pass
                    if not (_try_cookie_login(driver, sub_acct) or
                            (_full_login(driver, sub_acct.login_id, sub_acct.password_enc) and (_save_cookies(driver, sub_acct) or True))):
                        _log(log_fn, f'[{sub_lid}] 독립 로그인 실패 — 건너뜀')
                        summary[sub_lid] = {'login': False}
                        continue
                    sub_res = {}
                    for (y, m) in periods:
                        if guard.is_blocked(platform='gmarket')[0]:
                            break
                        sub_res[f'{y}-{m:02d}'] = crawl_account(driver, sub_lid, y, m, log_fn)
                        time.sleep(2)
                        # 폴백 독립로그인도 마스터와 90%+ 겹치면 중복 삭제
                        sub_acct2 = next((aa for aa in all_accts if aa.login_id == sub_lid), None)
                        if sub_acct2 and sub_acct2.gmarket_origin_id and sub_acct2.gmarket_origin_id != sub_lid:
                            master_lid2 = sub_acct2.gmarket_origin_id
                            master_pnos2 = set(_G.objects.filter(login_id=master_lid2, year=y, month=m)
                                               .values_list('product_no', flat=True))
                            sub_pnos2 = set(_G.objects.filter(login_id=sub_lid, year=y, month=m)
                                            .values_list('product_no', flat=True))
                            if sub_pnos2 and master_pnos2:
                                overlap2 = len(sub_pnos2 & master_pnos2) / len(sub_pnos2)
                                if overlap2 >= 0.9:
                                    deleted2 = _G.objects.filter(login_id=sub_lid, year=y, month=m).delete()[0]
                                    _log(log_fn, f'  [{sub_lid}] 폴백: 마스터와 {overlap2:.0%} 겹침 → 중복 {deleted2}건 삭제')
                    summary[sub_lid] = sub_res
                except Exception as e:
                    _log(log_fn, f'[{sub_lid}] 독립 크롤 오류: {str(e)[:120]}')
                    summary[sub_lid] = {'error': str(e)[:120]}
                finally:
                    if driver:
                        try: driver.quit()
                        except Exception: pass
                        driver = None
    finally:
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass
    return summary

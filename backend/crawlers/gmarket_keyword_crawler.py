"""지마켓 CPC 광고 '키워드별 실적' 크롤 → GmarketKeywordReport 저장.

기법(사용자 검증 PyQt 코드 이식): 광고센터 cpc/report/groupReport의 '키워드' 탭에서
상품번호를 검색창(#searchText)에 입력→Enter→키워드 행(#spanKeywordSearchData) 파싱.
상품당 ~5초. 대상 상품번호는 호출부에서 지정(기본=CPC ROAS≥200% 상품).

흐름:
  1. ad.esmplus.com 로그인(gmarket_crawler 쿠키/풀로그인 재사용)
  2. cpc/report/groupReport → 키워드 탭(li[data-type='K']) → 기간(이번달/직접입력) → 판매자 '지마켓' 선택
  3. 대상 상품번호 순회: 검색 → 키워드 행 추출 → (login_id, product_no, year, month) 멱등 저장
안전: eleven_block_guard 통합 락(preflight, platform='gmarket'). 동시 크롤 금지. 사람처럼 페이싱.
"""
import re
import time
import logging

from django.utils import timezone

# 기간 설정은 상품광고비 크롤러 것을 재사용(동일 페이지)
from crawlers.gmarket_ad_report_crawler import _set_period_thismonth, _set_period_month, _num, _dec

logger = logging.getLogger('crawler')
REPORT_URL = 'https://ad.esmplus.com/cpc/report/groupReport'


def _log(fn, m):
    logger.info(m)
    if fn:
        fn(m)


def _select_keyword_tab(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    tab = WebDriverWait(driver, 12).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "li[data-type='K'] a")))
    driver.execute_script("arguments[0].click();", tab)
    time.sleep(1.5)


def _select_seller_gmarket(driver):
    """판매자 ID 셀렉터 열기 → '지마켓'(radio data-type='2') 선택 → 적용."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.select_text[data-select='slt-0']")))
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.8)
        label = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='radio'][@data-type='2']/parent::label")))
        driver.execute_script("arguments[0].click();", label)
        time.sleep(0.4)
        apply_btn = driver.find_element(By.CSS_SELECTOR, "button.btn_apply")
        driver.execute_script("arguments[0].click();", apply_btn)
        time.sleep(0.6)
        return True
    except Exception:
        return False


def _extract_keyword_rows(driver, product_no):
    """현재 검색 결과의 키워드 행 → dict 리스트. 결과 없으면 []."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        WebDriverWait(driver, 12).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#spanKeywordSearchData table tbody tr")))
    except Exception:
        return []
    rows = driver.find_elements(By.CSS_SELECTOR, "#spanKeywordSearchData table tbody tr")
    out = []
    for row in rows:
        tds = row.find_elements(By.CSS_SELECTOR, "td")
        # 실측 12칸: [0]키워드 [1]노출 [2]클릭 [3]클릭율 [4]영역명 [5]평균노출순위
        #            [6]평균클릭비용 [7]총비용 [8]구매수 [9]구매금액 [10]전환율 [11]광고수익률
        # '영역명' 유무에 견고하도록 왼쪽 4칸은 앞에서, 지표 7칸은 끝에서 매핑.
        if len(tds) < 11:
            continue
        try:
            kw_el = tds[0].find_elements(By.CSS_SELECTOR, "span.report_goods")
            keyword = (kw_el[0].text if kw_el else tds[0].text).strip()
        except Exception:
            keyword = tds[0].text.strip()
        if not keyword:
            continue
        def t(i):
            return tds[i].text.strip()
        out.append({
            'keyword': keyword[:255],
            'impressions': _num(t(1)), 'clicks': _num(t(2)), 'click_rate': _dec(t(3)),
            'avg_rank': _dec(t(-7)), 'avg_click_cost': _num(t(-6)), 'cost': _num(t(-5)),
            'orders': _num(t(-4)), 'conv_amount': _num(t(-3)),
            'conv_rate': _dec(t(-2)), 'roas': _dec(t(-1)),
        })
    return out


def _set_period_range(driver, start, end):
    """임의 날짜범위(YYYY-MM-DD ~ YYYY-MM-DD)를 캘린더에 설정. 연도-누적 버킷용.
    displayDate(직접입력) → ApplyCalendarDate → searchSDT/searchEDT 기록(조회가 읽음)."""
    driver.execute_script(
        r"""
        var s=arguments[0], e=arguments[1];
        var m=document.querySelector("a[data-type='M']"); if(m){ try{m.click();}catch(_){} }
        var dd=document.getElementById('displayDate'); if(dd){ dd.value = s + ' ~ ' + e; }
        try{ if(window.CalendarLayer && CalendarLayer.ApplyCalendarDate) CalendarLayer.ApplyCalendarDate(); }catch(_){}
        var sd=document.getElementById('searchSDT'); if(sd) sd.innerHTML = s;
        var ed=document.getElementById('searchEDT'); if(ed) ed.innerHTML = e;
        """, start, end)
    time.sleep(1.0)
    sd = driver.execute_script("var e=document.getElementById('searchSDT');return e?(e.innerText||e.textContent||''):'';")
    ed = driver.execute_script("var e=document.getElementById('searchEDT');return e?(e.innerText||e.textContent||''):'';")
    return (sd or '').strip()[:10], (ed or '').strip()[:10]


def crawl_account_keywords(driver, login_id, product_nos, year, month, log_fn=None, date_range=None, kw_roas_min=100):
    """한 계정의 대상 상품번호들 키워드 추출 → 멱등 저장. 결과 dict.
    date_range=(start,end) 주면 그 범위로 조회(연도버킷, month=0 저장권장). 없으면 year/month 월별.
    kw_roas_min: ROAS가 그 값 이상인 키워드만 저장(효율키워드 보관, 기본 100). 0이면 전부 저장."""
    from selenium.webdriver.common.by import By
    from django.db import transaction
    from apps.cpc.models import GmarketKeywordReport
    today = timezone.localdate()
    is_current = (year == today.year and month == today.month)

    driver.get(REPORT_URL)
    time.sleep(5)
    _select_keyword_tab(driver)
    if date_range:
        sdt, edt = _set_period_range(driver, date_range[0], date_range[1])
    else:
        sdt, edt = _set_period_thismonth(driver) if is_current else _set_period_month(driver, year, month)
    # 조회 갱신(기간 반영)
    try:
        driver.execute_script("ReportList.GetTotalSearch();")
        time.sleep(3)
    except Exception:
        pass
    # 판매자 '지마켓' 선택 제외 — 전체(지마켓+옥션) 판매자 기준으로 검색 (사용자 요청 2026-06-14)
    # _select_seller_gmarket(driver)

    from selenium.webdriver.common.keys import Keys
    search_input = driver.find_element(By.ID, "searchText")
    now = timezone.now()
    total_kw = 0
    done = 0
    failed = []        # 3회 재시도해도 실패한 상품
    saved_pnos = set() # 이번 호출에서 저장 성공한 상품(호출부가 pending 계산에 사용)
    driver_dead = False
    MAX_TRY = 3
    for pno in product_nos:
        pno = re.sub(r'\D', '', str(pno))
        if not pno:
            continue
        saved = False
        for attempt in range(MAX_TRY):
            try:
                search_input.clear()
                search_input.send_keys(pno)
                time.sleep(0.5)
                search_input.send_keys(Keys.RETURN)
                time.sleep(3.5)   # 표 AJAX 렌더 대기(재시도 누적 25 도달 → 3.0→3.5 복귀, 저녁 서버지연 stale 완화)
                kws = _extract_keyword_rows(driver, pno)
                # 수집 단계 필터: 효율(ROAS) kw_roas_min% 이상 키워드만 저장 (기본 100)
                if kw_roas_min and kw_roas_min > 0:
                    kws = [k for k in kws if (k.get('cost') or 0) > 0
                           and float(k.get('conv_amount') or 0) * 100.0 / float(k['cost']) >= kw_roas_min]
                objs = [GmarketKeywordReport(
                    login_id=login_id, seller_id='', product_no=pno[:50],
                    keyword=k['keyword'], year=year, month=month,
                    period_start=sdt or None, period_end=edt or None,
                    impressions=k['impressions'], clicks=k['clicks'], click_rate=k['click_rate'],
                    avg_rank=k['avg_rank'], avg_click_cost=k['avg_click_cost'], cost=k['cost'],
                    orders=k['orders'], conv_amount=k['conv_amount'], conv_rate=k['conv_rate'],
                    roas=k['roas'], collected_at=now) for k in kws]
                with transaction.atomic():
                    GmarketKeywordReport.objects.filter(
                        login_id=login_id, product_no=pno, year=year, month=month).delete()
                    if objs:
                        GmarketKeywordReport.objects.bulk_create(objs, batch_size=500)
                total_kw += len(objs)
                done += 1
                saved = True
                saved_pnos.add(pno)
                rt = f' (재시도{attempt})' if attempt else ''
                _log(log_fn, f'  [{login_id}] 상품 {pno}: 키워드 {len(objs)}개 저장{rt}')
                time.sleep(1.2)   # 사람처럼 페이싱
                break
            except Exception as e:
                emsg = str(e)
                # ① 죽은 드라이버(브라우저 크래시) 즉시 감지 → 묶음 중단(호출부가 새 브라우저로 재시도)
                low = emsg.lower()
                if any(m in low for m in ('httpconnectionpool', 'max retries', 'invalid session',
                                          'no such window', 'disconnected', 'not reachable',
                                          'session deleted', 'already closed', 'connection refused')):
                    driver_dead = True
                    _log(log_fn, f'  ⛑️ [{login_id}] 브라우저 죽음 감지({emsg[:40]}) — 묶음 중단, 새 브라우저로 이어서 재시도')
                    break
                _log(log_fn, f'  [{login_id}] 상품 {pno} 시도{attempt+1}/{MAX_TRY} 오류: {emsg[:60]}')
                time.sleep(2)
                # 검색창 재취득(stale 복구). 안 되면 페이지 복구.
                try:
                    search_input = driver.find_element(By.ID, "searchText")
                except Exception:
                    try:
                        driver.get(REPORT_URL); time.sleep(4)
                        _select_keyword_tab(driver)
                        if date_range:
                            _set_period_range(driver, date_range[0], date_range[1])
                        try:
                            driver.execute_script("ReportList.GetTotalSearch();"); time.sleep(3)
                        except Exception:
                            pass
                        search_input = driver.find_element(By.ID, "searchText")
                    except Exception as e2:
                        if any(m in str(e2).lower() for m in ('httpconnectionpool', 'max retries',
                                'invalid session', 'no such window', 'disconnected', 'not reachable')):
                            driver_dead = True
                        break
        if driver_dead:
            break   # 묶음 중단 — 미처리분은 호출부에서 새 브라우저로 재시도
        if not saved:
            failed.append(pno)
            _log(log_fn, f'  ❌ [{login_id}] 상품 {pno} 최종실패({MAX_TRY}회) — 누락')
    return {'products': done, 'keywords': total_kw, 'failed': failed,
            'saved': saved_pnos, 'driver_dead': driver_dead}


def run(targets, year=None, month=None, log_fn=None, date_range=None):
    """targets: {login_id: [product_no,...]}. year/month 미지정시 당월.
    date_range=(start,end) 주면 연도-누적 버킷(상품당 1회 범위조회, month는 버킷키=0 권장).
    각 계정 로그인 1회로 대상 상품 키워드 수집(멱등 저장이라 재실행 안전)."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver, stop_display
    from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies

    import os as _os
    # 2개조 동시 백필: 그룹B는 GMKT_KW_LOCK=gmarket_b 로 별도 락 사용(기본은 단일 'gmarket')
    lock_platform = _os.environ.get('GMKT_KW_LOCK', 'gmarket')

    today = timezone.localdate()
    year = year if year is not None else today.year
    month = month if month is not None else today.month   # month=0(연도버킷) 허용 — 'or' 쓰면 0이 falsy
    targets = {lid: pnos for lid, pnos in (targets or {}).items() if pnos}
    if not targets:
        _log(log_fn, '대상 상품 없음 — 종료')
        return {'ok': True, 'accounts': 0, 'keywords': 0}

    ok, reason = guard.preflight('지마켓키워드수집', platform=lock_platform)
    if not ok:
        _log(log_fn, f'⏭️ 건너뜀 — {reason}')
        return {'ok': False, 'skipped': reason}

    accts = {a.login_id: a for a in CrawlerAccount.objects.filter(
        platform='gmarket', login_id__in=list(targets.keys()))}
    summary = {}
    total_kw = 0
    driver = None
    try:
        CHUNK = 150     # 브라우저당 150개(크래시는 ~290개서 발생, 150 안전) → 재생성 오버헤드↓
        MAX_ROUNDS = 12 # 무한루프 방지 상한
        for lid, pnos in targets.items():
            a = accts.get(lid)
            if not a:
                _log(log_fn, f'[{lid}] 계정 없음 — 건너뜀'); continue
            if guard.is_blocked(platform=lock_platform)[0]:
                _log(log_fn, '⛔ 차단 감지 — 중단'); break
            _label = f'{date_range[0]}~{date_range[1]}' if date_range else f'{year}-{month:02d}'
            # 중복 제거(순서 유지)
            pending = list(dict.fromkeys(re.sub(r'\D', '', str(p)) for p in pnos if str(p).strip()))
            pending = [p for p in pending if p]
            _log(log_fn, f'[{lid}] {_label} 키워드 크롤 대상 {len(pending)}개')
            acc_done = acc_kw = 0
            login_failed = False
            no_progress = 0
            rounds = 0
            # ② 실패·미처리분을 새 브라우저로 라운드 재시도(무실패 수렴). 진전 없으면 2라운드 후 포기.
            while pending and no_progress < 2 and rounds < MAX_ROUNDS:
                rounds += 1
                if guard.is_blocked(platform=lock_platform)[0]:
                    _log(log_fn, '⛔ 차단 감지 — 중단'); break
                batch = pending[:CHUNK]
                before = len(pending)
                driver = None
                try:
                    driver = create_driver(kill_existing=True)
                    if not (_try_cookie_login(driver, a) or
                            (_full_login(driver, a.login_id, a.password_enc) and (_save_cookies(driver, a) or True))):
                        _log(log_fn, f'[{lid}] 로그인 실패 — 건너뜀')
                        login_failed = True
                        break
                    res = crawl_account_keywords(driver, lid, batch, year, month, log_fn, date_range=date_range)
                    acc_done += res.get('products', 0)
                    acc_kw += res.get('keywords', 0)
                    saved = res.get('saved', set())
                    pending = [p for p in pending if p not in saved]
                    if res.get('driver_dead'):
                        _log(log_fn, f'  [{lid}] 라운드{rounds}: 브라우저 죽음 → 남은 {len(pending)}개 새 브라우저로 재시도')
                except Exception as e:
                    _log(log_fn, f'  ⚠️ [{lid}] 라운드{rounds} 예외(새 브라우저 재시도): {str(e)[:70]}')
                finally:
                    if driver:
                        try: driver.quit()
                        except Exception: pass
                        driver = None
                no_progress = no_progress + 1 if len(pending) >= before else 0
            total_kw += acc_kw
            if login_failed:
                summary[lid] = {'login': False}
            else:
                summary[lid] = {'products': acc_done, 'keywords': acc_kw, 'failed': pending}
                if pending:
                    _log(log_fn, f'  ❌ [{lid}] 최종 미수집 {len(pending)}개({rounds}라운드): {",".join(pending[:50])}')
                else:
                    _log(log_fn, f'  ✅ [{lid}] {_label} 전량 수집완료(실패 0)')
    finally:
        guard.release_global_lock(platform=lock_platform)
        try: stop_display()
        except Exception: pass
    _log(log_fn, f'🔑 [지마켓 키워드수집 완료] 계정 {len(summary)} / 키워드 {total_kw}개')
    return {'ok': True, 'accounts': len(summary), 'keywords': total_kw, 'detail': summary}

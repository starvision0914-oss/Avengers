"""rejoice666 6월 상품별 광고비 크롤 (CPC + AI매출업) — 진단/검증용.
로그인→각 리포트 상품별→기간 2026-06-01~06-30 설정→조회→엑셀다운→파싱→집계+단계별 소요시간.
저장은 안 함(흐름검증·문제파악 먼저).
실행: /usr/bin/python3 crawlers/diag_rejoice666_june.py [login_id]"""
import os, sys, time, glob, re, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
from selenium.webdriver.common.by import By

DL = '/tmp/avengers_adreport_dl'
SDT, EDT = '2026-06-01', '2026-06-30'

REPORTS = {
    'cpc': {
        'url': 'https://ad.esmplus.com/cpc/report/groupReport',
        'tab_js': "SelTab.SetReportListTab('I');",
        'search_js': "ReportList.GetTotalSearch();",
        'down_js': "ReportList.ExcelDown('Good');",
    },
    'ai': {
        'url': 'https://ad.esmplus.com/Remarketing/Report/GroupReport',
        'tab_js': None,   # 탭 클릭은 #reportsTab2
        'search_js': "RemarketingReport.Display.SearchMain();",
        'down_js': "RemarketingReport.ExcelDown.ExcelDown('goods');",
    },
}


def log(m):
    print(m, flush=True)


def clear_dl():
    os.makedirs(DL, exist_ok=True)
    for f in glob.glob(DL + '/*'):
        try: os.remove(f)
        except Exception: pass


def set_period(driver, preset='TM'):
    """calendar 위젯으로 기간 설정. 이번달(TM)=당월. searchSDT/EDT 반환."""
    for sel in ['#dvSearchControl i.icon_calendar', 'i.icon_calendar', '#displayDate']:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            driver.execute_script("arguments[0].click();", els[0]); break
    time.sleep(1.5)
    pre = driver.find_elements(By.CSS_SELECTOR, f"a[data-type='{preset}']")
    if pre:
        driver.execute_script("arguments[0].click();", pre[0])
        time.sleep(1)
    try:
        driver.execute_script("CalendarLayer.ApplyCalendarDate();")
    except Exception:
        btn = driver.find_elements(By.CSS_SELECTOR, "button.btn_apply")
        if btn:
            driver.execute_script("arguments[0].click();", btn[0])
    time.sleep(1.5)
    sd = driver.execute_script("var e=document.getElementById('searchSDT');return e?(e.innerText||e.textContent||''):'';")
    ed = driver.execute_script("var e=document.getElementById('searchEDT');return e?(e.innerText||e.textContent||''):'';")
    return {'count': 2, 'info': f'{sd} ~ {ed}'}


def wait_download(timeout=25):
    for _ in range(timeout * 2):
        files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
        if files:
            time.sleep(1)
            return sorted(files, key=os.path.getmtime)[-1]
        time.sleep(0.5)
    return None


def parse_excel(path):
    ext = path.lower()
    rows = []
    if ext.endswith('.xls'):
        import xlrd
        sh = xlrd.open_workbook(path).sheet_by_index(0)
        for r in range(sh.nrows):
            rows.append([str(x) for x in sh.row_values(r)])
    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for r in wb.active.iter_rows(values_only=True):
            rows.append(['' if c is None else str(c) for c in r])
    return rows


def find_header(rows):
    for i, r in enumerate(rows[:8]):
        joined = ' '.join(r)
        if '상품번호' in joined and ('총비용' in joined or '광고비' in joined or '클릭' in joined):
            return i
    return 0


def summarize(name, rows):
    if not rows:
        log(f'   [{name}] 빈 결과'); return
    h = find_header(rows)
    hdr = rows[h]
    log(f'   [{name}] 헤더(행{h}): {hdr}')
    ci = {c: i for i, c in enumerate(hdr)}
    def col(*names):
        for n in names:
            for c, i in ci.items():
                if n in c:
                    return i
        return None
    i_pno = col('상품번호'); i_cost = col('총비용', '광고비'); i_clk = col('클릭수')
    i_amt = col('구매금액'); i_roas = col('광고수익률')
    data = rows[h + 1:]
    log(f'   [{name}] 데이터행 {len(data)}개')
    tot_cost = 0; n = 0; top = []
    for r in data:
        if i_pno is None or i_pno >= len(r) or not re.search(r'\d', r[i_pno] or ''):
            continue
        cost = int(re.sub(r'[^\d-]', '', r[i_cost]) or 0) if i_cost is not None and i_cost < len(r) else 0
        tot_cost += cost; n += 1
        top.append((r[i_pno], cost,
                    r[i_clk] if i_clk is not None and i_clk < len(r) else '',
                    r[i_amt] if i_amt is not None and i_amt < len(r) else ''))
    log(f'   [{name}] 상품 {n}개 / 총광고비 {tot_cost:,}원')
    for pno, cost, clk, amt in sorted(top, key=lambda x: -x[1])[:10]:
        log(f'       상품 {pno:14} 광고비 {cost:>8,}  클릭 {clk:>5}  구매금액 {amt}')
    return {'products': n, 'total_cost': tot_cost}


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
    a = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
    if not a:
        log(f'계정 {eid} 없음'); return
    ok, reason = guard.preflight('rejoice666월간크롤', platform='gmarket')
    if not ok:
        log(f'⏭️ 건너뜀 — {reason}'); return

    T0 = time.time()
    timings = {}
    driver = None
    try:
        clear_dl()
        driver = create_driver(download_dir=DL, kill_existing=True)
        try:
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
        except Exception:
            pass
        t = time.time()
        if _try_cookie_login(driver, a):
            log(f'쿠키 로그인 OK {time.time()-t:.1f}s')
        elif _full_login(driver, a.login_id, a.password_enc):
            log(f'풀 로그인 OK {time.time()-t:.1f}s'); _save_cookies(driver, a)
        else:
            log('❌ 로그인 실패'); return
        timings['login'] = time.time() - t

        results = {}
        for name, cfg in REPORTS.items():
            log(f'\n========== {name.upper()} 리포트 ==========')
            ts = time.time()
            clear_dl()
            driver.get(cfg['url']); time.sleep(6)
            log(f'   접속 title="{(driver.title or "")[:30]}"')
            # 상품별 탭
            if cfg['tab_js']:
                try: driver.execute_script(cfg['tab_js'])
                except Exception as e: log(f'   탭 JS 오류 {e}')
            else:
                try:
                    driver.execute_script("arguments[0].click();", driver.find_element(By.ID, 'reportsTab2'))
                except Exception as e:
                    log(f'   reportsTab2 오류 {e}')
            time.sleep(3)
            # 기간 설정
            pf = set_period(driver)
            log(f'   날짜 input {pf["count"]}개: {pf["info"]}')
            time.sleep(1)
            # 조회
            t_s = time.time()
            try:
                driver.execute_script(cfg['search_js'])
            except Exception as e:
                log(f'   조회 JS 오류 {e}')
            time.sleep(8)
            timings[f'{name}_search'] = time.time() - t_s
            # 다운로드
            t_d = time.time()
            try:
                driver.execute_script(cfg['down_js'])
            except Exception as e:
                log(f'   다운로드 JS 오류 {e}')
            f = wait_download(30)
            timings[f'{name}_download'] = time.time() - t_d
            if not f:
                log('   ❌ 다운로드 파일 없음'); results[name] = None
                timings[f'{name}_total'] = time.time() - ts
                continue
            log(f'   다운로드: {os.path.basename(f)} ({os.path.getsize(f)} bytes)')
            rows = parse_excel(f)
            results[name] = summarize(name, rows)
            timings[f'{name}_total'] = time.time() - ts

        log('\n========== 소요시간 ==========')
        for k, v in timings.items():
            log(f'   {k:18} {v:6.1f}s')
        log(f'   {"전체":18} {time.time()-T0:6.1f}s')
        log(f'\n결과요약: {results}')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

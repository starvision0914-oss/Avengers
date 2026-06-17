"""AI매출업 상품별 — calendar 위젯으로 '이번달'(6월) 설정 → 조회 → 다운로드 → 파싱 검증.
calendar: i.icon_calendar 클릭 → a[data-type=TM](이번달) → CalendarLayer.ApplyCalendarDate().
실행: /usr/bin/python3 crawlers/diag_ai_period.py [login_id]"""
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


def log(m): print(m, flush=True)


def clear_dl():
    os.makedirs(DL, exist_ok=True)
    for f in glob.glob(DL + '/*'):
        try: os.remove(f)
        except Exception: pass


def open_cal_set_thismonth(driver, preset='TM'):
    """calendar 아이콘 클릭 → 프리셋(이번달=TM) 클릭 → 적용."""
    # 1) 아이콘 열기
    opened = False
    for sel in ['#dvSearchControl i.icon_calendar', 'i.icon_calendar', '#displayDate']:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            driver.execute_script("arguments[0].click();", els[0])
            opened = True
            log(f'   calendar 열기: {sel}')
            break
    time.sleep(1.5)
    # 2) 프리셋 클릭 (이번달 TM)
    pre = driver.find_elements(By.CSS_SELECTOR, f"a[data-type='{preset}']")
    if pre:
        driver.execute_script("arguments[0].click();", pre[0])
        log(f'   프리셋 클릭: data-type={preset} ("{(pre[0].text or "").strip()}")')
        time.sleep(1)
    else:
        log(f'   ⚠️ 프리셋 data-type={preset} 미발견')
    # 3) 적용
    try:
        driver.execute_script("CalendarLayer.ApplyCalendarDate();")
        log('   적용(ApplyCalendarDate) 호출')
    except Exception as e:
        btn = driver.find_elements(By.CSS_SELECTOR, "button.btn_apply")
        if btn:
            driver.execute_script("arguments[0].click();", btn[0]); log('   적용 버튼 클릭')
        else:
            log(f'   ⚠️ 적용 실패 {e}')
    time.sleep(1.5)
    # 4) 확인
    sd = driver.execute_script("return (document.getElementById('searchSDT')||{}).innerText||(document.getElementById('searchSDT')||{}).textContent||'';")
    ed = driver.execute_script("return (document.getElementById('searchEDT')||{}).innerText||(document.getElementById('searchEDT')||{}).textContent||'';")
    dd = driver.execute_script("return (document.getElementById('displayDate')||{}).value||'';")
    log(f'   설정된 기간: searchSDT={sd!r} searchEDT={ed!r} displayDate={dd!r}')
    return sd, ed


def wait_dl(timeout=30):
    for _ in range(timeout * 2):
        fs = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
        if fs:
            time.sleep(1); return sorted(fs, key=os.path.getmtime)[-1]
        time.sleep(0.5)
    return None


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
    a = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
    ok, reason = guard.preflight('AI기간테스트', platform='gmarket')
    if not ok:
        log(f'skip {reason}'); return
    driver = None; T0 = time.time()
    try:
        clear_dl()
        driver = create_driver(download_dir=DL, kill_existing=True)
        try: driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
        except Exception: pass
        t = time.time()
        if not (_try_cookie_login(driver, a) or (_full_login(driver, a.login_id, a.password_enc) and (_save_cookies(driver, a) or True))):
            log('로그인 실패'); return
        log(f'로그인 OK {time.time()-t:.1f}s')

        driver.get('https://ad.esmplus.com/Remarketing/Report/GroupReport'); time.sleep(6)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, 'reportsTab2'))
        time.sleep(3)
        log('상품별 탭 클릭')

        ts = time.time()
        open_cal_set_thismonth(driver, 'TM')   # 이번달 = 6월
        log(f'   기간설정 {time.time()-ts:.1f}s')

        t_s = time.time()
        driver.execute_script("RemarketingReport.Display.SearchMain();")
        time.sleep(8)
        log(f'   조회 {time.time()-t_s:.1f}s')

        clear_dl()
        t_d = time.time()
        driver.execute_script("RemarketingReport.ExcelDown.ExcelDown('goods');")
        f = wait_dl(30)
        log(f'   다운로드 {time.time()-t_d:.1f}s → {os.path.basename(f) if f else "❌없음"} ({os.path.getsize(f) if f else 0} bytes)')
        if f and os.path.getsize(f) > 100:
            import openpyxl
            try:
                wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
                rows = [['' if c is None else str(c) for c in r] for r in wb.active.iter_rows(values_only=True)]
                log(f'   파싱 OK: {len(rows)}행')
                if rows: log(f'   헤더: {rows[0]}')
                # 총 광고비
                hdr = rows[0] if rows else []
                ci = {c: i for i, c in enumerate(hdr)}
                cost_i = next((i for c, i in ci.items() if '총비용' in c or '광고비' in c), None)
                pno_i = next((i for c, i in ci.items() if '상품번호' in c), None)
                if cost_i is not None:
                    tot = sum(int(re.sub(r'[^\d-]', '', r[cost_i]) or 0) for r in rows[1:] if cost_i < len(r))
                    n = sum(1 for r in rows[1:] if pno_i is not None and pno_i < len(r) and re.search(r'\d', r[pno_i] or ''))
                    log(f'   ✅ AI 상품 {n}개 / 총광고비 {tot:,}원')
            except Exception as e:
                log(f'   파싱오류 {e}')
        log(f'\n전체 {time.time()-T0:.1f}s')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

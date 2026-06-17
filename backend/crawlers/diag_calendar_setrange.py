"""CalendarLayer.SetDateRange/SetDate/SetPeriod 함수 소스 덤프 + 과거월(2026-05) 설정 실제 테스트.
실행: /usr/bin/python3 crawlers/diag_calendar_setrange.py [login_id]"""
import os, sys, time, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
from selenium.webdriver.common.by import By


def log(m): print(m, flush=True)


def read_dates(driver):
    return driver.execute_script(r"""
        function t(id){var e=document.getElementById(id);return e?(e.innerText||e.textContent||e.value||'').trim():'(없음)';}
        return {sdt:t('searchSDT'), edt:t('searchEDT'), disp:t('displayDate')};
    """)


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
    a = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
    if not a:
        log(f'계정 {eid} 없음'); return
    ok, reason = guard.preflight('캘린더SetRange테스트', platform='gmarket')
    if not ok:
        log(f'⏭️ 건너뜀 — {reason}'); return
    driver = None
    try:
        driver = create_driver(kill_existing=True)
        if _try_cookie_login(driver, a):
            log('쿠키 로그인 OK')
        elif _full_login(driver, a.login_id, a.password_enc):
            log('풀 로그인 OK'); _save_cookies(driver, a)
        else:
            log('로그인 실패'); return

        driver.get('https://ad.esmplus.com/cpc/report/groupReport'); time.sleep(6)
        driver.execute_script("SelTab.SetReportListTab('I');"); time.sleep(3)

        # 함수 소스 덤프
        for fn in ('SetDateRange', 'SetDate', 'SetPeriod', 'SetManualBtnClicked', 'ApplyCalendarDate', 'SetSelectBoxDateRange'):
            src = driver.execute_script(
                "try{return CalendarLayer['%s'].toString().slice(0,400);}catch(e){return '(err '+e+')';}" % fn)
            log(f'\n### CalendarLayer.{fn} ###\n{src}')

        # 캘린더 열기
        driver.execute_script("var e=document.querySelector('#dvSearchControl i.icon_calendar')||document.querySelector('i.icon_calendar'); if(e)e.click();")
        time.sleep(1.2)
        log(f'\n[열기 후] {read_dates(driver)}')

        # 직접입력 모드
        driver.execute_script("var e=document.querySelector(\"a[data-type='M']\"); if(e)e.click();")
        time.sleep(1)

        # 시도 1: SetDateRange(문자열)
        for attempt, js in [
            ("SetDateRange('2026-05-01','2026-05-31')",
             "try{CalendarLayer.SetDateRange('2026-05-01','2026-05-31');return 'ok';}catch(e){return 'err '+e;}"),
            ("SetDateRange(Date,Date)",
             "try{CalendarLayer.SetDateRange(new Date(2026,4,1),new Date(2026,4,31));return 'ok';}catch(e){return 'err '+e;}"),
            ("SetDate then range",
             "try{CalendarLayer.SetDate&&CalendarLayer.SetDate('2026-05-01','2026-05-31');return 'ok';}catch(e){return 'err '+e;}"),
        ]:
            r = driver.execute_script(js)
            log(f'\n[{attempt}] → {r}  dates={read_dates(driver)}')

        # Apply 후 확인
        driver.execute_script("try{CalendarLayer.ApplyCalendarDate();}catch(e){}")
        time.sleep(1.5)
        log(f'\n[ApplyCalendarDate 후] {read_dates(driver)}')

        log('\n=== 테스트 완료 ===')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

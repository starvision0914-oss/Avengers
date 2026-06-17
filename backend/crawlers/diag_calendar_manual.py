"""GroupReport 캘린더 '직접입력(M)' 모드의 날짜 입력 메커니즘 캡처 — 읽기전용.
캘린더 아이콘 클릭 → a[data-type] 프리셋 목록 → '직접입력(M)' 클릭 후 입력필드/레이어 HTML 덤프.
실행: /usr/bin/python3 crawlers/diag_calendar_manual.py [login_id]"""
import os, sys, time, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
from selenium.webdriver.common.by import By


def log(m):
    print(m, flush=True)


def probe(driver, name, url, tabjs):
    log(f'\n========== {name.upper()} ==========')
    driver.get(url); time.sleep(6)
    if tabjs:
        try: driver.execute_script(tabjs)
        except Exception as e: log(f'탭 오류 {e}')
    else:
        try: driver.execute_script("arguments[0].click();", driver.find_element(By.ID, 'reportsTab2'))
        except Exception as e: log(f'reportsTab2 오류 {e}')
    time.sleep(3)

    # 1) 캘린더 아이콘 클릭
    clicked = driver.execute_script(r"""
        var sels=['#dvSearchControl i.icon_calendar','i.icon_calendar','#displayDate'];
        for(var i=0;i<sels.length;i++){var e=document.querySelector(sels[i]); if(e){e.click(); return sels[i];}}
        return '(아이콘 못찾음)';
    """)
    log(f'캘린더 아이콘 클릭: {clicked}')
    time.sleep(1.5)

    # 2) data-type 프리셋 전부
    presets = driver.execute_script(r"""
        return Array.prototype.slice.call(document.querySelectorAll('a[data-type]')).map(function(e){
            return {dt:e.getAttribute('data-type'), txt:(e.innerText||'').slice(0,12), vis:(e.offsetParent!==null)};
        });
    """)
    log(f'--- a[data-type] 프리셋 {len(presets)}개 ---')
    for p in presets:
        log(f'   data-type={p["dt"]!r} txt={p["txt"]!r} vis={p["vis"]}')

    # 3) 직접입력(M) 클릭
    mclick = driver.execute_script(r"""
        var e=document.querySelector("a[data-type='M']"); if(e){e.click(); return 'M클릭';}
        return '(M 없음)';
    """)
    log(f'직접입력(M): {mclick}')
    time.sleep(1.5)

    # 4) 클릭 후 보이는 input/select 전부
    inputs = driver.execute_script(r"""
        return Array.prototype.slice.call(document.querySelectorAll('input,select')).filter(function(e){
            return e.offsetParent!==null;
        }).map(function(e){
            return {tag:e.tagName, type:e.type||'', id:e.id||'', name:e.name||'',
                    cls:(e.className||'').slice(0,30), val:(e.value||'').slice(0,20),
                    ph:(e.placeholder||''), ro:e.readOnly||false, maxl:e.maxLength};
        });
    """)
    log(f'--- 직접입력 후 보이는 input/select {len(inputs)}개 ---')
    for d in inputs:
        log(f'   {d["tag"]}/{d["type"]} id={d["id"]!r} name={d["name"]!r} cls={d["cls"]!r} val={d["val"]!r} ph={d["ph"]!r} ro={d["ro"]} maxl={d["maxl"]}')

    # 5) searchSDT/searchEDT 의 정체
    for eid in ('searchSDT', 'searchEDT'):
        info = driver.execute_script("""
            var e=document.getElementById(arguments[0]); if(!e) return '(없음)';
            return e.tagName+' type='+(e.type||'')+' value='+(e.value||'')+' text='+((e.innerText||e.textContent||'').slice(0,20));
        """, eid)
        log(f'   #{eid}: {info}')

    # 6) 캘린더 레이어 HTML
    html = driver.execute_script(r"""
        var sels=['.calendar_layer','#calendarLayer','.ui_calendar','.layer_calendar','[class*=calendar]'];
        for(var i=0;i<sels.length;i++){var e=document.querySelector(sels[i]); if(e&&e.offsetParent!==null) return e.outerHTML.slice(0,1500);}
        return '(레이어 못찾음)';
    """)
    log(f'--- 캘린더 레이어 HTML ---\n{html}')

    # 7) Apply 함수 존재?
    fn = driver.execute_script("return typeof CalendarLayer!=='undefined' ? Object.keys(CalendarLayer).join(',') : '(CalendarLayer 없음)';")
    log(f'CalendarLayer keys: {fn}')


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
    a = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
    if not a:
        log(f'계정 {eid} 없음'); return
    ok, reason = guard.preflight('캘린더직접입력캡처', platform='gmarket')
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
        probe(driver, 'cpc', 'https://ad.esmplus.com/cpc/report/groupReport', "SelTab.SetReportListTab('I');")
        probe(driver, 'ai', 'https://ad.esmplus.com/Remarketing/Report/GroupReport', None)
        log('\n=== 캡처 완료 ===')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

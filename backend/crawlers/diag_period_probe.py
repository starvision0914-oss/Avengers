"""CPC/AI 리포트의 기간(날짜) 컨트롤 + AI 조회→다운로드 시퀀스 정밀 캡처 — 읽기전용.
모든 input(hidden 포함) id/name/value/readonly + 기간영역 HTML + 조회후 그리드 행수 덤프.
실행: /usr/bin/python3 crawlers/diag_period_probe.py [login_id]"""
import os, sys, time, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
from selenium.webdriver.common.by import By

PAGES = {
    'cpc': ('https://ad.esmplus.com/cpc/report/groupReport', "SelTab.SetReportListTab('I');"),
    'ai': ('https://ad.esmplus.com/Remarketing/Report/GroupReport', None),
}


def log(m):
    print(m, flush=True)


def dump_inputs(driver, label):
    data = driver.execute_script(r"""
        return Array.prototype.slice.call(document.querySelectorAll('input,select')).map(function(e){
            return {tag:e.tagName, type:e.type||'', id:e.id||'', name:e.name||'',
                    val:(e.value||'').slice(0,20), ro:e.readOnly||false,
                    vis:(e.offsetParent!==null)};
        });
    """)
    log(f'--- [{label}] input/select {len(data)}개 (날짜/기간 관련 + value 있는 것) ---')
    import re
    for d in data:
        blob = (d['id'] + d['name']).lower()
        dateish = re.search(r'\d{4}-?\d{2}-?\d{2}', d['val'] or '')
        if (any(k in blob for k in ('date', 'dt', 'start', 'end', 'from', 'to', 'period', 'cal', 'sdt', 'edt', 'term', 'day'))
                or dateish or d['tag'] == 'SELECT'):
            log(f'   {d["tag"]}/{d["type"]} id={d["id"]!r} name={d["name"]!r} val={d["val"]!r} ro={d["ro"]} vis={d["vis"]}')


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
    a = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
    if not a:
        log(f'계정 {eid} 없음'); return
    ok, reason = guard.preflight('기간컨트롤캡처', platform='gmarket')
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

        for name, (url, tabjs) in PAGES.items():
            log(f'\n========== {name.upper()} ==========')
            driver.get(url); time.sleep(6)
            if tabjs:
                try: driver.execute_script(tabjs)
                except Exception as e: log(f'탭 오류 {e}')
            else:
                try: driver.execute_script("arguments[0].click();", driver.find_element(By.ID, 'reportsTab2'))
                except Exception as e: log(f'reportsTab2 오류 {e}')
            time.sleep(3)
            dump_inputs(driver, name)
            # 기간 영역 HTML (기간/날짜 텍스트 포함 요소)
            html = driver.execute_script(r"""
                var els = Array.prototype.slice.call(document.querySelectorAll('div,fieldset,dl,ul,li,span,td'));
                for (var i=0;i<els.length;i++){
                    var t=els[i].innerText||'';
                    if(/기간|직접입력|오늘|7일|1개월|기간설정/.test(t) && t.length<300){
                        return els[i].outerHTML.slice(0,1200);
                    }
                }
                return '(기간영역 못찾음)';
            """)
            log(f'--- [{name}] 기간영역 HTML ---\n{html}')
            # 기간 preset 버튼/링크 텍스트
            btns = driver.execute_script(r"""
                return Array.prototype.slice.call(document.querySelectorAll('a,button,label')).filter(function(e){
                    return e.offsetParent!==null && /오늘|어제|7일|1주|1개월|30일|3개월|직접/.test(e.innerText||'');
                }).map(function(e){return {txt:(e.innerText||'').slice(0,10), id:e.id, onclick:(e.getAttribute('onclick')||'').slice(0,50)};});
            """)
            log(f'--- [{name}] 기간 프리셋 버튼 ---')
            for b in btns[:12]:
                log(f'   {b}')

        log('\n=== 캡처 완료 (읽기전용) ===')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

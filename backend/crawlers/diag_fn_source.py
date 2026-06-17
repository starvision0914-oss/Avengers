"""조회/다운로드 JS 함수 소스 + 폼 필드 덤프 — 기간 설정 방법 확정용. 읽기전용.
실행: /usr/bin/python3 crawlers/diag_fn_source.py [login_id]"""
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


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'rejoice666'
    a = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
    ok, reason = guard.preflight('JS소스캡처', platform='gmarket')
    if not ok:
        log(f'skip {reason}'); return
    driver = None
    try:
        driver = create_driver(kill_existing=True)
        if not (_try_cookie_login(driver, a) or (_full_login(driver, a.login_id, a.password_enc) and (_save_cookies(driver, a) or True))):
            log('로그인 실패'); return
        log('로그인 OK')

        # CPC
        driver.get('https://ad.esmplus.com/cpc/report/groupReport'); time.sleep(6)
        try: driver.execute_script("SelTab.SetReportListTab('I');")
        except Exception: pass
        time.sleep(2)
        srcs = driver.execute_script(r"""
            function src(f){ try{ return eval(f).toString().slice(0,900);}catch(e){return 'ERR:'+e;} }
            var out={};
            out.GetTotalSearch = src('ReportList.GetTotalSearch');
            out.ExcelDown = src('ReportList.ExcelDown');
            // displayDate 관련 hidden 필드 추정: 모든 input name=value 중 날짜숫자 포함
            out.dateFields = Array.prototype.slice.call(document.querySelectorAll('input')).filter(function(e){
                return /2026|20260|0601|0605|0611|Dt|Date|date/.test((e.name||'')+(e.value||''));
            }).slice(0,20).map(function(e){return e.name+'='+e.value;});
            // SetReportListTab 후 기간 관련 전역객체 탐색
            out.hasReportList = (typeof ReportList!=='undefined');
            return out;
        """)
        log('===== CPC GetTotalSearch =====\n' + str(srcs.get('GetTotalSearch')))
        log('===== CPC ExcelDown =====\n' + str(srcs.get('ExcelDown')))
        log('CPC dateFields: ' + str(srcs.get('dateFields')))

        # AI
        driver.get('https://ad.esmplus.com/Remarketing/Report/GroupReport'); time.sleep(6)
        try: driver.execute_script("arguments[0].click();", driver.find_element(By.ID, 'reportsTab2'))
        except Exception: pass
        time.sleep(2)
        srcs2 = driver.execute_script(r"""
            function src(f){ try{ return eval(f).toString().slice(0,900);}catch(e){return 'ERR:'+e;} }
            var out={};
            out.SearchMain = src('RemarketingReport.Display.SearchMain');
            out.ExcelDown = src('RemarketingReport.ExcelDown.ExcelDown');
            out.dateFields = Array.prototype.slice.call(document.querySelectorAll('input')).filter(function(e){
                return /2026|Dt|Date|date/.test((e.name||'')+(e.value||''));
            }).slice(0,20).map(function(e){return e.name+'='+e.value;});
            return out;
        """)
        log('===== AI SearchMain =====\n' + str(srcs2.get('SearchMain')))
        log('===== AI ExcelDown =====\n' + str(srcs2.get('ExcelDown')))
        log('AI dateFields: ' + str(srcs2.get('dateFields')))
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock(platform='gmarket')
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

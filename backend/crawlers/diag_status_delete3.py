"""상태기반 삭제 진단 v3 — 삭제/검색 JS 함수 실제 소스 + Ajax 엔드포인트 추출(읽기전용).
fnListDelete/searchSumData/prdNoCheck 소스를 떠서 직접 호출 가능한 삭제 엔드포인트를 찾는다.
삭제/판매중지 클릭 절대 없음. 실행: /usr/bin/python3 crawlers/diag_status_delete3.py [eid]"""
import os, sys, time, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.eleven_crawler import _do_login, _drain_alerts
from crawlers.browser import create_driver, stop_display
from crawlers.eleven_loss_delete import _focus_frame, PRODUCT_PAGE


def log(m):
    print(m, flush=True)


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'tmxkql22'
    ok, reason = guard.preflight('상태삭제진단3')
    if not ok:
        log(f'⏭️ 건너뜀 — {reason}'); return
    pw = {a.login_id: a.password_enc for a in CrawlerAccount.objects.filter(platform='11st')}.get(eid, '')
    driver = None
    try:
        driver = create_driver(kill_existing=False)
        t = time.time()
        sn = _do_login(driver, eid, pw)
        log(f'[{eid}] 로그인 {time.time()-t:.1f}s sn={sn}')
        if not sn:
            log('로그인 실패'); return
        driver.implicitly_wait(0)
        driver.set_page_load_timeout(30)
        _drain_alerts(driver, login_id=eid)
        driver.get(PRODUCT_PAGE)
        time.sleep(3)
        _focus_frame(driver)

        # 1) 주요 JS 함수 소스 덤프
        for fn in ['fnListDelete', 'searchSumData', 'prdNoCheck', 'chkSelStatCd3Change',
                   'doCommonStat', 'goNumCheck', 'fnListStop', 'fnStopSell']:
            src = driver.execute_script(
                f"try{{ return (typeof window.{fn}==='function')? window.{fn}.toString().slice(0,900):'(undef)'; }}"
                f"catch(e){{ return '(err)'+e; }}")
            log(f'\n===== {fn} =====\n{src}')

        # 2) jqxGrid 데이터소스 URL 추출
        ds = driver.execute_script(r"""
            try{
                var s=jQuery('#dvdataGrid').jqxGrid('source');
                var o={};
                if(s){ o.url=s.url||s._source&&s._source.url; o.type=s.type||(s._source&&s._source.type);
                        o.datafields=(s.datafields||(s._source&&s._source.datafields)||[]).slice(0,3); }
                return o;
            }catch(e){ return {err:(''+e).slice(0,120)}; }
        """)
        log(f'\n##### jqxGrid source: {ds}')

        # 3) 최근 Ajax 리소스 URL(상품조회/삭제 관련)
        res = driver.execute_script(r"""
            try{
                return (window.performance.getEntriesByType('resource')||[])
                  .map(function(e){return e.name;})
                  .filter(function(u){return /tmall|Action|product|Product|prd|list|List|search|Search/.test(u);})
                  .slice(-25);
            }catch(e){ return ['err'+e]; }
        """)
        log('\n##### Ajax 리소스 후보(최근):')
        for u in (res or []):
            log(f'   {u}')

        log('\n=== 진단3 완료 (삭제/판매중지 클릭 없음, 상품 변경 0) ===')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock()
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

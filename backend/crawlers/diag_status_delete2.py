"""상태기반 삭제 진단 v2 — 네이티브 클릭으로 상태필터 적용여부 확정 + 핸들러 덤프 + 판매금지 경로.
삭제/판매중지 클릭 절대 없음(읽기전용). 실행: /usr/bin/python3 crawlers/diag_status_delete2.py [eid]"""
import os, sys, time, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.eleven_crawler import _do_login, _drain_alerts
from crawlers.browser import create_driver, stop_display
from crawlers.eleven_loss_delete import _focus_frame, PRODUCT_PAGE
from selenium.webdriver.common.by import By


def log(m):
    print(m, flush=True)


def grid_state(driver):
    return driver.execute_script(r"""
        try{
            var $g=jQuery('#dvdataGrid');
            var di=$g.jqxGrid('getdatainformation')||{};
            var rows=$g.jqxGrid('getrows')||[];
            var stat={};
            rows.forEach(function(r){ var s=r.selStatCd||'?'; stat[s]=(stat[s]||0)+1; });
            return {rowscount:di.rowscount, got:rows.length, statusDist:stat};
        }catch(e){ return {err:(''+e).slice(0,100)}; }
    """)


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'tmxkql22'
    ok, reason = guard.preflight('상태삭제진단2')
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

        # 0) 핸들러 덤프 — 체크박스/검색버튼/검색함수
        dump = driver.execute_script(r"""
            function oc(id){var e=document.getElementById(id); return e?{onclick:(e.getAttribute('onclick')||''),
                outer:(e.outerHTML||'').slice(0,140)}:null;}
            var out={cb2:oc('chkSelStatCd2'), cb3:oc('chkSelStatCd3'), btn:oc('btnSearch')};
            // 체크박스의 label
            ['chkSelStatCd2','chkSelStatCd3'].forEach(function(id){
                var l=document.querySelector("label[for='"+id+"']");
                out[id+'_label']= l?{outer:l.outerHTML.slice(0,140), onclick:l.getAttribute('onclick')||''}:null;
            });
            // 검색 트리거 함수 후보 존재여부
            out.fns={searchList:typeof window.searchList, fnSearch:typeof window.fnSearch,
                     goSearch:typeof window.goSearch, searchSumData:typeof window.searchSumData,
                     getList:typeof window.getList, fnList:typeof window.fnList};
            return out;
        """)
        log(f'핸들러 덤프: cb품절={dump.get("cb2")}')
        log(f'  cb판매중지={dump.get("cb3")}')
        log(f'  검색버튼={dump.get("btn")}')
        log(f'  label품절={dump.get("chkSelStatCd2_label")}')
        log(f'  검색함수후보={dump.get("fns")}')

        # 1) 네이티브 클릭 테스트: 품절(chkSelStatCd2)만
        def native_filter(checkbox_id, label):
            # 모든 상태 체크 해제(JS) 후, 대상만 네이티브 클릭
            driver.execute_script(r"""
                ['chkSelStatCd1','chkSelStatCd2','chkSelStatCd3','chkSelStatCd4'].forEach(function(id){
                    var c=document.getElementById(id); if(c&&c.checked){ c.checked=false; }});
            """)
            clicked = False
            for sel in [(By.CSS_SELECTOR, f"label[for='{checkbox_id}']"), (By.ID, checkbox_id)]:
                try:
                    el = driver.find_element(*sel)
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    el.click()  # 네이티브 클릭
                    clicked = True
                    break
                except Exception as e:
                    log(f'   [{label}] {sel} 클릭실패 {str(e)[:50]}')
            chk = driver.execute_script(f"var c=document.getElementById('{checkbox_id}');return c?c.checked:null;")
            log(f'   [{label}] 클릭됨={clicked} checked={chk}')
            # 검색버튼 네이티브 클릭
            try:
                btn = driver.find_element(By.ID, 'btnSearch')
                btn.click()
            except Exception as e:
                log(f'   검색버튼 클릭실패 {str(e)[:50]}')
            time.sleep(3.5)
            log(f'   [{label}] 검색결과 → {grid_state(driver)}')

        log('--- 네이티브 클릭: 품절 단독 ---')
        native_filter('chkSelStatCd2', '품절')
        log('--- 네이티브 클릭: 판매중지 단독 ---')
        native_filter('chkSelStatCd3', '판매중지')

        # 2) 판매금지 경로 탐색 — 페이지 내 '판매금지'/'금지' 텍스트 요소
        ban = driver.execute_script(r"""
            var out=[];
            document.querySelectorAll('*').forEach(function(e){
                if(e.children.length===0){
                    var t=(e.textContent||'').trim();
                    if(t==='판매금지'||t==='판매제한'||t==='제재'){ out.push({tag:e.tagName,id:e.id,
                        cls:(e.className||'').toString().slice(0,40), txt:t}); }
                }
            });
            return out.slice(0,10);
        """)
        log(f'판매금지 관련 요소: {ban}')

        log('=== 진단2 완료 (삭제/판매중지 클릭 없음, 상품 변경 0) ===')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock()
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

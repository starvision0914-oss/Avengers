"""상태기반 삭제 진단 — 판매금지/품절/판매중지 상태필터로 검색 시 그리드 로드/선택 가능여부 확인.
삭제/판매중지 클릭 절대 없음(읽기전용). 상품번호 검색(고장) 대신 상태 체크박스 경로 검증.
실행: /usr/bin/python3 crawlers/diag_status_delete.py [eid]"""
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


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'tmxkql22'
    ok, reason = guard.preflight('상태삭제진단')
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
        log(f'페이지 title="{(driver.title or "")[:40]}"')

        # 1) 상태필터 체크박스 전수 덤프 (name/id/value/checked + 옆 라벨텍스트)
        log('--- 상태필터 체크박스 후보 ---')
        cbinfo = driver.execute_script(r"""
            var out=[];
            document.querySelectorAll("input[type=checkbox]").forEach(function(c){
                var id=c.id||'', nm=c.name||'';
                if(/stat|Stat|StatCd|sale|Sale/i.test(id+nm) || /chkSel/i.test(id+nm)){
                    var lbl='';
                    if(id){var l=document.querySelector("label[for='"+id+"']"); if(l) lbl=l.textContent.trim();}
                    if(!lbl && c.parentElement) lbl=(c.parentElement.textContent||'').trim().slice(0,20);
                    out.push({id:id,name:nm,value:c.value,checked:c.checked,label:lbl});
                }
            });
            return out;
        """)
        for c in cbinfo:
            log(f'   {c}')

        # 2) 상태별로 하나씩 단독 검색해 rowscount 측정 (어떤 체크박스가 무슨 상태인지 매핑)
        def search_with(checkbox_ids):
            r = driver.execute_script(r"""
                var ids=arguments[0];
                // 모든 상태 체크박스 해제
                document.querySelectorAll("input[type=checkbox]").forEach(function(c){
                    if(/chkSelStatCd/i.test(c.id||c.name||'')){ c.checked=false; }
                });
                // 대상만 체크
                ids.forEach(function(id){ var c=document.getElementById(id); if(c){ c.checked=true;
                    c.dispatchEvent(new Event('click',{bubbles:true})); } });
                var btn=document.getElementById('btnSearch'); if(btn) btn.click();
                return {clicked: !!btn};
            """, checkbox_ids)
            time.sleep(3.5)
            return driver.execute_script(r"""
                try{ var di=jQuery('#dvdataGrid').jqxGrid('getdatainformation')||{};
                     return {rowscount:di.rowscount}; }
                catch(e){ return {err:(''+e).slice(0,80)}; }
            """)

        statcd_ids = [c['id'] for c in cbinfo if 'chkSelStatCd' in (c.get('id') or '')]
        log(f'--- chkSelStatCd 단독검색 매핑 (ids={statcd_ids}) ---')
        for cid in statcd_ids:
            res = search_with([cid])
            log(f'   체크 {cid} 단독 → {res}')

        # 3) 판매금지/품절/판매중지 후보 동시 체크 검색 + 선택 테스트
        log('--- 3개 상태 동시검색 + 선택 테스트 ---')
        if statcd_ids:
            res = search_with(statcd_ids)  # 일단 전체 체크해 최대치 확인
            log(f'   전체 상태 체크 검색 → {res}')
            seltest = driver.execute_script(r"""
                var out={};
                try{ jQuery('#dvdataGrid').jqxGrid('selectallrows');
                     out.selected=(jQuery('#dvdataGrid').jqxGrid('getselectedrowindexes')||[]).length;
                     out.datarows=(jQuery('#dvdataGrid').jqxGrid('getdatainformation')||{}).rowscount;
                     // 보이는 상태/상품번호 샘플
                     var rows=jQuery('#dvdataGrid').jqxGrid('getrows')||[];
                     out.sample=rows.slice(0,5).map(function(r){
                        var o={}; Object.keys(r).forEach(function(k){ if(/stat|prdNo|prd|상태|번호/i.test(k)) o[k]=r[k]; });
                        return o; });
                     out.cols = rows.length? Object.keys(rows[0]).slice(0,20):[];
                }catch(e){ out.err=(''+e).slice(0,100); }
                return out;
            """)
            log(f'   selectallrows → {seltest}')

        log('=== 진단 완료 (삭제/판매중지 클릭 없음, 상품 변경 0) ===')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock()
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

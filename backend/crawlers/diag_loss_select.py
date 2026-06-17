"""적자삭제 select_all/검색 결함 DOM 진단 — 삭제/판매중지 클릭 절대 없음(읽기전용).
로그인→/view/8006→적자 상품번호 검색 후: 검색필터 적용여부(그리드 행수·표시 상품번호) +
체크박스 실태(전체선택/행별 checkbox 개수·checked 상태) + 전체선택 후보 요소를 덤프한다.
실행: /usr/bin/python3 crawlers/diag_loss_select.py [eid]"""
import os, sys, time, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from datetime import timedelta
from django.utils import timezone
from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from apps.cpc.views import _eleven_product_rows
from crawlers.eleven_crawler import _do_login, _drain_alerts
from crawlers.browser import create_driver, stop_display
from crawlers.eleven_loss_delete import (_focus_frame, _paste_and_search,
                                         _grid_rowcount, XP_PRDNO, XP_SELECTALL, PRODUCT_PAGE)
from selenium.webdriver.common.by import By


def log(m):
    print(m, flush=True)


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'rejoice345'
    d1 = timezone.localdate() - timedelta(days=1)
    d0 = d1.replace(day=1)
    rows = _eleven_product_rows(eid, d0, d1, None, 100, 2000, 10)
    import re
    nums = []
    for r in rows:
        d = re.sub(r'\D', '', str(r.get('product_no', '')))
        if d:
            nums.append(d)
    nums = sorted(set(nums))
    log(f'[{eid}] 적자 상품번호 {len(nums)}개: {nums}')
    if not nums:
        log('대상 없음 — 종료'); return

    ok, reason = guard.preflight('적자삭제진단')
    if not ok:
        log(f'⏭️ 건너뜀 — {reason}'); return

    pw = {a.login_id: a.password_enc for a in CrawlerAccount.objects.filter(platform='11st')}.get(eid, '')
    driver = None
    try:
        driver = create_driver(kill_existing=False)
        t = time.time()
        sn = _do_login(driver, eid, pw)
        log(f'  로그인 {time.time()-t:.1f}s sn={sn}')
        if not sn:
            log('로그인 실패'); return
        driver.implicitly_wait(0)
        driver.set_page_load_timeout(30)
        _drain_alerts(driver, login_id=eid)
        driver.get(PRODUCT_PAGE)
        time.sleep(3)
        log(f'페이지 title="{(driver.title or "")[:40]}"')

        # 검색 실행 (읽기전용 — 삭제/판매중지 클릭 없음)
        grid_rows = _paste_and_search(driver, nums, log, eid)
        log(f'=== 검색 후 _grid_rowcount={grid_rows} (검색 {len(nums)}건) ===')
        _focus_frame(driver)

        # 1) 그리드에 실제 표시된 상품번호 추출 — 검색필터 적용여부 판정
        shown = []
        for xp in ["//td//*[text()]", "//table//td"]:
            try:
                els = driver.find_elements(By.XPATH, xp)
                for e in els:
                    txt = (e.text or '').strip()
                    if re.fullmatch(r'\d{8,12}', txt):
                        shown.append(txt)
            except Exception:
                pass
            if shown:
                break
        shown = list(dict.fromkeys(shown))
        log(f'그리드 표시 상품번호({len(shown)}): {shown[:25]}')
        inter = set(shown) & set(nums)
        log(f'→ 검색대상과 교집합 {len(inter)}/{len(nums)} | 대상外 표시 {len(set(shown)-set(nums))}개  '
            f'(교집합<<대상 또는 대상外 많으면 = 검색필터 미적용)')

        # 2) 체크박스 실태
        cbs = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        vis = [c for c in cbs if c.is_displayed()]
        checked = [c for c in vis if c.is_selected()]
        log(f'체크박스 총 {len(cbs)} / 표시 {len(vis)} / 체크됨 {len(checked)}')
        for c in vis[:8]:
            log(f'   cb name={c.get_attribute("name")!r} id={c.get_attribute("id")!r} '
                f'class={c.get_attribute("class")!r} checked={c.is_selected()}')

        # 3) 전체선택 후보 요소
        sxp, sel = _find_safe(driver, XP_SELECTALL)
        log(f'전체선택(XP_SELECTALL) 매칭: {sxp or "미발견"}')
        if sel is not None:
            log(f'   outerHTML={driver.execute_script("return arguments[0].outerHTML;", sel)[:200]}')

        # 4) 검색 입력칸 / 검색버튼 실체
        from crawlers.eleven_loss_delete import _find, XP_SEARCH
        pxp, pel = _find(driver, XP_PRDNO, 5)
        log(f'prdNo 입력칸: {pxp}')
        if pel is not None:
            log(f'   {driver.execute_script("return arguments[0].outerHTML;", pel)[:160]}')
        bxp, bel = _find(driver, XP_SEARCH, 5)
        log(f'검색버튼: {bxp}')
        if bel is not None:
            log(f'   {driver.execute_script("return arguments[0].outerHTML;", bel)[:160]}')

        # 5) jqx 그리드 id + JS API 프로브 (jQuery/jqxGrid 가용성, 행수, 선택행)
        probe = driver.execute_script(r"""
            var out = {jq: (typeof window.jQuery!=='undefined'), grids: [], err: null};
            try {
                var nodes = document.querySelectorAll("[id*='jqxgrid'],[id*='Grid'],[id*='grid'],div.jqx-grid");
                var seen = {};
                nodes.forEach(function(n){
                    var id = n.id; if(!id || seen[id]) return; seen[id]=1;
                    var info = {id:id};
                    if(window.jQuery){ try{
                        var $g = jQuery('#'+id);
                        info.rows = $g.jqxGrid('getrows') ? $g.jqxGrid('getrows').length : null;
                        info.datarows = ($g.jqxGrid('getdatainformation')||{}).rowscount;
                        info.selected = ($g.jqxGrid('getselectedrowindexes')||[]).length;
                    }catch(e){ info.apiErr = (''+e).slice(0,80); } }
                    out.grids.push(info);
                });
            } catch(e){ out.err = (''+e).slice(0,120); }
            return out;
        """)
        log(f'jqx 프로브: jQuery={probe.get("jq")} err={probe.get("err")}')
        for g in probe.get('grids', [])[:6]:
            log(f'   grid id={g.get("id")!r} rows={g.get("rows")} datarows={g.get("datarows")} '
                f'selected={g.get("selected")} apiErr={g.get("apiErr")}')

        # 6) 검색 트리거 교정 테스트: textarea#prdNo 값 세팅 후 진짜 #btnSearch 클릭 → jqx 행수 확인
        log('--- 검색 교정 테스트 (read-only) ---')
        fix = driver.execute_script(r"""
            var nums = arguments[0];
            var ta = document.getElementById('prdNo');
            if(!ta) return {err:'no prdNo'};
            ta.value = nums.join('\n');
            ta.dispatchEvent(new Event('input',{bubbles:true}));
            ta.dispatchEvent(new Event('keyup',{bubbles:true}));
            var btn = document.getElementById('btnSearch');
            if(btn){ btn.click(); }
            return {set:ta.value.length, clicked: !!btn};
        """, nums)
        log(f'검색 트리거: {fix}')
        time.sleep(4)
        post = driver.execute_script(r"""
            try{
                var di = jQuery('#dvdataGrid').jqxGrid('getdatainformation')||{};
                return {rowscount: di.rowscount, sel: (jQuery('#dvdataGrid').jqxGrid('getselectedrowindexes')||[]).length};
            }catch(e){ return {err:(''+e).slice(0,100)}; }
        """)
        log(f'검색 후 dvdataGrid: {post}')

        # 7) 선택 API 테스트: jqx selectallrows / 체크박스컬럼 — 선택수 보고 (삭제 클릭 없음)
        seltest = driver.execute_script(r"""
            var out={};
            try{ jQuery('#dvdataGrid').jqxGrid('selectallrows');
                 out.afterSelectAll=(jQuery('#dvdataGrid').jqxGrid('getselectedrowindexes')||[]).length; }
            catch(e){ out.selErr=(''+e).slice(0,80); }
            return out;
        """)
        log(f'선택 테스트: {seltest}')

        # 8) 판매중지/삭제 버튼 onclick 핸들러 덤프 (어떤 선택을 읽는지 파악용)
        for name in ['판매중지', '선택상품삭제', '삭제']:
            try:
                els = driver.find_elements(By.XPATH, f"//a[contains(normalize-space(.),'{name}')]")
                for e in els[:1]:
                    log(f'버튼 "{name}" onclick={e.get_attribute("onclick")!r} href={e.get_attribute("href")!r}')
            except Exception as ex:
                log(f'버튼 "{name}" 조회오류 {ex}')

        log('=== 진단 완료 (삭제/판매중지 클릭 없음, 상품 변경 0) ===')
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        guard.release_global_lock()
        try:
            stop_display()
        except Exception:
            pass


def _find_safe(driver, xpaths):
    from crawlers.eleven_loss_delete import _find
    try:
        return _find(driver, xpaths, 5)
    except Exception:
        return None, None


if __name__ == '__main__':
    main()

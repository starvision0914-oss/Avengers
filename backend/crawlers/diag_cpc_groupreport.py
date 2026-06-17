"""CPC 상품별 리포트(ad.esmplus.com/cpc/report/groupReport) DOM 캡처 — 읽기전용.
상품별 탭(onclick SelTab.SetReportListTab('I')) 클릭 → 기간컨트롤/조회·다운로드 버튼 식별
→ 조회 후 그리드 헤더+샘플 덤프. 크롤러/모델 설계용. 다운로드/저장 안 함.
실행: /usr/bin/python3 crawlers/diag_cpc_groupreport.py [login_id]"""
import os, sys, time, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
from selenium.webdriver.common.by import By

REPORT_URL = 'https://ad.esmplus.com/cpc/report/groupReport'


def log(m):
    print(m, flush=True)


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'dlrmsgh012'
    a = CrawlerAccount.objects.filter(platform='gmarket', login_id=eid).first()
    if not a:
        log(f'계정 {eid} 없음'); return

    ok, reason = guard.preflight('CPC리포트캡처', platform='gmarket')
    if not ok:
        log(f'⏭️ 건너뜀 — {reason}'); return

    driver = None
    try:
        driver = create_driver(kill_existing=False)
        t = time.time()
        if _try_cookie_login(driver, a):
            log(f'쿠키 로그인 OK {time.time()-t:.1f}s')
        elif _full_login(driver, a.login_id, a.password_enc):
            log(f'풀 로그인 OK {time.time()-t:.1f}s')
            _save_cookies(driver, a)
        else:
            log('로그인 실패'); return

        driver.get(REPORT_URL)
        time.sleep(6)
        log(f'URL: {driver.current_url}  title="{(driver.title or "")[:40]}"')

        # 상품별 탭: onclick SelTab.SetReportListTab('I')
        clicked_tab = False
        for xp in ["//a[contains(@onclick,\"SetReportListTab('I')\")]",
                   "//a[.//strong[normalize-space()='상품별']]",
                   "//a[normalize-space()='상품별']"]:
            try:
                els = [e for e in driver.find_elements(By.XPATH, xp) if e.is_displayed()]
                if els:
                    driver.execute_script("arguments[0].click();", els[0])
                    log(f'상품별 탭 클릭: {xp}')
                    clicked_tab = True
                    break
            except Exception:
                pass
        if not clicked_tab:
            try:
                driver.execute_script("SelTab.SetReportListTab('I');")
                log('상품별 탭: JS SelTab.SetReportListTab(\'I\') 직접 호출')
            except Exception as e:
                log(f'⚠️ 상품별 탭 클릭 실패: {str(e)[:80]}')
        time.sleep(3)

        log('--- 날짜/기간 input ---')
        for inp in driver.find_elements(By.XPATH, "//input"):
            try:
                if not inp.is_displayed():
                    continue
                iid = inp.get_attribute('id') or ''
                nm = inp.get_attribute('name') or ''
                blob = (iid + nm).lower()
                if any(k in blob for k in ('date', 'dt', 'start', 'end', 'from', 'to', 'period', 'cal')):
                    log(f'   id={iid!r} name={nm!r} value={inp.get_attribute("value")!r} type={inp.get_attribute("type")!r}')
            except Exception:
                pass

        log('--- 버튼/링크(조회/검색/다운/엑셀) ---')
        for el in driver.find_elements(By.XPATH, "//button|//a|//input[@type='button']|//input[@type='submit']"):
            try:
                if not el.is_displayed():
                    continue
                txt = (el.text or el.get_attribute('value') or '').strip()
                if any(k in txt for k in ('조회', '검색', '다운', '엑셀', 'Excel', 'excel', 'download')):
                    log(f'   "{txt[:16]}" id={el.get_attribute("id")!r} onclick={(el.get_attribute("onclick") or "")[:70]!r} '
                        f'href={(el.get_attribute("href") or "")[:60]!r}')
            except Exception:
                pass

        # 조회 클릭(읽기전용)
        for xp in ["//button[contains(.,'조회')]", "//a[contains(.,'조회')]",
                   "//input[@value='조회']", "//*[@id='btnSearch']", "//button[contains(.,'검색')]"]:
            try:
                els = [e for e in driver.find_elements(By.XPATH, xp) if e.is_displayed()]
                if els:
                    driver.execute_script("arguments[0].click();", els[0])
                    log(f'조회 클릭: {xp}')
                    break
            except Exception:
                pass
        time.sleep(6)

        log('--- 그리드 헤더(th) ---')
        ths = [(_t.text or '').strip() for _t in driver.find_elements(By.XPATH, "//table//th") if (_t.text or '').strip()]
        log('   ' + ' | '.join(dict.fromkeys(ths))[:400] if ths else '   (th 없음 — jqx 가능성)')
        log('--- 첫 데이터행 샘플 ---')
        for r in driver.find_elements(By.XPATH, "//table//tbody/tr")[:3]:
            cells = [(c.text or '').strip() for c in r.find_elements(By.XPATH, "./td")]
            if any(cells):
                log('   ' + ' | '.join(cells)[:400])
        jqx = driver.execute_script(r"""
            try{ if(!window.jQuery) return {jq:false};
              var ids=[]; document.querySelectorAll("div.jqx-grid,[id*='grid'],[id*='Grid']").forEach(function(n){if(n.id)ids.push(n.id);});
              var out={jq:true, grids:[]};
              ids.slice(0,6).forEach(function(id){ try{
                 var di=jQuery('#'+id).jqxGrid('getdatainformation')||{};
                 out.grids.push({id:id, rows:di.rowscount});
              }catch(e){} });
              return out;
            }catch(e){return {err:(''+e).slice(0,80)};}
        """)
        log(f'jqx 프로브: {jqx}')
        log('=== 캡처 완료 (다운로드/저장 없음, 조회만) ===')
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        guard.release_global_lock(platform='gmarket')
        try:
            stop_display()
        except Exception:
            pass


if __name__ == '__main__':
    main()

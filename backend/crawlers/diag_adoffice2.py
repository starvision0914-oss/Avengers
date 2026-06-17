"""11번가 광고센터 — 캠페인 내부(광고그룹/소재) 깊이 탐색. 읽기전용(네비게이션만, OFF/삭제/저장 클릭 없음).
목적: 상품번호 단위로 광고 OFF가 가능한지 = 소재 목록에 상품번호 컬럼 + 행별 토글 + 검색창 존재 여부 확인.
실행: /usr/bin/python3 crawlers/diag_adoffice2.py [eid]"""
import os, sys, time, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()
from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.eleven_crawler import _do_login, _drain_alerts
from crawlers.browser import create_driver, stop_display
from selenium.webdriver.common.by import By

ADOFFICE = 'https://adoffice.11st.co.kr/'

def log(m): print(m, flush=True)

def dump(driver, tag):
    log(f'\n##### [{tag}] URL={driver.current_url[:80]}')
    d = driver.execute_script(r"""
      function txt(e){return (e.textContent||'').trim();}
      // 테이블 헤더(컬럼명)
      var heads=Array.from(document.querySelectorAll('table thead th, table thead td')).map(txt).filter(Boolean);
      // 첫 데이터행 셀들(상품번호 보이는지)
      var firstRow=[]; var tr=document.querySelector('table tbody tr');
      if(tr) firstRow=Array.from(tr.querySelectorAll('td')).map(txt).map(function(s){return s.slice(0,22);});
      // 검색 input들 (placeholder)
      var inputs=Array.from(document.querySelectorAll('input')).filter(function(i){return i.offsetParent!==null;})
        .map(function(i){return (i.placeholder||i.name||i.type||'').slice(0,20);}).filter(Boolean);
      // 보이는 버튼
      var btns=Array.from(document.querySelectorAll('button')).filter(function(b){return b.offsetParent!==null && txt(b);})
        .map(function(b){return txt(b).slice(0,16);});
      // 토글/스위치 류
      var toggles=document.querySelectorAll("[role=switch], .toggle, input[type=checkbox]").length;
      return {heads:heads, firstRow:firstRow, inputs:inputs.slice(0,12), btns:btns.slice(0,20),
              rows:document.querySelectorAll('table tbody tr').length, toggles:toggles,
              tabs:Array.from(document.querySelectorAll('[role=tab], .tab, nav span')).map(txt).filter(function(t){return t&&t.length<12;}).slice(0,15)};
    """)
    log(f"  컬럼(헤더): {d['heads']}")
    log(f"  첫행 셀: {d['firstRow']}")
    log(f"  검색input: {d['inputs']}")
    log(f"  탭/메뉴: {list(dict.fromkeys(d['tabs']))}")
    log(f"  버튼: {d['btns']}")
    log(f"  행수={d['rows']} 토글/체크={d['toggles']}")

def click_text(driver, label):
    els=[e for e in driver.find_elements(By.XPATH, f"//*[normalize-space(text())='{label}']") if e.is_displayed()]
    if els:
        driver.execute_script("arguments[0].click();", els[0]); return True
    return False

def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'tmxkql27'
    ok, reason = guard.preflight('adoffice진단2')
    if not ok: log(f'⏭️ 건너뜀 — {reason}'); return
    pw = {a.login_id: a.password_enc for a in CrawlerAccount.objects.filter(platform='11st')}.get(eid, '')
    driver=None
    try:
        driver=create_driver(kill_existing=False)
        t=time.time(); sn=_do_login(driver, eid, pw)
        log(f'[{eid}] 로그인 {time.time()-t:.1f}s sn={sn}')
        if not sn: log('로그인 실패'); return
        driver.implicitly_wait(0); driver.set_page_load_timeout(40)
        _drain_alerts(driver, login_id=eid)
        driver.get(ADOFFICE); time.sleep(6)
        # 광고관리 진입
        click_text(driver, '광고관리'); time.sleep(4)
        dump(driver, '캠페인 목록')
        # 캠페인 1개 클릭해서 내부 진입 (행의 첫 링크)
        try:
            link=driver.execute_script("""
              var tr=document.querySelector('table tbody tr');
              if(!tr) return null; var a=tr.querySelector('a'); if(a){a.click(); return a.textContent;} return null;""")
            log(f'\n>> 캠페인 클릭: {link}'); time.sleep(5)
            dump(driver, '캠페인 내부(광고그룹?)')
        except Exception as e: log(f'캠페인클릭 오류 {str(e)[:50]}')
        # 광고그룹 1개 더 들어가기
        try:
            link2=driver.execute_script("""
              var tr=document.querySelector('table tbody tr');
              if(!tr) return null; var a=tr.querySelector('a'); if(a){a.click(); return a.textContent;} return null;""")
            log(f'\n>> 광고그룹 클릭: {link2}'); time.sleep(5)
            dump(driver, '광고그룹 내부(소재/상품?)')
        except Exception as e: log(f'광고그룹클릭 오류 {str(e)[:50]}')
        # 소재/상품 탭 후보 클릭
        for lbl in ['소재','상품','광고','키워드']:
            if click_text(driver, lbl):
                log(f'\n>> "{lbl}" 탭 클릭'); time.sleep(3); dump(driver, f'{lbl} 탭')
        log('\n=== 깊이 탐색 완료 (변경 클릭 없음) ===')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock()
        try: stop_display()
        except Exception: pass

if __name__ == '__main__':
    main()

"""11번가 광고센터(adoffice) 셀렉터 유효성 진단 — 읽기전용.
사용자 GUI도구의 XPath가 지금도 유효한지 검증 + 버튼/메뉴를 텍스트로 덤프해 안정 셀렉터 후보 확보.
상태변경(선택ON/OFF·저장·입찰변경) 클릭 절대 없음. 네비게이션 클릭만.
실행: /usr/bin/python3 crawlers/diag_adoffice.py [eid]"""
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

# 사용자 도구가 쓰던 핵심 XPath들 (유효성 테스트 대상)
TOOL_XPATHS = {
    'nav_광고관리_1': '//*[@id="root"]/div/div[1]/div/nav/div[2]/div[2]/div[1]/div[1]/span',
    'nav_광고관리_2': '//*[@id="root"]/div/div[1]/div/nav/div[2]/div[2]/div[2]/div/div/div/div[1]/div[1]/div[1]/span',
    'bid_헤더체크박스': '//*[@id="root"]/div/div[2]/main/div[2]/div[3]/div[1]/div/table/thead/tr/th[1]/div/div[1]/div/span/input',
    'onoff_헤더체크박스': '//*[@id="root"]/div/div[2]/div[2]/div[4]/div[1]/div/table/thead/tr/th[1]/div/div[1]/div/span/input',
    'onoff_선택ON': '//*[@id="root"]/div/div[2]/div[2]/div[3]/div[1]/div[1]/button[1]',
    'onoff_선택OFF': '//*[@id="root"]/div/div[2]/div[2]/div[3]/div[1]/div[1]/button[2]',
}


def log(m):
    print(m, flush=True)


def dump_page(driver, tag):
    log(f'\n##### [{tag}] URL={driver.current_url[:70]} title="{(driver.title or "")[:40]}"')
    # 화면의 모든 버튼 텍스트
    btns = driver.execute_script(r"""
        return Array.from(document.querySelectorAll('button')).filter(function(b){
            return b.offsetParent!==null && (b.textContent||'').trim();
        }).map(function(b){return (b.textContent||'').trim().slice(0,18);}).slice(0,40);
    """)
    log(f'  보이는 버튼({len(btns)}): {btns}')
    # 좌측 nav 메뉴 텍스트
    nav = driver.execute_script(r"""
        var n=document.querySelector('nav'); if(!n) return [];
        return Array.from(n.querySelectorAll('span,a,div')).map(function(e){return (e.textContent||'').trim();})
            .filter(function(t){return t && t.length<14;}).slice(0,30);
    """)
    log(f'  nav 메뉴: {list(dict.fromkeys(nav))[:20]}')
    # 테이블/체크박스/행수
    info = driver.execute_script(r"""
        return {tables:document.querySelectorAll('table').length,
                checkboxes:document.querySelectorAll("input[type=checkbox]").length,
                rows:document.querySelectorAll('table tbody tr').length};
    """)
    log(f'  테이블={info["tables"]} 체크박스={info["checkboxes"]} 행={info["rows"]}')


def test_xpaths(driver, tag):
    log(f'  --- 도구 XPath 유효성 [{tag}] ---')
    for name, xp in TOOL_XPATHS.items():
        try:
            els = driver.find_elements(By.XPATH, xp)
            vis = any(e.is_displayed() for e in els) if els else False
            log(f'    {name}: {"✅존재" if els else "❌없음"}{" (보임)" if vis else ""} [{len(els)}개]')
        except Exception as e:
            log(f'    {name}: ⚠️오류 {str(e)[:40]}')


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else 'tmxkql22'
    ok, reason = guard.preflight('adoffice진단')
    if not ok:
        log(f'⏭️ 건너뜀 — {reason}'); return
    pw = {a.login_id: a.password_enc for a in CrawlerAccount.objects.filter(platform='11st')}.get(eid, '')
    driver = None
    try:
        driver = create_driver(kill_existing=False)
        t = time.time()
        sn = _do_login(driver, eid, pw)
        log(f'[{eid}] 셀러오피스 로그인 {time.time()-t:.1f}s sn={sn}')
        if not sn:
            log('로그인 실패'); return
        driver.implicitly_wait(0)
        driver.set_page_load_timeout(40)
        _drain_alerts(driver, login_id=eid)

        # 광고센터 진입 (SSO 유지되는지)
        driver.get(ADOFFICE)
        time.sleep(6)
        dump_page(driver, '광고센터 진입직후')
        test_xpaths(driver, '진입직후')

        # 광고관리로 네비게이션 시도 (텍스트 기반 — 상태변경 아님)
        for label in ['광고관리', '캠페인', '파워클릭', '광고 관리']:
            try:
                els = [e for e in driver.find_elements(By.XPATH, f"//*[normalize-space(text())='{label}']") if e.is_displayed()]
                if els:
                    driver.execute_script("arguments[0].click();", els[0])
                    log(f'\n>> "{label}" 메뉴 클릭(네비게이션)')
                    time.sleep(4)
                    dump_page(driver, f'{label} 클릭후')
                    test_xpaths(driver, f'{label} 후')
                    break
            except Exception as e:
                log(f'  "{label}" 클릭오류 {str(e)[:40]}')

        log('\n=== adoffice 진단 완료 (상태변경 클릭 없음) ===')
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock()
        try: stop_display()
        except Exception: pass


if __name__ == '__main__':
    main()

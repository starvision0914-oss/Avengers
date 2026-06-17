"""sellerNo 출처 탐색 프로브 — 쿠키/스토리지/XHR/소스 전수 덤프"""
import os, sys, time, re, json, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'jinag7461'


def log(m): print(m, flush=True)


def main():
    acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='11st')
    driver = create_driver(download_dir='/tmp/diag_dl')
    try:
        _ec._try_cookie_login(driver, acct)
        log(f'로그인 OK: {LOGIN_ID}')
        for page in ['https://soffice.11st.co.kr/view/main',
                     'https://soffice.11st.co.kr/pages/excel-download/']:
            log(f'\n##### {page} #####')
            driver.get(page); time.sleep(12)
            log(f'URL: {driver.current_url}')
            # 쿠키
            log('--- 쿠키 ---')
            for c in driver.get_cookies():
                v = str(c['value'])
                if re.search(r'\d{6,}', v) or re.search(r'sell|mem|no', c['name'], re.I):
                    log(f'  {c["name"]} = {v[:80]}')
            # 스토리지
            for store in ('localStorage', 'sessionStorage'):
                try:
                    data = driver.execute_script(
                        f"var o={{}};for(var i=0;i<{store}.length;i++){{var k={store}.key(i);"
                        f"o[k]={store}.getItem(k);}}return o;")
                    log(f'--- {store} ({len(data)}개) ---')
                    for k, v in (data or {}).items():
                        sv = str(v)
                        if re.search(r'\d{6,}', sv):
                            log(f'  {k} = {sv[:120]}')
                except Exception as e:
                    log(f'  {store} err {e}')
            # window 전역 (숫자 포함 객체)
            try:
                wk = driver.execute_script(
                    "var r={};for(var k in window){try{var v=window[k];"
                    "if(typeof v==='number'&&v>100000&&v<1e10)r[k]=v;"
                    "else if(typeof v==='string'&&/^\\d{6,10}$/.test(v))r[k]=v;}catch(e){}}return r;")
                log(f'--- window 숫자 전역 ({len(wk)}개) ---')
                for k, v in (wk or {}).items():
                    log(f'  window.{k} = {v}')
            except Exception as e:
                log(f'  win err {e}')
            # XHR 리소스 (api/bff 포함)
            try:
                urls = driver.execute_script(
                    "return performance.getEntriesByType('resource').map(e=>e.name)")
                api = [u for u in (urls or []) if re.search(r'/bff/|/api/|seller|Seller', u)]
                log(f'--- API XHR ({len(api)}개) ---')
                for u in api[:25]:
                    log(f'  {u[:140]}')
            except Exception as e:
                log(f'  xhr err {e}')
            # 소스에서 8자리 숫자 + 주변
            try:
                src = driver.page_source
                for m in re.finditer(r'.{12}(\d{8})\D', src):
                    log(f'  src8: ...{m.group(0)[:30]}')
                    break
            except Exception:
                pass
    finally:
        try: driver.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

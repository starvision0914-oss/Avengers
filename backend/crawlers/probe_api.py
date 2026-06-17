"""셀러오피스 API 프로브 — login-seller / product-list 응답 구조 확인 (in-page fetch)"""
import os, sys, time, json, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'jinag7461'
BASE = 'https://apis.11st.co.kr/product/bruce/selleroffice/v1'


def log(m): print(m, flush=True)


def fetch(driver, path):
    """페이지 컨텍스트에서 fetch (쿠키/인증 자동 포함)."""
    js = """
    const cb = arguments[arguments.length-1];
    fetch(arguments[0], {credentials:'include', headers:{'Accept':'application/json'}})
      .then(r=>r.text().then(t=>cb({status:r.status, body:t.slice(0,4000)})))
      .catch(e=>cb({status:-1, body:String(e)}));
    """
    try:
        return driver.execute_async_script(js, path)
    except Exception as e:
        return {'status': -2, 'body': str(e)}


def main():
    acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='11st')
    driver = create_driver(download_dir='/tmp/diag_dl')
    try:
        _ec._try_cookie_login(driver, acct)
        log(f'로그인 OK: {LOGIN_ID}')
        # apis 호출은 동일 출처 정책상 soffice 페이지 컨텍스트에서 (CORS 허용됨)
        driver.get('https://soffice.11st.co.kr/view/main'); time.sleep(8)
        driver.execute_script("window.__t = performance.now()")

        for path in [f'{BASE}/main/login-seller',
                     f'{BASE}/product-list/?pageNo=1&pageSize=3',
                     f'{BASE}/product-list/?page=1&size=3',
                     f'{BASE}/product-list/?pageNumber=1&pageSize=3&searchType=ALL',
                     f'{BASE}/product-list/?currentPage=1&pageSize=3&displayStatusCode=&searchKeyword=',
                     f'{BASE}/product-list/?pageNo=1&pageSize=3&dispYn=Y',
                     f'{BASE}/product/count',
                     f'{BASE}/product-list/count']:
            log(f'\n===== GET {path} =====')
            r = fetch(driver, path)
            log(f'status={r.get("status")}')
            body = r.get('body', '')
            # JSON 이면 키구조 요약
            try:
                j = json.loads(body)
                log('JSON keys: ' + str(list(j.keys()) if isinstance(j, dict) else type(j)))
                log(json.dumps(j, ensure_ascii=False)[:2500])
            except Exception:
                log(body[:1500])
    finally:
        try: driver.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

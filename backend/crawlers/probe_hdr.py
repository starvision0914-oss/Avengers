"""CDP 헤더주입(Vine-MemberNumber=M_N)으로 login-seller 직접조회 → 진짜 sellerNo"""
import os, sys, time, re, json, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LID = sys.argv[1] if len(sys.argv) > 1 else 'dlrmsgh011'


def log(m): print(m, flush=True)


def main():
    a = CrawlerAccount.objects.get(login_id=LID, platform='11st')
    log(f'계정: {LID} | 셀러명={a.seller_name} | 상태={a.crawling_status} | active={a.is_active}')
    d = create_driver(download_dir='/tmp/diag_dl')
    try:
        _ec._try_cookie_login(d, a)
        d.get('https://soffice.11st.co.kr/view/main'); time.sleep(5)
        mn = None
        for c in d.get_cookies():
            if c['name'] == 'TP':
                m = re.search(r'M_N(?:%7C|\|)(\d{6,})', c['value'])
                if m: mn = m.group(1)
        log(f'M_N(memberNo)={mn}')
        try:
            d.execute_cdp_cmd('Network.enable', {})
            d.execute_cdp_cmd('Network.setExtraHTTPHeaders',
                              {'headers': {'Vine-MemberNumber': str(mn)}})
        except Exception as e:
            log(f'CDP 헤더주입 err: {e}')
        d.get('https://apis.11st.co.kr/product/bruce/selleroffice/v1/main/login-seller')
        time.sleep(3)
        body = d.execute_script("return document.body.innerText")
        log(f'login-seller 응답: {body[:400]}')
        try:
            j = json.loads(body)
            if j.get('sellerNo'):
                log(f'>> 진짜 sellerNo={j["sellerNo"]} | M_N과 일치={str(j["sellerNo"])==str(mn)} | 닉={j.get("sellerNickName")}')
        except Exception:
            pass
    finally:
        try: d.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

"""읽기전용: 대량엑셀 그리드가 로드되는지만 확인 (생성요청 안 함)"""
import os, sys, time, re, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LID = sys.argv[1] if len(sys.argv) > 1 else 'jinag7461'


def main():
    a = CrawlerAccount.objects.get(login_id=LID, platform='11st')
    d = create_driver(download_dir='/tmp/diag_dl')
    try:
        _ec._try_cookie_login(d, a)
        d.get('https://soffice.11st.co.kr/view/main'); time.sleep(5)
        sn = None
        for c in d.get_cookies():
            if c['name'] == 'TP':
                m = re.search(r'M_N(?:%7C|\|)(\d{6,})', c['value'])
                if m: sn = m.group(1)
        d.get(f'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={sn}'); time.sleep(6)
        alert = None
        try:
            al = d.switch_to.alert; alert = al.text; al.accept()
        except Exception:
            pass
        g = ''
        try:
            g = d.execute_script("var x=document.getElementById('popup-body-grid');return x?x.innerText:''") or ''
        except Exception:
            pass
        ok = not (alert and '조회할 수 없습니다' in alert)
        print(f'[{LID}] sellerNo={sn} 로드alert={alert} 그리드OK={ok}', flush=True)
        print('  그리드: ' + ' | '.join([l for l in g.split('\n') if l.strip()][:8]), flush=True)
    finally:
        try: d.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

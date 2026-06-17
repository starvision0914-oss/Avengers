"""대량엑셀 무(無)sellerNo 파라미터로 그리드 로드/생성 가능한지 테스트"""
import os, sys, time, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LID = sys.argv[1] if len(sys.argv) > 1 else 'dlrmsgh011'
BTN = '//*[@id="popup-body-search"]/div[2]/button'


def log(m): print(m, flush=True)


def alert_txt(d, w=3):
    for _ in range(w*2):
        try:
            a=d.switch_to.alert; t=a.text; a.accept(); return t
        except Exception:
            time.sleep(0.5)
    return None


def grid(d):
    try:
        return d.execute_script("var x=document.getElementById('popup-body-grid');return x?x.innerText:''") or ''
    except Exception:
        return ''


def try_url(d, label, url):
    log(f'\n### {label}: {url} ###')
    d.get(url); time.sleep(6)
    a = alert_txt(d, 3)
    log(f'  로드 alert: {a}')
    log(f'  그리드: ' + ' | '.join([l for l in grid(d).split("\n") if l.strip()][:8]))
    return a


def main():
    acct = CrawlerAccount.objects.get(login_id=LID, platform='11st')
    d = create_driver(download_dir='/tmp/diag_dl')
    try:
        _ec._try_cookie_login(d, acct)
        log(f'로그인 OK: {LID} ({acct.seller_name})')
        # A) 무파라미터
        a1 = try_url(d, '무파라미터', 'https://soffice.11st.co.kr/pages/excel-download/')
        # 무파라미터에서 생성 시도
        if not (a1 and '조회할 수 없습니다' in a1):
            try:
                btn = WebDriverWait(d, 15).until(EC.element_to_be_clickable((By.XPATH, BTN)))
                d.execute_script("arguments[0].click();", btn)
                log(f'  생성요청 alert: {alert_txt(d, 10)}')
            except Exception as e:
                log(f'  생성버튼 실패: {str(e)[:80]}')
        # B) 빈 sellerNo
        try_url(d, '빈sellerNo', 'https://soffice.11st.co.kr/pages/excel-download/?sellerNo=')
    finally:
        try: d.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

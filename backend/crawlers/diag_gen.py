"""jinag7460 생성요청 후 어떤 팝업/모달/토스트가 뜨는지 덤프"""
import os, sys, time, re, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LID = sys.argv[1] if len(sys.argv) > 1 else 'jinag7460'
BTN = '//*[@id="popup-body-search"]/div[2]/button'


def log(m): print(m, flush=True)


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
        log(f'sellerNo={sn}')
        d.get(f'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={sn}'); time.sleep(6)
        log('클릭 전 그리드: ' + ' | '.join(
            [l for l in (d.execute_script("var g=document.getElementById('popup-body-grid');return g?g.innerText:''") or '').split('\n') if l.strip()][:9]))
        btn = WebDriverWait(d, 20).until(EC.element_to_be_clickable((By.XPATH, BTN)))
        d.execute_script("arguments[0].click();", btn)
        time.sleep(3)
        # alert?
        try:
            al = d.switch_to.alert; log(f'ALERT: {al.text}'); al.accept()
        except Exception:
            log('ALERT 없음')
        # 화면에 보이는 모든 팝업/모달/토스트 텍스트
        try:
            popups = d.execute_script("""
              return Array.from(document.querySelectorAll('div,span,p'))
                .filter(e=>{var s=getComputedStyle(e);
                  return s.display!=='none'&&s.visibility!=='hidden'&&e.offsetHeight>0
                    &&/한도|초과|이미|불가|제한|요청|완료|실패|오류|확인|생성/.test(e.innerText||'')
                    &&(e.innerText||'').length<120;})
                .map(e=>e.innerText.trim()).filter((v,i,a)=>a.indexOf(v)===i).slice(0,15);
            """)
            log('--- 화면 팝업/문구 후보 ---')
            for p in (popups or []):
                log(f'  · {p}')
        except Exception as e:
            log(f'popup dump err {e}')
        time.sleep(2)
        log('클릭 후 그리드: ' + ' | '.join(
            [l for l in (d.execute_script("var g=document.getElementById('popup-body-grid');return g?g.innerText:''") or '').split('\n') if l.strip()][:9]))
    finally:
        try: d.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

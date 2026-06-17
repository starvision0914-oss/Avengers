"""tmxkzhfldk8 등록상품 실패 원인 확정 — 로그인→생성요청→그리드/상품수 확인"""
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

LID = 'tmxkzhfldk8'
BTN = '//*[@id="popup-body-search"]/div[2]/button'


def log(m): print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


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


def main():
    a = CrawlerAccount.objects.get(login_id=LID, platform='11st')
    a.cookie_data=''; a.save(update_fields=['cookie_data'])  # 강제 새 로그인
    d = create_driver(download_dir='/tmp/diag_dl')
    try:
        log(f'{LID}({a.seller_name}) 새 로그인...')
        if not _ec._do_login(d, a.login_id, a.password_enc):
            log('로그인 실패'); return
        _ec._save_cookies(d, a)
        log('로그인 성공')
        sn=None
        for c in d.get_cookies():
            if c['name']=='TP':
                m=re.search(r'M_N(?:%7C|\|)(\d{6,})', c['value']);
                if m: sn=m.group(1)
        log(f'sellerNo={sn}')
        d.get(f'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={sn}'); time.sleep(6)
        alert_txt(d,3)
        log('요청전 그리드: '+' | '.join([l for l in grid(d).split('\n') if l.strip()][:9]))
        # 상품수 API 확인
        try:
            cnt=d.execute_async_script("""
              var cb=arguments[arguments.length-1];
              fetch('https://apis.11st.co.kr/product/bruce/selleroffice/v1/product-list/?pageNo=1&pageSize=1',{credentials:'include'})
                .then(r=>r.text()).then(t=>cb(t.slice(0,200))).catch(e=>cb('ERR'+e));""")
            log(f'product-list API: {cnt}')
        except Exception as e:
            log(f'API err {e}')
        log('파일생성요청 클릭...')
        try:
            btn=WebDriverWait(d,20).until(EC.element_to_be_clickable((By.XPATH,BTN)))
            d.execute_script("arguments[0].click();",btn)
            log('생성요청 alert: '+str(alert_txt(d,10)))
        except Exception as e:
            log(f'버튼 실패: {e}')
        # 2분 폴링하며 그리드 관찰
        for i in range(6):
            time.sleep(20); alert_txt(d,2)
            try: d.refresh(); time.sleep(4)
            except Exception: pass
            at=alert_txt(d,2)
            g=grid(d)
            log(f'[{(i+1)*20}s] 그리드: '+' | '.join([l for l in g.split("\n") if l.strip()][:9])+(f' || alert={at}' if at else ''))
    finally:
        try: d.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

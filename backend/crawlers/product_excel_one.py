"""11번가 대량엑셀 상품다운로드 — 단일계정 (sellerNo 자동탐지 → 생성요청 → 완료대기 → 다운로드 → 나의상품 저장)"""
import os, sys, time, re, zipfile, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from crawlers.test_product_excel import _read_rows, _ec_parse, _upsert
from apps.cpc.models import CrawlerAccount

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'jinag7461'
SN_OVERRIDE = sys.argv[2] if len(sys.argv) > 2 else None
BTN_GEN = '//*[@id="popup-body-search"]/div[2]/button'


def log(m): print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def accept_alert(driver, wait_s, tag=''):
    for _ in range(int(wait_s * 2)):
        try:
            a = driver.switch_to.alert
            t = a.text; log(f'  alert[{tag}]: {t}'); a.accept(); time.sleep(0.4); return t
        except Exception:
            time.sleep(0.5)
    return None


def grid_text(driver):
    try:
        return driver.execute_script(
            "var g=document.getElementById('popup-body-grid');return g?g.innerText:''") or ''
    except Exception:
        return ''


def detect_seller_no(driver):
    """TP 쿠키의 M_N = sellerNo (셀러오피스 로그인 세션). 가장 안정적."""
    if SN_OVERRIDE:
        log(f'  sellerNo 수동지정: {SN_OVERRIDE}')
        return SN_OVERRIDE
    driver.get('https://soffice.11st.co.kr/view/main'); time.sleep(6)
    for c in driver.get_cookies():
        if c['name'] == 'TP':
            m = re.search(r'M_N(?:%7C|\|)(\d{6,})', c['value'])
            if m:
                log(f'  TP쿠키 M_N(sellerNo)={m.group(1)}')
                return m.group(1)
    log('  TP쿠키에서 M_N 못찾음')
    return None


def main():
    acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='11st')
    DL = Path('/tmp/avengers_11st_product_downloads') / LOGIN_ID
    DL.mkdir(parents=True, exist_ok=True)
    for f in DL.glob('*'):
        try: f.unlink()
        except Exception: pass

    driver = create_driver(download_dir=str(DL))
    try:
        log(f'로그인: {LOGIN_ID}')
        used = _ec._try_cookie_login(driver, acct)
        if not used:
            if not _ec._do_login(driver, acct.login_id, acct.password_enc):
                log('로그인 실패'); return
            _ec._save_cookies(driver, acct)
        log('로그인 OK')

        sn = detect_seller_no(driver)
        log(f'>> 탐지된 sellerNo: {sn}')
        if not sn:
            log('sellerNo 탐지 실패 — 중단'); return

        url = f'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={sn}'
        log(f'페이지 진입: {url}')
        driver.get(url); time.sleep(6)
        before = [l for l in grid_text(driver).split('\n') if l.strip()][:8]
        log('  요청전 그리드: ' + ' | '.join(before))

        try:
            driver.execute_cdp_cmd('Page.setDownloadBehavior',
                                   {'behavior': 'allow', 'downloadPath': str(DL)})
        except Exception:
            pass

        log('파일생성요청 클릭...')
        btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, BTN_GEN)))
        driver.execute_script("arguments[0].click();", btn)
        accept_alert(driver, 15, '생성요청')

        today = time.strftime('%Y-%m-%d')
        ready = False
        for i in range(16):  # 최대 ~4분
            time.sleep(15)
            accept_alert(driver, 2, f'r{i}전')
            try:
                driver.refresh(); time.sleep(5)
            except Exception:
                pass
            atxt = accept_alert(driver, 2, f'r{i}후')
            g = grid_text(driver)
            if today in g and '파일 생성 완료' in g:
                log(f'  [{(i+1)*15}s] 오늘 파일 생성완료 확인')
                log('  완료 그리드: ' + ' | '.join(
                    [l for l in g.split('\n') if l.strip()][:10]))
                ready = True
                break
            log(f'  [{(i+1)*15}s] 대기중 (오늘행={today in g}, 완료={"파일 생성 완료" in g}'
                f'{", err="+atxt if atxt else ""})')
        if not ready:
            log('오늘 완료 파일 미확인 — 중단'); return

        log('오늘 파일 다운로드...')
        driver.execute_script("document.querySelector('#popup-body-grid a').click();")
        accept_alert(driver, 5, '다운로드')
        got = None
        for _ in range(90):
            files = [f for f in DL.glob('*') if not f.name.endswith('.crdownload')]
            if files:
                got = max(files, key=lambda f: f.stat().st_mtime); break
            time.sleep(1)
        if not got:
            log('다운로드 실패'); return
        log(f'다운로드: {got.name} ({got.stat().st_size}b)')
        # 파일명 날짜 검증
        fm = re.search(r'_(\d{8})\d{6}', got.name)
        log(f'  파일 생성일자: {fm.group(1) if fm else "?"} (오늘={time.strftime("%Y%m%d")})')

        target = got
        if zipfile.is_zipfile(got):
            with zipfile.ZipFile(got) as z:
                names = z.namelist(); z.extractall(DL)
            inner = [DL / n for n in names if n.lower().endswith(('.xls', '.xlsx', '.csv'))]
            if inner:
                target = inner[0]
        rows = _read_rows(target)
        prods = _ec_parse(rows)
        log(f'파싱: {len(prods)}건')
        if prods:
            log(f'  샘플: {prods[0]["product_no"]} {prods[0]["product_name"][:25]} {prods[0]["sale_price"]}')
        n = _upsert(acct, prods)
        from apps.cpc.models import ElevenMyProduct
        log(f'나의상품 저장 완료: {n}건 (DB총 {ElevenMyProduct.objects.filter(account=acct).count()})')
    finally:
        try: driver.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

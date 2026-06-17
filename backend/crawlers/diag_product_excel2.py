"""11번가 대량엑셀 진단 v2 — 올바른 sellerNo로 생성요청→오늘파일 완료까지 대기→다운로드"""
import os, sys, time, re, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'jinag7460'
SELLER_NO = sys.argv[2] if len(sys.argv) > 2 else '75122833'
BTN_GEN = '//*[@id="popup-body-search"]/div[2]/button'
DL = Path('/tmp/diag_dl'); DL.mkdir(exist_ok=True)
for f in DL.glob('*'):
    try: f.unlink()
    except Exception: pass


def log(m): print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def accept_alert(driver, wait_s, tag=''):
    for _ in range(int(wait_s * 2)):
        try:
            a = driver.switch_to.alert
            log(f'  alert[{tag}]: {a.text}'); a.accept(); time.sleep(0.4); return a.text
        except Exception:
            time.sleep(0.5)
    return None


def grid_text(driver):
    try:
        return driver.execute_script(
            "var g=document.getElementById('popup-body-grid');return g?g.innerText:''") or ''
    except Exception:
        return ''


def main():
    acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='11st')
    driver = create_driver(download_dir=str(DL))
    try:
        log(f'로그인: {LOGIN_ID}')
        used = _ec._try_cookie_login(driver, acct)
        if not used:
            if not _ec._do_login(driver, acct.login_id, acct.password_enc):
                log('로그인 실패'); return
            _ec._save_cookies(driver, acct)
        log('로그인 OK')

        url = f'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={SELLER_NO}'
        log(f'페이지 진입: {url}')
        driver.get(url); time.sleep(6)
        log(f'  실제 URL: {driver.current_url}')

        # 페이지 소스에서 셀러번호 단서 (일반화용)
        for pat in [r'sellerNo["\']?\s*[:=]\s*["\']?(\d{6,})',
                    r'(\d{8})_\d{3}_\d{14}']:
            m = re.search(pat, driver.page_source)
            if m:
                log(f'  소스 단서 {pat[:18]} = {m.group(1)}')

        before = grid_text(driver)
        log(f'=== 요청전 그리드 ===\n    ' + '\n    '.join(
            [l for l in before.split("\n") if l.strip()][:12]))

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
        done_link = None
        for i in range(16):  # 최대 ~4분
            time.sleep(15)
            accept_alert(driver, 2, f'r{i}전')
            try:
                driver.refresh(); time.sleep(5)
            except Exception:
                accept_alert(driver, 3, f'r{i}refresh')
            atxt = accept_alert(driver, 2, f'r{i}후')
            g = grid_text(driver)
            has_today = today in g
            completed = '파일 생성 완료' in g
            log(f'  [{(i+1)*15}s] 오늘({today})행={has_today} 완료문구={completed} '
                f'{"err="+atxt if atxt else ""}')
            if has_today and completed:
                # 오늘자 + 완료 → 다운로드 링크 확보
                lines = [l for l in g.split('\n') if l.strip()]
                log('  === 완료 그리드 ===\n    ' + '\n    '.join(lines[:14]))
                try:
                    href = driver.execute_script(
                        "var a=document.querySelector('#popup-body-grid a');"
                        "return a?a.href:''")
                    log(f'  다운로드 href: {href[:90]}')
                    done_link = href
                except Exception:
                    pass
                break
        else:
            log('  타임아웃 — 오늘 완료 파일 못확인')
            log('  최종 그리드:\n    ' + '\n    '.join(
                [l for l in grid_text(driver).split("\n") if l.strip()][:12]))

        if done_link:
            log('다운로드 시도(오늘 파일)...')
            driver.execute_script(
                "document.querySelector('#popup-body-grid a').click();")
            accept_alert(driver, 5, '다운로드')
            for _ in range(60):
                files = [f for f in DL.glob('*') if not f.name.endswith('.crdownload')]
                if files:
                    got = max(files, key=lambda f: f.stat().st_mtime)
                    log(f'  다운로드 완료: {got.name} ({got.stat().st_size}b)')
                    break
                time.sleep(1)
    finally:
        try: driver.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

"""11번가 대량엑셀(상품) 진단 — sellerNo 탐지 + 그리드(파일목록) 요청 전/후 비교"""
import os, sys, time, re, json, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'jinag7460'
BTN_GEN = '//*[@id="popup-body-search"]/div[2]/button'


def log(m): print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def accept_alert(driver, wait_s, tag=''):
    for _ in range(int(wait_s * 2)):
        try:
            a = driver.switch_to.alert
            log(f'  alert[{tag}]: {a.text}')
            a.accept(); time.sleep(0.4); return True
        except Exception:
            time.sleep(0.5)
    return False


def find_seller_no(driver):
    log('--- sellerNo 탐지 ---')
    driver.get('https://soffice.11st.co.kr/'); time.sleep(4)
    log(f'  현재 URL: {driver.current_url}')
    cands = {}
    # window 전역 키
    try:
        keys = driver.execute_script(
            "return Object.keys(window).filter(k=>/sell|member|mem|seller/i.test(k))")
        for k in (keys or [])[:30]:
            try:
                v = driver.execute_script(f"return JSON.stringify(window[{json.dumps(k)}])")
                if v and len(str(v)) < 300:
                    cands[f'win.{k}'] = v
            except Exception:
                pass
    except Exception as e:
        log(f'  win key err: {e}')
    # storage
    for store in ('localStorage', 'sessionStorage'):
        try:
            data = driver.execute_script(
                f"var o={{}};for(var i=0;i<{store}.length;i++){{var k={store}.key(i);"
                f"if(/sell|mem/i.test(k))o[k]={store}.getItem(k);}}return o;")
            for k, v in (data or {}).items():
                cands[f'{store}.{k}'] = str(v)[:200]
        except Exception:
            pass
    # 쿠키
    for c in driver.get_cookies():
        if re.search(r'sell|mem', c['name'], re.I):
            cands[f'cookie.{c["name"]}'] = c['value'][:120]
    # page source 정규식
    for pat in [r'"?sellerNo"?\s*[:=]\s*"?(\d{6,})',
                r'"?sellNo"?\s*[:=]\s*"?(\d{6,})',
                r'"?sellerMemNo"?\s*[:=]\s*"?(\d{6,})',
                r'"?memNo"?\s*[:=]\s*"?(\d{6,})']:
        m = re.search(pat, driver.page_source)
        if m:
            cands[f'src:{pat[:20]}'] = m.group(1)
    for k, v in cands.items():
        log(f'  후보 {k} = {v}')
    # 숫자만 추출해 최빈값 추정
    nums = re.findall(r'\d{6,}', ' '.join(str(v) for v in cands.values()))
    if nums:
        from collections import Counter
        top = Counter(nums).most_common(3)
        log(f'  숫자 빈도 top: {top}')
        return top[0][0]
    return None


def dump_grid(driver, tag):
    try:
        txt = driver.execute_script(
            "var g=document.getElementById('popup-body-grid');return g?g.innerText:'(grid없음)';")
    except Exception as e:
        txt = f'(err {e})'
    lines = [l for l in (txt or '').split('\n') if l.strip()][:25]
    log(f'=== 그리드 [{tag}] (상위 {len(lines)}줄) ===')
    for l in lines:
        log(f'    {l}')
    # 다운로드 링크들
    try:
        links = driver.execute_script(
            "return Array.from(document.querySelectorAll('#popup-body-grid a')).slice(0,8)"
            ".map(a=>({t:a.innerText.trim(),h:(a.getAttribute('href')||'').slice(0,60),"
            "oc:(a.getAttribute('onclick')||'').slice(0,60)}))")
        log(f'  그리드 내 링크 {len(links or [])}개:')
        for x in (links or []):
            log(f'    a: text="{x["t"]}" href="{x["h"]}" onclick="{x["oc"]}"')
    except Exception as e:
        log(f'  링크덤프 err: {e}')


def main():
    acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='11st')
    driver = create_driver(download_dir='/tmp/diag_dl')
    try:
        log(f'로그인: {LOGIN_ID}')
        used = _ec._try_cookie_login(driver, acct)
        if not used:
            if not _ec._do_login(driver, acct.login_id, acct.password_enc):
                log('로그인 실패'); return
            _ec._save_cookies(driver, acct)
        log('로그인 OK')

        sn = find_seller_no(driver)
        log(f'>> 추정 sellerNo: {sn}')

        # sellerNo 없이 + 있이 둘다 시도
        for sno in [sn, '75884047']:
            if not sno:
                continue
            url = f'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={sno}'
            log(f'\n##### 페이지 진입 sellerNo={sno} #####')
            driver.get(url); time.sleep(6)
            log(f'  실제 URL: {driver.current_url}')
            dump_grid(driver, f'요청전 sn={sno}')

            log('  파일생성요청 클릭...')
            try:
                btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, BTN_GEN)))
                driver.execute_script("arguments[0].click();", btn)
            except Exception as e:
                log(f'  버튼 클릭 실패: {e}')
                continue
            accept_alert(driver, 15, '생성요청')

            # 주기적 새로고침하며 오늘자 파일 등장 확인
            today = time.strftime('%Y%m%d')
            for i in range(8):
                time.sleep(15)
                accept_alert(driver, 2, f'refresh{i}전')
                driver.refresh(); time.sleep(5)
                accept_alert(driver, 2, f'refresh{i}후')
                try:
                    body = driver.execute_script(
                        "var g=document.getElementById('popup-body-grid');return g?g.innerText:''")
                except Exception:
                    body = ''
                has_today = today in (body or '') or time.strftime('%Y/%m/%d') in (body or '')
                log(f'  [{(i+1)*15}s후] 오늘({today}) 파일 있음? {has_today}')
                if has_today:
                    dump_grid(driver, f'오늘파일등장 sn={sno}')
                    break
            else:
                dump_grid(driver, f'요청후 타임아웃 sn={sno}')
            break  # 첫 유효 sellerNo 만 진단
    finally:
        try: driver.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()

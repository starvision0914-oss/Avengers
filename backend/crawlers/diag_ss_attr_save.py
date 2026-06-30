"""
판매자센터 상품 수정 페이지에서 속성 설정 후 저장 → PUT body 캡처
"""
import os, sys, time, json
sys.path.insert(0, '/home/rejoice888/Avengers/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from crawlers.browser import create_driver
from crawlers.smartstore_crawler import login_smartstore
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from apps.smartstore.models import SmartStoreAccount

LOGIN_ID = 'dlrmsgh01234@gmail.com'
acc = SmartStoreAccount.objects.get(login_id=LOGIN_ID)
DOWNLOAD_DIR = '/tmp/smartstore_excel'
driver = create_driver(download_dir=DOWNLOAD_DIR, enable_perf_log=True)

def ss(name):
    driver.save_screenshot(f'{DOWNLOAD_DIR}/{name}.png')
    print(f'SS: {name}')

def get_put_requests():
    logs = driver.get_log('performance')
    puts = []
    for entry in logs:
        try:
            msg = json.loads(entry['message'])
            m = msg.get('message', {})
            if m.get('method') == 'Network.requestWillBeSent':
                req = m.get('params', {}).get('request', {})
                if req.get('method') in ['PUT', 'POST'] and 'smartstore' in req.get('url', ''):
                    puts.append({
                        'url': req.get('url', ''),
                        'method': req.get('method'),
                        'body': req.get('postData', '')[:2000]
                    })
        except: pass
    return puts

try:
    ok = login_smartstore(driver, acc.login_id, acc.login_pw, print)
    if not ok: sys.exit(1)
    time.sleep(2)
    for _ in range(2):
        try:
            driver.find_element(By.XPATH, '//*[contains(text(),"하루동안")]').click()
            time.sleep(1)
        except: pass

    # 상품 목록 → 수정 버튼 클릭
    driver.get('https://sell.smartstore.naver.com/#/products/origin-list')
    time.sleep(7)
    try:
        driver.find_element(By.XPATH, '//*[contains(text(),"하루동안")]').click()
        time.sleep(1)
    except: pass

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[normalize-space(text())="검색"]'))
    ).click()
    time.sleep(7)

    edit_btn = driver.execute_script("""
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.textContent.trim() === '수정' && b.offsetParent) return b;
        }
        return null;
    """)
    if not edit_btn:
        print('수정 버튼 없음')
        sys.exit(1)

    driver.execute_script("arguments[0].click()", edit_btn)
    time.sleep(10)
    ss('s0_edit_page')
    print(f'URL: {driver.current_url}')

    # 속성 섹션 스크롤 후 확인
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2)")
    time.sleep(2)
    ss('s1_mid_page')

    # 상품속성 섹션 찾기
    attr_section = driver.execute_script("""
        var divs = document.querySelectorAll('div, section');
        for (var d of divs) {
            if (d.textContent.includes('상품속성') && d.textContent.includes('고정형태')) {
                return {found: true, html: d.outerHTML.substring(0, 1000)};
            }
        }
        // 텍스트로 찾기
        var all = document.body.querySelectorAll('*');
        for (var e of all) {
            if (e.textContent.trim() === '상품속성' && e.offsetParent) {
                return {found: true, tag: e.tagName, class: e.className, parentHtml: e.parentElement ? e.parentElement.outerHTML.substring(0, 500) : 'no parent'};
            }
        }
        return {found: false};
    """)
    print(f'속성 섹션: {json.dumps(attr_section, ensure_ascii=False)[:300]}')

    # 속성 값 선택 버튼 찾기 (무지)
    muji_clicked = driver.execute_script("""
        var all = document.querySelectorAll('button, span, div, label, li, a');
        for (var e of all) {
            var t = e.textContent.trim();
            if (t === '무지' && e.offsetParent) {
                e.click();
                return '클릭: ' + t;
            }
        }
        return '없음';
    """)
    print(f'무지 클릭: {muji_clicked}')
    time.sleep(1)
    ss('s2_after_attr_select')

    # "수정저장" 버튼 찾기 (클릭하지 않고 확인만)
    save_btn = driver.execute_script("""
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.textContent.includes('수정저장') && b.offsetParent) {
                return {text: b.textContent.trim(), class: b.className};
            }
        }
        return null;
    """)
    print(f'저장 버튼: {save_btn}')

    # 실제로 저장 시도 (PUT body 캡처용)
    if save_btn:
        print('\n수정저장 클릭...')
        driver.execute_script("""
            var btns = document.querySelectorAll('button');
            for (var b of btns) {
                if (b.textContent.includes('수정저장') && b.offsetParent) {
                    b.click();
                    break;
                }
            }
        """)
        time.sleep(5)
        ss('s3_after_save')

        puts = get_put_requests()
        print(f'\nPUT/POST 요청: {len(puts)}개')
        for p in puts:
            print(f'  {p["method"]} {p["url"]}')
            if p["body"]:
                print(f'  body: {p["body"][:500]}')

finally:
    time.sleep(2)
    driver.quit()
    print('\n완료')

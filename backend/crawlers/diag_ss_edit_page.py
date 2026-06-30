"""
상품 수정 버튼 클릭 후 속성 섹션 확인 + 네트워크 로그
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

def get_network_urls():
    logs = driver.get_log('performance')
    urls = set()
    for entry in logs:
        try:
            msg = json.loads(entry['message'])
            m = msg.get('message', {})
            if m.get('method') in ['Network.responseReceived', 'Network.requestWillBeSent']:
                url = (m.get('params', {}).get('response', {}).get('url', '') or
                       m.get('params', {}).get('request', {}).get('url', ''))
                if url and 'smartstore.naver.com' in url and not any(x in url for x in ['.css', '.js', '.png', '.svg', '.ico', '.woff']):
                    urls.add(url)
        except: pass
    return urls

def ss(name):
    driver.save_screenshot(f'{DOWNLOAD_DIR}/{name}.png')
    print(f'SS: {name}')

try:
    ok = login_smartstore(driver, acc.login_id, acc.login_pw, print)
    if not ok: sys.exit(1)
    time.sleep(2)
    for _ in range(2):
        try:
            driver.find_element(By.XPATH, '//*[contains(text(),"하루동안")]').click()
            time.sleep(1)
        except: pass

    # 상품 목록
    driver.get('https://sell.smartstore.naver.com/#/products/origin-list')
    time.sleep(7)
    ss('p0_list')

    # 검색
    try:
        driver.find_element(By.XPATH, '//*[contains(text(),"하루동안")]').click()
        time.sleep(1)
    except: pass
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[normalize-space(text())="검색"]'))
    ).click()
    time.sleep(7)
    ss('p1_searched')

    # 첫 번째 "수정" 버튼 찾아 클릭
    edit_btn = driver.execute_script("""
        var btns = document.querySelectorAll('button, a');
        for (var b of btns) {
            if (b.textContent.trim() === '수정' && b.offsetParent) {
                return b;
            }
        }
        return null;
    """)

    if edit_btn:
        print(f'수정 버튼 발견: {edit_btn.tag_name}')
        driver.execute_script("arguments[0].click()", edit_btn)
        time.sleep(8)
        ss('p2_edit_page')
        print(f'현재 URL: {driver.current_url}')

        # 속성 섹션 확인
        attr_info = driver.execute_script("""
            var sections = document.querySelectorAll('section, div[class*="section"], div[class*="item"]');
            var result = [];
            for (var s of sections) {
                var text = s.textContent.trim();
                if (text.includes('속성') || text.includes('상품정보') || text.includes('카테고리')) {
                    result.push({
                        tag: s.tagName,
                        class: s.className.substring(0, 50),
                        text: text.substring(0, 100)
                    });
                    if (result.length >= 5) break;
                }
            }
            return result;
        """)
        print(f'속성 관련 섹션: {json.dumps(attr_info, ensure_ascii=False)[:500]}')

        # 페이지 전체 텍스트에서 속성 확인
        page_text = driver.execute_script("return document.body.innerText;")
        if '속성' in page_text:
            idx = page_text.find('속성')
            print(f'속성 컨텍스트: {page_text[max(0,idx-50):idx+200]}')
        else:
            print('페이지에 "속성" 텍스트 없음')

        # 네트워크 로그에서 속성 API 확인
        urls = get_network_urls()
        attr_urls = [u for u in urls if any(k in u for k in ['attr', 'Attr', 'category', 'Category'])]
        print(f'\n속성 관련 URL: {len(attr_urls)}개')
        for u in attr_urls:
            print(f'  {u}')
    else:
        print('수정 버튼 없음')
        # 버튼 목록
        btns = driver.execute_script("""
            var btns = document.querySelectorAll('button, a');
            var r = [];
            for (var b of btns) {
                var t = b.textContent.trim();
                if (t && t.length < 20 && b.offsetParent) r.push(t);
            }
            return [...new Set(r)].slice(0, 20);
        """)
        print('버튼들:', btns)

finally:
    time.sleep(2)
    driver.quit()
    print('\n완료')

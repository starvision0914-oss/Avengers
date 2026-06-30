"""
판매자센터 상품 수정 페이지에서 속성 관련 API URL 캡처
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

def get_network_logs():
    logs = driver.get_log('performance')
    urls = []
    for entry in logs:
        try:
            msg = json.loads(entry['message'])
            m = msg.get('message', {})
            if m.get('method') == 'Network.responseReceived':
                url = m.get('params', {}).get('response', {}).get('url', '')
                if url and ('sell.smartstore.naver.com' in url or 'seller' in url.lower()):
                    urls.append(url)
        except: pass
    return urls

try:
    ok = login_smartstore(driver, acc.login_id, acc.login_pw, print)
    if not ok: sys.exit(1)
    time.sleep(2)
    for _ in range(2):
        try:
            driver.find_element(By.XPATH, '//*[contains(text(),"하루동안")]').click()
            time.sleep(1)
        except: pass

    # 첫 번째 상품 수정 페이지
    cno = 13645931373  # 가채 가발 묶음머리
    edit_url = f'https://sell.smartstore.naver.com/#/products/channel/{cno}/edit'
    print(f'상품 수정 페이지: {edit_url}')
    driver.get(edit_url)
    time.sleep(10)  # 페이지 로드 대기

    driver.save_screenshot(f'{DOWNLOAD_DIR}/attr_edit_page.png')
    print('스크린샷 저장됨')

    # 네트워크 로그 확인
    logs = get_network_logs()
    print(f'\n캡처된 URL: {len(logs)}개')

    attr_urls = [u for u in logs if any(k in u.lower() for k in ['attr', 'category', 'property', 'spec', 'option'])]
    print(f'속성 관련 URL: {len(attr_urls)}개')
    for u in attr_urls[:20]:
        print(f'  {u}')

    if not attr_urls:
        print('\n전체 URL 목록:')
        for u in logs[:30]:
            print(f'  {u}')

    # XHR/Fetch 요청 캡처
    all_logs = driver.get_log('performance')
    requests_made = []
    for entry in all_logs:
        try:
            msg = json.loads(entry['message'])
            m = msg.get('message', {})
            if m.get('method') == 'Network.requestWillBeSent':
                req = m.get('params', {}).get('request', {})
                url = req.get('url', '')
                if 'naver.com' in url and req.get('method') == 'GET':
                    requests_made.append(url)
        except: pass

    print(f'\n발송된 GET 요청: {len(requests_made)}개')
    for u in requests_made:
        if any(k in u.lower() for k in ['attr', 'categ', 'property', 'spec', 'product']):
            print(f'  ★ {u}')

    # 페이지 내용에서 속성 영역 찾기
    attr_section = driver.execute_script("""
        var els = document.querySelectorAll('*');
        for (var e of els) {
            if (e.textContent.includes('상품 속성') && e.children.length > 0) {
                return e.outerHTML.substring(0, 500);
            }
        }
        return '속성 섹션 없음';
    """)
    print(f'\n속성 섹션: {attr_section[:300]}')

finally:
    time.sleep(2)
    driver.quit()
    print('\n완료')

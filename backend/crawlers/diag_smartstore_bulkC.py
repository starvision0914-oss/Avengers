"""
숨겨진 체크박스 탐색 + 좌표 클릭 + Angular scope로 수정양식 다운로드
"""
import os, sys, time, glob
sys.path.insert(0, '/home/rejoice888/Avengers/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from crawlers.browser import create_driver
from crawlers.smartstore_crawler import login_smartstore
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

LOGIN_ID = 'dlrmsgh01234@gmail.com'
from apps.smartstore.models import SmartStoreAccount
acc = SmartStoreAccount.objects.get(login_id=LOGIN_ID)

DOWNLOAD_DIR = '/tmp/smartstore_excel'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
driver = create_driver(download_dir=DOWNLOAD_DIR)

def ss(name):
    driver.save_screenshot(f'{DOWNLOAD_DIR}/{name}.png')
    print(f'SS: {name}')

def wait_download(timeout=90):
    for i in range(timeout):
        files = (glob.glob(f'{DOWNLOAD_DIR}/*.xlsx') + glob.glob(f'{DOWNLOAD_DIR}/*.xls') +
                 glob.glob(f'{DOWNLOAD_DIR}/*.csv'))
        done = [f for f in files if not f.endswith('.crdownload') and os.path.getsize(f) > 100]
        if done:
            return done[0]
        if i % 10 == 0:
            print(f'  대기 {i}s')
        time.sleep(1)
    return None

try:
    ok = login_smartstore(driver, acc.login_id, acc.login_pw, print)
    if not ok:
        sys.exit(1)
    time.sleep(2)
    try:
        driver.find_element(By.XPATH, '//*[contains(text(),"하루동안")]').click()
        time.sleep(1)
    except: pass

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
    ss('90_searched')

    # 숨겨진 포함 모든 체크박스 탐색
    all_chk = driver.execute_script("""
        var inputs = document.querySelectorAll('input[type="checkbox"]');
        return Array.from(inputs).map(function(el, i) {
            var rect = el.getBoundingClientRect();
            return {
                i: i,
                name: el.name,
                ng_model: el.getAttribute('ng-model') || '',
                visible: el.offsetParent !== null,
                display: getComputedStyle(el).display,
                visibility: getComputedStyle(el).visibility,
                opacity: getComputedStyle(el).opacity,
                rect: {top: Math.round(rect.top), left: Math.round(rect.left), w: Math.round(rect.width), h: Math.round(rect.height)}
            };
        });
    """)
    import json
    print(f'전체 체크박스 {len(all_chk)}개:')
    for c in all_chk:
        print(f'  [{c["i"]}] ng_model={c["ng_model"]} vis={c["visible"]} disp={c["display"]} rect={c["rect"]}')

    # 화면에 보이는 체크박스 영역 클릭 (좌표)
    # 스크린샷에서 첫 번째 상품 행 체크박스가 약 x=230, y=580 위치
    print('\n좌표 클릭 시도 (헤더 체크박스: 약 230,555)')
    header_chk = driver.find_element(By.XPATH, '//div[contains(@class,"product-list") or contains(@class,"origin")]//input[@type="checkbox"] | //input[@type="checkbox" and @ng-model and contains(@ng-model,"select")]')
    print('발견:', header_chk.get_attribute('ng-model'))
except Exception as e_find:
    print(f'셀렉터 실패: {e_find}')

# ActionChains로 좌표 직접 클릭
try:
    # 스크롤해서 상품 목록 보이도록
    driver.execute_script("window.scrollTo(0, 400)")
    time.sleep(1)
    ss('91_scrolled')

    # 화면 크기 확인
    size = driver.execute_script("return {w: window.innerWidth, h: window.innerHeight}")
    print(f'화면 크기: {size}')

    # 첫 번째 상품 행의 체크박스 위치 추정 (화면 스크린샷 기준)
    # 체크박스가 약 x=230, y=165(스크롤 후) 위치
    action = ActionChains(driver)
    action.move_to_element_with_offset(driver.find_element(By.TAG_NAME, 'body'), 230, 165)
    action.click()
    action.perform()
    time.sleep(1)
    ss('92_coord_click')

    # 체크박스 상태 확인
    checked_count = driver.execute_script("""
        return document.querySelectorAll('input[type="checkbox"]:checked').length;
    """)
    print(f'체크된 체크박스: {checked_count}개')

    if checked_count == 0:
        # 다른 좌표 시도
        for y_offset in [155, 175, 185, 200]:
            for x_offset in [225, 235, 245]:
                action = ActionChains(driver)
                action.move_to_element_with_offset(driver.find_element(By.TAG_NAME, 'body'), x_offset, y_offset)
                action.click()
                action.perform()
                time.sleep(0.3)

        checked_count = driver.execute_script("""
            return document.querySelectorAll('input[type="checkbox"]:checked').length;
        """)
        print(f'재시도 후 체크된 체크박스: {checked_count}개')
        ss('93_retry_click')

except Exception as e:
    print(f'좌표 클릭 오류: {e}')

# Angular scope 직접 조작
try:
    result = driver.execute_script("""
        // ng-repeat 요소들 중 상품 목록 찾기
        var elements = document.querySelectorAll('[ng-repeat]');
        var productElements = [];
        elements.forEach(function(el) {
            var ngr = el.getAttribute('ng-repeat') || '';
            if (ngr.includes('product') || ngr.includes('item') || ngr.includes('list')) {
                productElements.push({ngr: ngr, tag: el.tagName, cls: el.className.substring(0,40)});
            }
        });
        return productElements.slice(0, 10);
    """)
    print('\nng-repeat 상품 관련 요소들:')
    for r in result:
        print(f'  {r}')
except: pass

# 수정양식 다운로드 시도
try:
    driver.execute_script("""
        var btns = document.querySelectorAll('button, div.item, li, a, span');
        for (var b of btns) {
            if (b.textContent.trim() === '엑셀 일괄작업' && b.offsetParent) {
                b.click();
                return '엑셀 일괄작업 클릭';
            }
        }
    """)
    time.sleep(2)

    msg = driver.execute_script("""
        var btns = document.querySelectorAll('a, li, div, span');
        for (var b of btns) {
            if (b.textContent.trim() === '수정양식 다운로드' && b.offsetParent) {
                b.click();
                return '수정양식 다운로드 클릭';
            }
        }
        return '없음';
    """)
    print('수정양식 클릭:', msg)
    time.sleep(3)

    try:
        alert_msg = driver.find_element(By.XPATH, '//*[contains(text(),"없습니다") or contains(text(),"선택")]')
        print('알림:', alert_msg.text[:80])
    except: pass

    ss('94_final')
    dl = wait_download(30)
    if dl:
        print(f'성공: {dl} ({os.path.getsize(dl):,}bytes)')
    else:
        print('실패')
except Exception as e:
    print(f'오류: {e}')

driver.quit()
print('\n완료')

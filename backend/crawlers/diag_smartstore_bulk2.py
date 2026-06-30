"""
상품관리 메뉴 클릭으로 상품 조회/수정 이동 후 일괄 수정 엑셀 다운로드 흐름 탐색
"""
import os, sys, time
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

os.makedirs('/tmp/smartstore_excel', exist_ok=True)
driver = create_driver(download_dir='/tmp/smartstore_excel')

def ss(name):
    path = f'/tmp/smartstore_excel/{name}.png'
    driver.save_screenshot(path)
    print(f'스크린샷: {path}')

try:
    ok = login_smartstore(driver, acc.login_id, acc.login_pw, print)
    if not ok:
        print('로그인 실패')
        sys.exit(1)

    # 공지 팝업 닫기
    try:
        close = driver.find_element(By.XPATH, '//*[contains(@class,"close") or contains(text(),"하루동안")]')
        close.click()
        time.sleep(1)
    except:
        pass

    ss('01_dashboard')

    # 상품관리 메뉴 클릭
    print('상품관리 메뉴 클릭')
    menu = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//li[contains(@class,"menu")]//span[text()="상품관리"] | //a[contains(text(),"상품관리")] | //*[text()="상품관리"]'))
    )
    menu.click()
    time.sleep(2)
    ss('02_product_menu')

    # 서브메뉴 목록 출력
    sub_items = driver.find_elements(By.XPATH, '//*[contains(@class,"sub") or contains(@class,"depth")]//a | //ul//li//a')
    print('메뉴 항목들:')
    for item in sub_items[:20]:
        txt = item.text.strip()
        href = item.get_attribute('href') or ''
        if txt:
            print(f'  "{txt}" href={href}')

    # 상품 조회/수정 클릭
    try:
        prod_menu = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//*[contains(text(),"상품 조회") or contains(text(),"조회/수정")]'))
        )
        prod_menu.click()
        time.sleep(4)
        print('현재 URL:', driver.current_url)
        ss('03_product_list')
    except Exception as e:
        print('상품 조회/수정 클릭 실패:', e)
        ss('03_fail')

    # 일괄수정 버튼 찾기
    btns = driver.find_elements(By.XPATH, '//*[contains(text(),"일괄") or contains(text(),"Excel") or contains(text(),"엑셀") or contains(text(),"다운")]')
    print('일괄/엑셀/다운 관련 요소:')
    for b in btns[:15]:
        txt = b.text.strip()
        if txt:
            print(f'  [{b.tag_name}] "{txt}"')

finally:
    time.sleep(2)
    driver.quit()
    print('완료')

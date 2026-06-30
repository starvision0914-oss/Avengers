"""
스마트스토어 판매자센터 상품 일괄 수정 엑셀 다운로드 다이애그
목적: 엑셀 양식 내 속성 컬럼 구조 파악
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

LOGIN_ID = 'dlrmsgh01234@gmail.com'

from apps.smartstore.models import SmartStoreAccount
acc = SmartStoreAccount.objects.get(login_id=LOGIN_ID)

driver = create_driver(download_dir='/tmp/smartstore_excel')
os.makedirs('/tmp/smartstore_excel', exist_ok=True)

try:
    ok = login_smartstore(driver, acc.login_id, acc.login_pw, print)
    if not ok:
        print('로그인 실패')
        driver.quit()
        sys.exit(1)

    print('로그인 성공, 상품 조회/수정 이동')
    driver.get('https://sell.smartstore.naver.com/#/products/manage')
    time.sleep(5)

    print('현재 URL:', driver.current_url)
    print('페이지 타이틀:', driver.title)

    # 전체 선택 체크박스
    try:
        chk = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type=checkbox][id*="all"], th input[type=checkbox]'))
        )
        chk.click()
        time.sleep(1)
        print('전체 선택 완료')
    except Exception as e:
        print('전체 선택 실패:', e)

    # 일괄 수정 버튼 찾기
    btns = driver.find_elements(By.XPATH, '//*[contains(text(),"일괄") or contains(text(),"Excel") or contains(text(),"엑셀")]')
    print('일괄/엑셀 관련 요소들:')
    for b in btns[:10]:
        print(f'  [{b.tag_name}] "{b.text.strip()}" class={b.get_attribute("class")}')

    # 스크린샷
    driver.save_screenshot('/tmp/smartstore_excel/products_page.png')
    print('스크린샷: /tmp/smartstore_excel/products_page.png')

    # 상품 일괄 등록 메뉴
    driver.get('https://sell.smartstore.naver.com/#/products/mass-upload')
    time.sleep(4)
    print('일괄 등록 URL:', driver.current_url)
    btns2 = driver.find_elements(By.XPATH, '//*[contains(text(),"양식") or contains(text(),"다운") or contains(text(),"Excel")]')
    for b in btns2[:10]:
        print(f'  [{b.tag_name}] "{b.text.strip()}"')
    driver.save_screenshot('/tmp/smartstore_excel/mass_upload.png')

finally:
    time.sleep(2)
    driver.quit()

print('완료')

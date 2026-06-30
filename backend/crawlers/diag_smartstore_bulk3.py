"""
원상품 조회/수정 페이지에서 일괄변경 옵션 확인 + 상품 일괄등록 엑셀 양식 다운로드
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

os.makedirs('/tmp/smartstore_excel', exist_ok=True)
driver = create_driver(download_dir='/tmp/smartstore_excel')

def ss(name):
    path = f'/tmp/smartstore_excel/{name}.png'
    driver.save_screenshot(path)
    print(f'스크린샷: {path}')

try:
    ok = login_smartstore(driver, acc.login_id, acc.login_pw, print)
    if not ok:
        sys.exit(1)

    # 팝업 닫기
    try:
        driver.find_element(By.XPATH, '//*[contains(text(),"하루동안")]').click()
        time.sleep(1)
    except: pass

    # 원상품 조회/수정 직접 이동
    print('원상품 조회/수정 이동')
    driver.get('https://sell.smartstore.naver.com/#/products/origin-list')
    time.sleep(5)
    print('URL:', driver.current_url)
    ss('04_origin_list')

    # 검색 버튼 클릭 (전체 상품 로드)
    try:
        search_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"검색") and not(contains(text(),"상세"))]'))
        )
        search_btn.click()
        time.sleep(5)
        ss('05_search_result')
    except Exception as e:
        print('검색 버튼 실패:', e)

    # 전체 선택 체크박스
    try:
        chk_all = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, '//thead//input[@type="checkbox"] | //th//input[@type="checkbox"]'))
        )
        chk_all.click()
        time.sleep(1)
        print('전체 선택 완료')
        ss('06_all_selected')
    except Exception as e:
        print('전체 선택 실패:', e)

    # 일괄변경 드롭다운 찾기
    bulk_btns = driver.find_elements(By.XPATH, '//*[contains(text(),"일괄변경") or contains(text(),"일괄 변경")]')
    print(f'일괄변경 요소 {len(bulk_btns)}개:')
    for b in bulk_btns[:5]:
        print(f'  [{b.tag_name}] "{b.text.strip()}" class={b.get_attribute("class")}')

    # 일괄변경 드롭다운 클릭해서 옵션 열기
    if bulk_btns:
        try:
            bulk_btns[0].click()
            time.sleep(2)
            ss('07_bulk_dropdown')
            options = driver.find_elements(By.XPATH, '//ul//li | //select//option | //*[@role="option"] | //*[@role="menuitem"]')
            print('드롭다운 옵션들:')
            for o in options[:20]:
                txt = o.text.strip()
                if txt and len(txt) > 1:
                    print(f'  "{txt}"')
        except Exception as e:
            print('드롭다운 클릭 실패:', e)

    # 상품 일괄등록 페이지 → 엑셀 양식 다운로드
    print('\n상품 일괄등록 페이지 이동')
    driver.get('https://sell.smartstore.naver.com/#/products/bulkadd')
    time.sleep(5)
    ss('08_bulkadd')
    print('URL:', driver.current_url)

    elems = driver.find_elements(By.XPATH, '//*[contains(text(),"양식") or contains(text(),"다운") or contains(text(),"엑셀") or contains(text(),"Excel") or contains(text(),"템플릿")]')
    print('양식/다운로드 관련 요소들:')
    for e in elems[:15]:
        txt = e.text.strip()
        if txt:
            print(f'  [{e.tag_name}] "{txt}"')

    # 양식 다운로드 버튼 클릭 시도
    for keyword in ['양식 다운', '엑셀 양식', '템플릿 다운', '양식다운']:
        try:
            btn = driver.find_element(By.XPATH, f'//*[contains(text(),"{keyword}")]')
            print(f'"{keyword}" 버튼 클릭')
            btn.click()
            time.sleep(5)
            break
        except: pass

    # 다운로드된 파일 확인
    files = os.listdir('/tmp/smartstore_excel')
    print('\n다운로드된 파일:', [f for f in files if f.endswith('.xlsx') or f.endswith('.xls')])

finally:
    time.sleep(2)
    driver.quit()
    print('완료')

"""롯데온 로그인 → 2FA 휴대폰 인증 선택 → 코드 파일 폴링(빠른 채팅relay용)."""
import os, sys, time
os.environ.setdefault('DISPLAY', ':99')
sys.path.insert(0, '/home/rejoice888/Avengers/backend')

from selenium.webdriver.common.by import By
from crawlers.browser import create_driver

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'rejoice234'
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else '@dlwodbs00'
CODE_FILE = '/tmp/lotteon_otp_code.txt'

if os.path.exists(CODE_FILE):
    os.remove(CODE_FILE)

profile_dir = f'/tmp/lotteon_profiles/{LOGIN_ID}'
driver = create_driver(user_data_dir=profile_dir, kill_existing=False)

def find_click(selectors, label, by=By.CSS_SELECTOR):
    for sel in selectors:
        try:
            els = driver.find_elements(by, sel)
        except Exception as e:
            print(f'{label} 선택자 오류({sel}): {e}', flush=True)
            continue
        if els:
            try:
                els[0].click()
            except Exception:
                driver.execute_script("arguments[0].click();", els[0])  # interactable 체크 우회
            print(f'{label} 클릭 완료 ({sel})', flush=True)
            return True
    print(f'{label} 못 찾음', flush=True)
    return False

def find_fill(selectors, value, label):
    for sel in selectors:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            els[0].clear(); els[0].send_keys(value)
            print(f'{label} 입력 완료 ({sel})', flush=True)
            return True
    print(f'{label} 못 찾음', flush=True)
    return False

try:
    driver.get('https://store.lotteon.com')
    time.sleep(3)
    print('현재 URL:', driver.current_url, flush=True)

    if 'login' not in driver.current_url.lower() and 'main' in driver.current_url.lower():
        print('이미 로그인된 상태 — 완료', flush=True)
        sys.exit(0)

    find_fill(['input[placeholder="사용자ID"]'], LOGIN_ID, '아이디')
    find_fill(['input[type="password"]'], PASSWORD, '비밀번호')
    find_click(['.btn_login'], '로그인버튼')
    time.sleep(3)
    print('로그인 후 URL:', driver.current_url, flush=True)

    # 2단계 인증: 휴대폰 박스 클릭 → SMS 발송 트리거
    # 실측 구조(2026-07-07): <li id="mf_phoneType" class="w2group phone athnSendBtn" style="cursor:pointer;">
    # WebSquare는 커스텀 마우스이벤트 바인딩이라 .click()이 안 먹을 수 있음 → ActionChains로 실제 마우스 이동+클릭
    from selenium.webdriver.common.action_chains import ActionChains
    try:
        el = driver.find_element(By.ID, 'mf_phoneType')
        ActionChains(driver).move_to_element(el).pause(0.3).click(el).perform()
        print('휴대폰인증박스 ActionChains 클릭 완료', flush=True)
    except Exception as e:
        print(f'ActionChains 클릭 실패: {e}', flush=True)
        find_click(['#mf_phoneType'], '휴대폰인증박스(폴백)')
    time.sleep(2)

    # 클릭 후 "전송/확인/인증번호받기" 등 추가 버튼이 있는지 폭넓게 탐색
    try:
        candidates = driver.find_elements(By.XPATH, '//*[@style[contains(.,"cursor")] or contains(@class,"btn") or self::button or self::a]')
        for c in candidates[:20]:
            txt = (c.text or '').strip()
            if txt:
                print(f'[클릭후보] text="{txt}" id={c.get_attribute("id")}', flush=True)
    except Exception as e:
        print(f'후보탐색 실패: {e}', flush=True)
    time.sleep(2)

    print('===== 코드 대기 시작 =====', flush=True)
    print(f'사용자가 코드를 알려주면 즉시 {CODE_FILE} 에 써주세요 — 0.5초마다 확인합니다.', flush=True)

    code = None
    for i in range(600):  # 최대 5분, 0.5초 간격
        if os.path.exists(CODE_FILE):
            with open(CODE_FILE) as f:
                code = f.read().strip()
            if code:
                break
        time.sleep(0.5)

    if not code:
        print('5분 경과 — 코드 못 받음', flush=True)
    else:
        print(f'코드 수신: {code} — 즉시 입력 시도', flush=True)
        find_fill(['input[placeholder*="인증"]', 'input[placeholder*="코드"]', 'input[type="text"]', 'input[type="tel"]', 'input[type="number"]'], code, '인증코드')
        find_click(['.btn_login', 'button[type="submit"]', '.btn_confirm', '.btn_ok'], '확인버튼')
        time.sleep(2)
        print('제출 후 URL:', driver.current_url, flush=True)

    print('브라우저는 계속 유지합니다.', flush=True)
    time.sleep(600)

except Exception as e:
    print(f'오류: {e}', flush=True)
    time.sleep(600)

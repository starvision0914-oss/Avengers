"""롯데온 판매자센터 로그인 — VNC(192.168.45.100:5905)로 사용자가 직접 OTP 입력하도록 화면에 띄워둠."""
import os, sys, time
os.environ.setdefault('DISPLAY', ':99')
sys.path.insert(0, '/home/rejoice888/Avengers/backend')

from selenium.webdriver.common.by import By
from crawlers.browser import create_driver

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'rejoice234'
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else '@dlwodbs00'

profile_dir = f'/tmp/lotteon_profiles/{LOGIN_ID}'
driver = create_driver(user_data_dir=profile_dir, kill_existing=False)
try:
    driver.get('https://store.lotteon.com')
    time.sleep(3)
    print('현재 URL:', driver.current_url)

    # 이미 로그인된 세션이면(쿠키 재사용) 바로 종료
    if 'login' not in driver.current_url.lower() and 'main' in driver.current_url.lower():
        print('이미 로그인된 상태로 보임 — 완료')
        sys.exit(0)

    # 로그인폼 탐색 (WebSquare 기반, 스크린샷으로 실측한 placeholder 우선)
    for sel in ['input[placeholder="사용자ID"]', '#login_id', 'input[name="userId"]', '#userId', 'input[placeholder*="아이디"]', 'input[placeholder*="ID"]']:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            els[0].clear(); els[0].send_keys(LOGIN_ID)
            print(f'아이디 입력 완료 ({sel})')
            break
    else:
        print('아이디 필드 못 찾음 — 화면 확인 필요')

    for sel in ['#login_pwd', 'input[name="password"]', '#password', 'input[type="password"]']:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            els[0].clear(); els[0].send_keys(PASSWORD)
            print(f'비밀번호 입력 완료 ({sel})')
            break
    else:
        print('비밀번호 필드 못 찾음 — 화면 확인 필요')

    for sel in ['button[type="submit"]', '.btn_login', '#loginBtn', 'button:contains("로그인")']:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            els[0].click()
            print(f'로그인 버튼 클릭 ({sel})')
            break
    else:
        print('로그인 버튼 못 찾음 — 화면에서 직접 눌러주세요')

    print('')
    print('===== VNC(192.168.45.100:5905)로 접속해서 =====')
    print('1) 로그인이 자동으로 안 됐으면 직접 아이디/비번 입력 후 로그인')
    print('2) SMS OTP 화면 뜨면 폰(010-****-9019)으로 온 코드를 화면에서 직접 입력')
    print('3) 완료되면 이 스크립트는 그냥 열어둔 채 알려주세요')
    print('')
    print('로그인 상태를 계속 확인합니다(브라우저는 절대 안 닫습니다)...')
    logged_in = False
    for i in range(180):   # 30분, 10초 간격
        time.sleep(10)
        try:
            url = driver.current_url
        except Exception as e:
            print(f'[{(i+1)*10}s] 브라우저 상태 확인 실패(창이 살아있는지 확인): {e}')
            continue
        if 'login' not in url.lower():
            print(f'[{(i+1)*10}s] 로그인 완료 감지! URL: {url}')
            logged_in = True
            break
        if (i+1) % 6 == 0:
            print(f'[{(i+1)*10}s] 아직 로그인 대기중... URL: {url}')
    if not logged_in:
        print('30분 경과 — 아직 로그인 화면일 수 있음. 브라우저는 계속 열어둡니다.')
    print('스크립트는 여기서 대기를 멈추지만 브라우저 프로세스는 그대로 유지됩니다.')

except Exception as e:
    print(f'오류 발생: {e}')
    print('브라우저는 그래도 유지합니다.')

# driver.quit()을 절대 호출하지 않음 — 사용자가 VNC로 계속 써야 하므로 브라우저를 살려둠.

"""티스토리(카카오계정) 로그인 — VNC(192.168.45.100:5905)로 사용자가 직접 카카오 보안인증을 통과하도록
화면에 띄워둠. 통과 후 쿠키를 TistoryAccount에 저장해 다음부터는 자동 로그인되게 함."""
import os, sys, time
os.environ.setdefault('DISPLAY', ':99')
sys.path.insert(0, '/home/rejoice888/Avengers/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from selenium.webdriver.common.by import By
from crawlers.browser import create_driver
from apps.tistory_blog.models import TistoryAccount

ACCOUNT_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1
account = TistoryAccount.objects.get(id=ACCOUNT_ID)

profile_dir = f'/tmp/tistory_profiles/{account.blog_name}'
driver = create_driver(user_data_dir=profile_dir, kill_existing=False)
try:
    driver.get('https://www.tistory.com/auth/login')
    time.sleep(2)
    els = driver.find_elements(By.CSS_SELECTOR, 'a.link_kakao_id')
    if els:
        els[0].click()
        print('카카오 로그인 버튼 클릭')
    time.sleep(2)

    els = driver.find_elements(By.CSS_SELECTOR, "input[name='loginId']")
    if els:
        els[0].clear(); els[0].send_keys(account.login_id)
        print('아이디 입력 완료')
    els = driver.find_elements(By.CSS_SELECTOR, "input[name='password']")
    if els:
        els[0].clear(); els[0].send_keys(account.login_pw)
        els[0].submit()
        print('비밀번호 입력+제출 완료')

    print('')
    print('===== VNC(192.168.45.100:5905)로 접속해서 =====')
    print('카카오 보안인증(기기인증/2단계인증 등) 화면이 뜨면 직접 통과시켜주세요.')
    print('완료되면 이 스크립트는 그대로 두고 알려주시면 됩니다.')
    print('')
    print(f'대상 블로그: https://{account.blog_name}.tistory.com/manage/newpost/')
    print('로그인 상태를 계속 확인합니다(브라우저는 절대 안 닫습니다)...')

    logged_in = False
    checked_manage_once = False
    for i in range(180):   # 30분, 10초 간격
        time.sleep(10)
        try:
            url = driver.current_url   # 절대 driver.get() 호출 안 함 — 사용자가 화면에서 인증 중인 페이지를 뺏지 않음
        except Exception as e:
            print(f'[{(i+1)*10}s] 브라우저 상태 확인 실패: {e}')
            continue
        # 로그인 페이지를 완전히 벗어났으면(카카오/티스토리 로그인 URL이 아니면) 로그인 완료로 간주.
        # 이후 한 번만 조용히 manage 페이지로 이동해 최종 확인(사용자 작업 중 방해 최소화).
        if 'auth/login' not in url and 'accounts.kakao.com' not in url:
            if not checked_manage_once:
                time.sleep(2)
                driver.get(f'https://{account.blog_name}.tistory.com/manage/newpost/')
                time.sleep(2)
                checked_manage_once = True
                url = driver.current_url
            if 'manage' in url and 'auth/login' not in url:
                print(f'[{(i+1)*10}s] 로그인 완료 감지! URL: {url}')
                logged_in = True
                break
        if (i + 1) % 6 == 0:
            print(f'[{(i+1)*10}s] 아직 로그인 대기중... URL: {url}')

    if logged_in:
        import json
        from django.utils import timezone
        account.cookie_data = json.dumps(driver.get_cookies())
        account.cookie_saved_at = timezone.now()
        account.save(update_fields=['cookie_data', 'cookie_saved_at'])
        print('쿠키 저장 완료 — 이제 자동화 크롤러가 이 쿠키로 로그인 가능')
    else:
        print('30분 경과 — 아직 로그인 화면일 수 있음. 브라우저는 계속 열어둡니다.')

except Exception as e:
    print(f'오류 발생: {e}')
    print('브라우저는 그래도 유지합니다.')

# driver.quit()을 절대 호출하지 않음 — 사용자가 VNC로 계속 써야 하므로 브라우저를 살려둠.

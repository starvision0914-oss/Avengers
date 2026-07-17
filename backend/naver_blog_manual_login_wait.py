"""
네이버 블로그 계정 수동 1회 로그인 대기 스크립트.
xclip/xdotool 없이도 진행 가능: 브라우저만 열어두고, 사람이 Avengers
'/naver-blog' 화면 보기(VNC)로 직접 들어가서 아이디/비번 입력 + 캡차/2차인증을 처리.
로그인 감지되면 쿠키 저장 후 종료.
사용: python3 -u naver_blog_manual_login_wait.py [login_id]  (기본 rejoice888)
로그: /tmp/naver_manual_login.log
"""
import os
import sys
import time

os.environ.setdefault('DISPLAY', ':99')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402
django.setup()

from crawlers.browser import create_driver  # noqa: E402
from crawlers.naver_blog_crawler import (  # noqa: E402
    NAVER_LOGIN_URL, _naver_logged_in, _save_cookies,
)
from apps.naver_blog.models import NaverBlogAccount  # noqa: E402

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'rejoice888'
MAX_WAIT_MIN = 20


def log(m):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), m), flush=True)


account = NaverBlogAccount.objects.get(login_id=LOGIN_ID)
driver = create_driver(kill_existing=False)
result = 'TIMEOUT'
try:
    driver.get(NAVER_LOGIN_URL)
    log('로그인 페이지 열림 — Avengers > 네이버블로그 > 계정 탭 > "화면 보기"로 들어와서 직접 로그인해주세요.')
    deadline = time.time() + MAX_WAIT_MIN * 60
    last_log = 0
    while time.time() < deadline:
        time.sleep(3)
        if _naver_logged_in(driver):
            result = 'OK'
            break
        if time.time() - last_log >= 30:
            log('로그인 대기 중... 남은 %d분' % int((deadline - time.time()) / 60))
            last_log = time.time()

    if result == 'OK':
        _save_cookies(driver, account)
        account.refresh_from_db()
        log('로그인 확인됨 — 쿠키 저장 완료 (len=%d)' % len(account.cookie_data or ''))
    else:
        log('시간 초과 — 로그인 미확인, 쿠키 저장 안 함')
finally:
    log('RESULT=%s' % result)
    try:
        driver.quit()
    except Exception:
        pass

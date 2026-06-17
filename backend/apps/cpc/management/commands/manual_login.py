"""
수동 로그인 — 캡차/2단계 인증이 필요한 계정을 웹 브라우저로 열어
사용자가 직접 인증 후 쿠키를 저장합니다.

사용법:
  python3 manage.py manual_login dlwodb777

웹브라우저: http://<서버IP>:6080/vnc.html 에서 확인
"""
import os
import sys
import json
import time
import signal
import subprocess
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger('crawler')

XVFB_DISPLAY = ':99'
VNC_PORT = 5999
NOVNC_PORT = 6080


class Command(BaseCommand):
    help = '수동 로그인 (캡차/2FA 인증용) — noVNC 웹으로 브라우저 제어'

    def add_arguments(self, parser):
        parser.add_argument('account_id', help='로그인할 계정 ID (예: dlwodb777)')
        parser.add_argument('--platform', default='gmarket', help='gmarket 또는 11st')
        parser.add_argument('--timeout', type=int, default=300, help='최대 대기시간(초)')

    def handle(self, *args, **options):
        login_id = options['account_id']
        platform = options['platform']
        timeout = options['timeout']

        from apps.cpc.models import CrawlerAccount
        try:
            acct = CrawlerAccount.objects.get(login_id=login_id, platform=platform)
        except CrawlerAccount.DoesNotExist:
            self.stderr.write(f'계정 없음: {login_id} ({platform})')
            return

        procs = []
        driver = None

        try:
            # 1. Xvfb 시작
            self.stdout.write('[1] Xvfb 시작...')
            xvfb = subprocess.Popen(
                ['Xvfb', XVFB_DISPLAY, '-screen', '0', '1920x1080x24'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            procs.append(xvfb)
            os.environ['DISPLAY'] = XVFB_DISPLAY
            time.sleep(1)

            # 2. x11vnc 시작
            self.stdout.write('[2] x11vnc 시작...')
            vnc = subprocess.Popen(
                ['x11vnc', '-display', XVFB_DISPLAY, '-rfbport', str(VNC_PORT),
                 '-nopw', '-forever', '-shared', '-noxdamage'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            procs.append(vnc)
            time.sleep(1)

            # 3. noVNC (websockify) 시작
            self.stdout.write('[3] noVNC 시작...')
            novnc = subprocess.Popen(
                ['websockify', '--web', '/usr/share/novnc/',
                 str(NOVNC_PORT), f'localhost:{VNC_PORT}'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            procs.append(novnc)
            time.sleep(1)

            self.stdout.write(self.style.SUCCESS(
                f'\n*** 웹 브라우저에서 접속하세요: http://192.168.1.16:{NOVNC_PORT}/vnc.html ***\n'
            ))

            # 4. Chrome 실행 (headless 아닌 실제 GUI)
            self.stdout.write('[4] Chrome 시작...')
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By

            chrome_bin = None
            for c in [os.path.expanduser('~/.local/share/google-chrome/chrome'),
                       '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
                       '/usr/bin/chromium-browser', '/usr/bin/chromium']:
                if os.path.isfile(c):
                    chrome_bin = c
                    break

            try:
                import undetected_chromedriver as uc
                opts = uc.ChromeOptions()
                if chrome_bin:
                    opts.binary_location = chrome_bin
                opts.add_argument('--no-sandbox')
                opts.add_argument('--disable-dev-shm-usage')
                opts.add_argument('--window-size=1920,1080')
                opts.add_argument('--start-maximized')

                ver = None
                try:
                    out = subprocess.check_output([chrome_bin, '--version'], stderr=subprocess.DEVNULL).decode()
                    ver = int(out.strip().split()[-1].split('.')[0])
                except Exception:
                    pass

                driver = uc.Chrome(options=opts, version_main=ver)
            except Exception:
                opts = Options()
                if chrome_bin:
                    opts.binary_location = chrome_bin
                opts.add_argument('--no-sandbox')
                opts.add_argument('--disable-dev-shm-usage')
                opts.add_argument('--window-size=1920,1080')
                driver = webdriver.Chrome(options=opts)

            # 5. 로그인 페이지 이동 + 자동 입력
            if platform == 'gmarket':
                login_url = 'https://ad.esmplus.com/'
                driver.get(login_url)
                time.sleep(3)

                try:
                    radio = driver.find_element(By.XPATH, '//input[@name="rdoSiteSelect" and @value="GMKT"]')
                    radio.click()
                    time.sleep(0.5)
                except Exception:
                    pass

                try:
                    driver.find_element(By.ID, 'SellerId').clear()
                    driver.find_element(By.ID, 'SellerId').send_keys(acct.login_id)
                    driver.find_element(By.ID, 'SellerPassword').clear()
                    driver.find_element(By.ID, 'SellerPassword').send_keys(acct.password_enc)
                    self.stdout.write(f'  아이디/비밀번호 자동 입력 완료')
                except Exception as e:
                    self.stdout.write(f'  자동 입력 실패: {e}')

            elif platform == '11st':
                login_url = 'https://login.11st.co.kr/auth/front/selleroffice/login.tmall'
                driver.get(login_url)
                time.sleep(3)

                try:
                    driver.find_element(By.ID, 'loginName').send_keys(acct.login_id)
                    driver.find_element(By.ID, 'passWord').send_keys(acct.password_enc)
                    self.stdout.write(f'  아이디/비밀번호 자동 입력 완료')
                except Exception as e:
                    self.stdout.write(f'  자동 입력 실패: {e}')

            self.stdout.write(self.style.WARNING(
                f'\n캡차/인증을 웹에서 직접 완료하세요. (최대 {timeout}초 대기)\n'
                f'로그인 성공 후 자동으로 쿠키가 저장됩니다.\n'
            ))

            # 6. 로그인 완료 대기
            success = False
            for i in range(timeout // 5):
                time.sleep(5)
                url = driver.current_url.lower()

                if platform == 'gmarket':
                    if 'logon' not in url and 'signin' not in url and 'ad.esmplus.com' in url:
                        success = True
                        break
                elif platform == '11st':
                    if 'soffice.11st.co.kr' in url:
                        success = True
                        break

                if (i + 1) % 12 == 0:
                    self.stdout.write(f'  {(i+1)*5}초 대기중... (현재: {driver.current_url[:60]})')

            if success:
                self.stdout.write(self.style.SUCCESS('\n로그인 성공!'))

                # 쿠키 저장
                cookies = driver.get_cookies()
                acct.cookie_data = json.dumps(cookies)
                acct.cookie_saved_at = timezone.now()
                acct.fail_count = 0
                acct.crawling_status = '정상'
                acct.save(update_fields=['cookie_data', 'cookie_saved_at', 'fail_count', 'crawling_status'])
                self.stdout.write(self.style.SUCCESS(f'쿠키 저장 완료 ({len(cookies)}개)'))
                self.stdout.write('이제 크롤러가 쿠키 로그인으로 정상 수집됩니다.')
            else:
                self.stdout.write(self.style.ERROR(f'\n타임아웃 ({timeout}초) — 로그인 미완료'))

        except KeyboardInterrupt:
            self.stdout.write('\n중단됨')
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            for p in reversed(procs):
                try:
                    p.terminate()
                    p.wait(timeout=5)
                except Exception:
                    try:
                        p.kill()
                    except Exception:
                        pass
            self.stdout.write('정리 완료')

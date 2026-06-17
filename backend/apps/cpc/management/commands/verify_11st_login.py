"""
11번가 ID/PW 단독 검증 명령
- 매 계정마다 새 chrome driver 생성/종료
- 로그인만 시도 (다운로드 안 함)
- 결과: PASS / OTP / FAIL_PW / FAIL_OTHER
"""
import time
import subprocess
from django.core.management.base import BaseCommand
from django.utils import timezone


def _kill_chrome():
    for proc in ['undetected_chromedriver', 'chromedriver', 'chrome --', 'Xvfb']:
        try:
            subprocess.run(['pkill', '-9', '-f', proc], timeout=3, capture_output=True)
        except Exception:
            pass


class Command(BaseCommand):
    help = '11번가 계정 ID/PW 단독 검증 (매 계정마다 chrome 재생성)'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='+', required=True)

    def handle(self, *args, **options):
        from apps.cpc.models import CrawlerAccount
        from crawlers.browser import create_driver, stop_display
        from crawlers.eleven_crawler import _do_login

        ids = options['accounts']
        accounts = list(CrawlerAccount.objects.filter(platform='11st', login_id__in=ids))
        found = {a.login_id for a in accounts}
        missing = set(ids) - found
        if missing:
            self.stdout.write(self.style.WARNING(f'없는 계정: {missing}'))

        results = []
        for acc in accounts:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'[{acc.login_id}] 검증 시작...')
            _kill_chrome()
            time.sleep(2)

            driver = None
            try:
                driver = create_driver()
                ok = _do_login(driver, acc.login_id, acc.password_enc)
                if ok:
                    url = driver.current_url
                    self.stdout.write(self.style.SUCCESS(f'[{acc.login_id}] ✅ PASS  url={url[:80]}'))
                    results.append((acc.login_id, 'PASS', ''))
                else:
                    url = driver.current_url
                    if 'otpLoginForm' in url:
                        self.stdout.write(self.style.WARNING(f'[{acc.login_id}] ⚠️  OTP 처리 실패 (ID/PW는 OK)'))
                        results.append((acc.login_id, 'OTP_FAIL', url))
                    else:
                        # alert 메시지 확인 시도
                        try:
                            page_text = driver.page_source[:500]
                        except Exception:
                            page_text = ''
                        self.stdout.write(self.style.ERROR(f'[{acc.login_id}] ❌ FAIL  url={url[:80]}'))
                        results.append((acc.login_id, 'FAIL', url[:120]))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[{acc.login_id}] ❌ ERROR: {str(e)[:100]}'))
                results.append((acc.login_id, 'ERROR', str(e)[:120]))
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                _kill_chrome()
                stop_display()

        # 최종 리포트
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write('=== 검증 결과 ===')
        for r in results:
            self.stdout.write(f'  {r[0]:<20} {r[1]:<10} {r[2][:60]}')
        ok_n = sum(1 for r in results if r[1] == 'PASS')
        self.stdout.write(self.style.SUCCESS(f'\n✅ PASS={ok_n} / 전체={len(results)}'))

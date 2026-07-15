"""지마켓 계정 ID/PW 단독 검증 명령 (테스트계정 1회 로그인 확인용)
- 매 계정마다 새 chrome driver 생성/종료(격리 프로필)
- 로그인만 시도, 성공 시 쿠키 저장. 다른 크롤링 안 함.
- 결과: PASS / FAIL
"""
import time
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 계정 ID/PW 단독 검증 (매 계정마다 chrome 재생성)'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='+', required=True)

    def handle(self, *args, **options):
        from apps.cpc.models import CrawlerAccount
        from apps.cpc.eleven_block_guard import preflight, release_global_lock
        from crawlers.browser import create_driver
        from crawlers.gmarket_cost_crawler import _esm_login, _save_cookies

        ids = options['accounts']
        accounts = list(CrawlerAccount.objects.filter(platform='gmarket', login_id__in=ids))
        found = {a.login_id for a in accounts}
        missing = set(ids) - found
        if missing:
            self.stdout.write(self.style.WARNING(f'없는 계정: {missing}'))

        ok, reason = preflight('verify_gmarket_login', platform='gmarket')
        if not ok:
            self.stdout.write(self.style.ERROR(f'사전점검 실패: {reason}'))
            return

        results = []
        try:
            for i, acc in enumerate(accounts):
                self.stdout.write(f'\n{"="*60}')
                self.stdout.write(f'[{acc.login_id}] 검증 시작...')

                driver = None
                try:
                    profile_dir = f'/tmp/gmarket_verify_profile_{acc.login_id}'
                    driver = create_driver(user_data_dir=profile_dir)
                    ok_login = _esm_login(driver, acc.login_id, acc.password_enc)
                    if ok_login:
                        _save_cookies(driver, acc)
                        self.stdout.write(self.style.SUCCESS(f'[{acc.login_id}] ✅ PASS'))
                        results.append((acc.login_id, 'PASS', ''))
                    else:
                        url = driver.current_url
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
                if i < len(accounts) - 1:
                    time.sleep(15)  # 캡차 유발 방지 — 계정 간 페이싱
        finally:
            release_global_lock('gmarket')

        # 최종 리포트
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write('=== 검증 결과 ===')
        for r in results:
            self.stdout.write(f'  {r[0]:<20} {r[1]:<10} {r[2][:60]}')
        ok_n = sum(1 for r in results if r[1] == 'PASS')
        self.stdout.write(self.style.SUCCESS(f'\n✅ PASS={ok_n} / 전체={len(results)}'))

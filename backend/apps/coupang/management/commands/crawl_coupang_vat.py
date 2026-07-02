"""쿠팡 Wing 부가세신고 매출자료 크롤링 (전 계정 순차).

사용법:
  python manage.py crawl_coupang_vat --start 202601 --end 202607
  python manage.py crawl_coupang_vat --account abc123 --start 202601 --end 202607
"""
import time

from django.core.management.base import BaseCommand

from apps.coupang.models import CoupangAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.browser import create_driver, stop_display
from crawlers.coupang_crawler import crawl_coupang_vat


class Command(BaseCommand):
    help = '쿠팡 Wing 부가세 매출자료 수집'

    def add_arguments(self, parser):
        parser.add_argument('--start', required=True, help='YYYYMM')
        parser.add_argument('--end', required=True, help='YYYYMM')
        parser.add_argument('--account', help='특정 login_id만')

    def handle(self, *args, **options):
        qs = CoupangAccount.objects.filter(is_active=True)
        if options.get('account'):
            qs = qs.filter(login_id=options['account'])
        accounts = list(qs.order_by('display_order', 'id'))
        self.stdout.write(f'[쿠팡] 대상 계정 {len(accounts)}개')

        if not accounts:
            return

        ok, reason = guard.preflight('쿠팡부가세수집', platform='coupang', wait=True, wait_timeout=1800)
        if not ok:
            self.stdout.write(self.style.ERROR(f'[쿠팡] 락 획득 실패: {reason}'))
            return

        success = fail = 0
        try:
            for acct in accounts:
                driver = None
                try:
                    driver = create_driver()
                    driver.set_page_load_timeout(40)
                    result = crawl_coupang_vat(
                        driver, acct, options['start'], options['end'],
                        log_fn=lambda m: self.stdout.write(m))
                    if result.get('판매자윙') or result.get('로켓그로스'):
                        success += 1
                    else:
                        fail += 1
                except Exception as e:
                    fail += 1
                    self.stdout.write(self.style.ERROR(f'[쿠팡:{acct.login_id}] 오류: {e}'))
                finally:
                    if driver:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                    stop_display()
                time.sleep(3)
        finally:
            guard.release_global_lock('coupang')

        self.stdout.write(self.style.SUCCESS(f'[쿠팡] 완료: 성공={success} 실패={fail}'))

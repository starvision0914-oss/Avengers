"""
python manage.py crawl_smartstore [--days N] [--date YYYY-MM-DD] [--account ID] [--skip-sales] [--skip-products]
"""
import time
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.smartstore.models import (
    SmartStoreAccount, SmartStoreSales, SmartStoreAdCost,
    SmartStoreProduct, SmartStoreCrawlLog,
)
from crawlers.browser import create_driver
from crawlers.smartstore_crawler import (
    login_smartstore, switch_store,
    fetch_daily_sales, fetch_ad_cost, fetch_products,
)

LOCK_FILE = '/tmp/smartstore_crawl.lock'


def _acquire_lock():
    import os, signal
    if os.path.exists(LOCK_FILE):
        try:
            pid = int(open(LOCK_FILE).read().strip().split('|')[0])
            os.kill(pid, 0)
            return False  # 다른 프로세스가 실행 중
        except (ProcessLookupError, OSError, ValueError):
            pass
    import os as _os
    with open(LOCK_FILE, 'w') as f:
        f.write(f'{_os.getpid()}|crawl_smartstore|{timezone.now().isoformat()}')
    return True


def _release_lock():
    import os
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass


class Command(BaseCommand):
    help = '스마트스토어 상품 + 판매통계 + 광고비 크롤링'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--date', type=str, help='YYYY-MM-DD 단일 날짜')
        parser.add_argument('--account', type=int, help='계정 ID (없으면 전체)')
        parser.add_argument('--skip-sales', action='store_true', help='판매통계 건너뜀')
        parser.add_argument('--skip-products', action='store_true', help='상품 수집 건너뜀')

    def handle(self, *args, **options):
        if not _acquire_lock():
            self.stdout.write('[smartstore] 이미 실행 중 — 건너뜀')
            return

        try:
            self._run(options)
        finally:
            _release_lock()

    def _run(self, options):
        if options['date']:
            start = end = date.fromisoformat(options['date'])
        else:
            end = date.today() - timedelta(days=1)
            start = end - timedelta(days=options['days'] - 1)

        skip_sales = options['skip_sales']
        skip_products = options['skip_products']

        self.stdout.write(f'[smartstore] 시작: 상품={"skip" if skip_products else "O"} 판매통계={"skip" if skip_sales else f"{start}~{end}"}')

        qs = SmartStoreAccount.objects.filter(is_active=True).exclude(login_pw='')
        if options['account']:
            qs = qs.filter(id=options['account'])

        accounts = list(qs.order_by('display_order'))
        self.stdout.write(f'[smartstore] 대상 계정: {len(accounts)}개')

        for account in accounts:
            crawl_log = SmartStoreCrawlLog.objects.create(account=account, status='running')
            driver = None
            try:
                driver = create_driver()
                self.stdout.write(f'  [{account.display_name}] 로그인 중...')

                if not login_smartstore(driver, account.login_id, account.login_pw,
                                        log_fn=lambda msg: self.stdout.write('    ' + msg)):
                    crawl_log.status = 'error'
                    crawl_log.message = '로그인 실패'
                    crawl_log.ended_at = timezone.now()
                    crawl_log.save()
                    continue

                # 복수 스토어 계정 전환
                if account.store_slug:
                    switch_store(driver, account.store_slug,
                                 log_fn=lambda msg: self.stdout.write('    ' + msg))

                messages = []

                # ── 상품 수집 ──
                if not skip_products:
                    products = fetch_products(driver,
                                             log_fn=lambda msg: self.stdout.write('    ' + msg))
                    prod_saved = 0
                    for p in products:
                        if not p['product_no']:
                            continue
                        SmartStoreProduct.objects.update_or_create(
                            account=account,
                            product_no=p['product_no'],
                            defaults={
                                'channel_product_no': p['channel_product_no'],
                                'name': p['name'],
                                'sale_price': p['sale_price'],
                                'stock_quantity': p['stock_quantity'],
                                'status_type': p['status_type'],
                                'seller_management_code': p['seller_management_code'],
                                'category_id': p['category_id'],
                                'product_image_url': p['product_image_url'],
                            }
                        )
                        prod_saved += 1
                    messages.append(f'상품:{prod_saved}건')
                    self.stdout.write(f'  [{account.display_name}] 상품 {prod_saved}건 저장')

                # ── 판매통계 ──
                if not skip_sales:
                    sales = fetch_daily_sales(driver, start, end,
                                              log_fn=lambda msg: self.stdout.write('    ' + msg))
                    sales_saved = 0
                    for row in sales:
                        SmartStoreSales.objects.update_or_create(
                            account=account,
                            date=row['date'],
                            defaults={
                                'order_count': row['order_count'],
                                'sales_amount': row['sales_amount'],
                                'cancel_amount': row['cancel_amount'],
                                'return_amount': row['return_amount'],
                                'settlement_amount': row['settlement_amount'],
                                'commission_amount': row['commission_amount'],
                            }
                        )
                        sales_saved += 1
                    messages.append(f'판매:{sales_saved}건')

                    # ── 광고비 ──
                    ad_costs = fetch_ad_cost(driver, start, end,
                                             log_fn=lambda msg: self.stdout.write('    ' + msg))
                    ad_saved = 0
                    for row in ad_costs:
                        SmartStoreAdCost.objects.update_or_create(
                            account=account,
                            date=row['date'],
                            ad_type=row['ad_type'],
                            defaults={
                                'cost': row['cost'],
                                'impression': row['impression'],
                                'click': row['click'],
                                'conversion_count': row['conversion_count'],
                                'conversion_amount': row['conversion_amount'],
                            }
                        )
                        ad_saved += 1
                    messages.append(f'광고:{ad_saved}건')

                crawl_log.status = 'done'
                crawl_log.message = ', '.join(messages)
                crawl_log.ended_at = timezone.now()
                crawl_log.save()
                self.stdout.write(f'  [{account.display_name}] 완료: {", ".join(messages)}')

            except Exception as e:
                self.stdout.write(f'  [{account.display_name}] 오류: {e}')
                crawl_log.status = 'error'
                crawl_log.message = str(e)[:500]
                crawl_log.ended_at = timezone.now()
                crawl_log.save()
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                time.sleep(5)

        self.stdout.write('[smartstore] 전체 완료')

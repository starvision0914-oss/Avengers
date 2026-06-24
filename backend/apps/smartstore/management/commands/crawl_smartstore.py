"""
python manage.py crawl_smartstore [--days N] [--date YYYY-MM-DD] [--account ID]
"""
import time
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.smartstore.models import SmartStoreAccount, SmartStoreSales, SmartStoreAdCost, SmartStoreCrawlLog
from crawlers.browser import get_driver, quit_driver
from crawlers.smartstore_crawler import crawl_smartstore_account


class Command(BaseCommand):
    help = '스마트스토어 판매통계 + 광고비 크롤링'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--date', type=str, help='YYYY-MM-DD 단일 날짜')
        parser.add_argument('--account', type=int, help='계정 ID (없으면 전체)')

    def handle(self, *args, **options):
        if options['date']:
            start = end = date.fromisoformat(options['date'])
        else:
            end = date.today() - timedelta(days=1)
            start = end - timedelta(days=options['days'] - 1)

        self.stdout.write(f'스마트스토어 크롤링: {start} ~ {end}')

        qs = SmartStoreAccount.objects.filter(is_active=True).exclude(login_pw='')
        if options['account']:
            qs = qs.filter(id=options['account'])

        accounts = list(qs.order_by('display_order'))
        self.stdout.write(f'대상 계정: {len(accounts)}개')

        for account in accounts:
            crawl_log = SmartStoreCrawlLog.objects.create(account=account, status='running')
            driver = None
            try:
                driver = get_driver()
                result = crawl_smartstore_account(
                    driver, account, start, end,
                    log_fn=lambda msg: self.stdout.write(msg)
                )

                if result is None:
                    crawl_log.status = 'error'
                    crawl_log.message = '로그인 실패 또는 비밀번호 없음'
                    crawl_log.ended_at = timezone.now()
                    crawl_log.save()
                    continue

                # 판매 통계 저장
                sales_saved = 0
                for row in result['sales']:
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

                # 광고비 저장
                ad_saved = 0
                for row in result['ad_costs']:
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

                crawl_log.status = 'done'
                crawl_log.message = f'판매:{sales_saved}건, 광고:{ad_saved}건'
                crawl_log.ended_at = timezone.now()
                crawl_log.save()
                self.stdout.write(f'  [{account.display_name}] 판매:{sales_saved} 광고:{ad_saved}')

            except Exception as e:
                self.stdout.write(f'  [{account.display_name}] 오류: {e}')
                crawl_log.status = 'error'
                crawl_log.message = str(e)[:500]
                crawl_log.ended_at = timezone.now()
                crawl_log.save()
            finally:
                if driver:
                    try:
                        quit_driver(driver)
                    except Exception:
                        pass
                time.sleep(5)

        self.stdout.write('완료')

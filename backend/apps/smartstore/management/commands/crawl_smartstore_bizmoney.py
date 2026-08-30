"""스마트스토어 비즈머니(비즈월렛) 잔액 수집 — ads.naver.com billing/balance 스크랩.

Usage:
  python3 manage.py crawl_smartstore_bizmoney
  python3 manage.py crawl_smartstore_bizmoney --account-id 7
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.smartstore.models import SmartStoreAccount


class Command(BaseCommand):
    help = '스마트스토어 비즈머니(비즈월렛) 잔액 수집'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', type=int)

    def handle(self, *args, **options):
        from crawlers.browser import create_driver
        from crawlers.smartstore_crawler import fetch_bizmoney_balance

        qs = SmartStoreAccount.objects.filter(is_active=True).exclude(
            naver_ad_account_id='', naver_ad_ai_account_id=''
        )
        if options['account_id']:
            qs = qs.filter(id=options['account_id'])

        accounts = [a for a in qs if a.naver_ad_account_id or a.naver_ad_ai_account_id]
        self.stdout.write(f'대상 계정: {len(accounts)}개')
        if not accounts:
            return

        driver = create_driver()
        ok = 0
        fail = 0
        try:
            for acc in accounts:
                balance = fetch_bizmoney_balance(driver, acc, log_fn=lambda m: self.stdout.write(f'  {m}'))
                if balance is not None:
                    SmartStoreAccount.objects.filter(pk=acc.pk).update(
                        bizmoney_balance=balance, bizmoney_synced_at=timezone.now()
                    )
                    self.stdout.write(f'{acc.display_name or acc.store_name}: {balance:,}원')
                    ok += 1
                else:
                    self.stdout.write(f'{acc.display_name or acc.store_name}: 수집 실패')
                    fail += 1
        finally:
            try:
                driver.quit()
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(f'완료: 성공 {ok} / 실패 {fail}'))

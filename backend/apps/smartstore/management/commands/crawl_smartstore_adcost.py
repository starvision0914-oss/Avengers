"""
스마트스토어 광고비 수집
  1) naver_ad_account_id 있는 계정 → 광고센터 billing 페이지 Selenium 스크랩 (소진액 VAT포함)
  2) naver_ad_customer_id 있는 계정 (billing ID 없음) → Naver 검색광고 REST API

Usage:
  python3 manage.py crawl_smartstore_adcost
  python3 manage.py crawl_smartstore_adcost --since 2026-06-01 --until 2026-06-27
  python3 manage.py crawl_smartstore_adcost --account-id 13
  python3 manage.py crawl_smartstore_adcost --billing-only   # billing 스크랩만
"""
import sys
import os
import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.smartstore.models import SmartStoreAccount, SmartStoreAdCost
from apps.smartstore.services.naver_search_ad import sync_ad_cost

logger = logging.getLogger('crawler')


def _save_billing_rows(account, rows: list, ad_type='cpc') -> int:
    """billing 스크랩 결과를 SmartStoreAdCost에 upsert."""
    upserted = 0
    for row in rows:
        SmartStoreAdCost.objects.update_or_create(
            account=account,
            date=row['date'],
            ad_type=ad_type,
            defaults={'cost': row['cost']},
        )
        upserted += 1
    return upserted


class Command(BaseCommand):
    help = '스마트스토어 광고비 수집 (billing 스크랩 우선, fallback API)'

    def add_arguments(self, parser):
        parser.add_argument('--since', type=str, default=None)
        parser.add_argument('--until', type=str, default=None)
        parser.add_argument('--account-id', type=int, default=None)
        parser.add_argument('--billing-only', action='store_true', default=False,
                            help='billing 스크랩 계정만 처리')

    def handle(self, *args, **options):
        since_str = options['since']
        until_str = options['until']
        account_id = options['account_id']
        billing_only = options['billing_only']

        today = date.today()
        since_date = date.fromisoformat(since_str) if since_str else today.replace(day=1)
        until_date = date.fromisoformat(until_str) if until_str else today

        qs = SmartStoreAccount.objects.filter(is_active=True)
        if account_id:
            qs = qs.filter(id=account_id)

        billing_accounts = [a for a in qs if a.naver_ad_account_id]
        ai_billing_accounts = [a for a in qs if a.naver_ad_ai_account_id and not billing_only]
        api_accounts = [a for a in qs
                        if not a.naver_ad_account_id and a.naver_ad_customer_id and not billing_only]

        # ── billing 스크랩 (Selenium) ──
        if billing_accounts:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../../crawlers'))
            try:
                from crawlers.browser import create_driver as make_driver
                from crawlers.smartstore_crawler import fetch_ad_cost_billing
            except ImportError:
                try:
                    import importlib.util, pathlib
                    _root = pathlib.Path(__file__).parents[5]
                    sys.path.insert(0, str(_root / 'crawlers'))
                    from browser import make_driver
                    from smartstore_crawler import fetch_ad_cost_billing
                except Exception as e:
                    self.stderr.write(f'browser 모듈 import 실패: {e}')
                    fetch_ad_cost_billing = None
                    make_driver = None

            if fetch_ad_cost_billing and make_driver:
                driver = make_driver()
                try:
                    for account in billing_accounts:
                        self.stdout.write(f'[billing] {account.display_name} (ad-account={account.naver_ad_account_id})')
                        rows = fetch_ad_cost_billing(
                            driver, account, since_date, until_date,
                            log_fn=lambda msg: self.stdout.write(f'  {msg}'),
                        )
                        if rows:
                            n = _save_billing_rows(account, rows)
                            self.stdout.write(f'  → 저장 {n}건')
                        else:
                            self.stdout.write('  → 데이터 없음')
                finally:
                    try:
                        driver.quit()
                    except Exception:
                        pass

        # ── AI billing 스크랩 (Selenium) ──
        if ai_billing_accounts:
            if not fetch_ad_cost_billing:
                pass
            else:
                driver_ai = make_driver()
                try:
                    for account in ai_billing_accounts:
                        self.stdout.write(f'[AI billing] {account.display_name} (ad-account={account.naver_ad_ai_account_id})')

                        class _AIProxy:
                            """fetch_ad_cost_billing에 AI 계정 정보를 주입하기 위한 프록시."""
                            def __init__(self, acc):
                                self._acc = acc
                            @property
                            def naver_ad_account_id(self): return self._acc.naver_ad_ai_account_id
                            @property
                            def naver_ad_login_id(self): return self._acc.naver_ad_ai_login_id
                            @property
                            def display_name(self): return self._acc.display_name

                        rows = fetch_ad_cost_billing(
                            driver_ai, _AIProxy(account), since_date, until_date,
                            log_fn=lambda msg: self.stdout.write(f'  {msg}'),
                        )
                        if rows:
                            n = _save_billing_rows(account, rows, ad_type='ai')
                            self.stdout.write(f'  → 저장 {n}건')
                        else:
                            self.stdout.write('  → 데이터 없음')
                finally:
                    try:
                        driver_ai.quit()
                    except Exception:
                        pass

        # ── REST API (fallback) ──
        for account in api_accounts:
            self.stdout.write(f'[API] {account.display_name}')
            result = sync_ad_cost(account, since=str(since_date), until=str(until_date))
            if result.get('skipped'):
                self.stdout.write(f'  → 스킵: {result["reason"]}')
            else:
                self.stdout.write(f'  → 저장 {result["upserted"]}건')

        if not billing_accounts and not api_accounts:
            self.stdout.write('광고비 수집 대상 계정 없음 (naver_ad_account_id 또는 naver_ad_customer_id 필요)')

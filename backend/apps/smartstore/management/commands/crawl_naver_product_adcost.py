"""
네이버 상품별 광고비 수집 (Naver Search Ad API)
Campaign → AdGroup → 소재(SHOPPING_PRODUCT_AD) → /stats?type=AD 순회

Usage:
  python3 manage.py crawl_naver_product_adcost
  python3 manage.py crawl_naver_product_adcost --since 2026-06-01 --until 2026-06-29
  python3 manage.py crawl_naver_product_adcost --account-id 13
"""
import logging
from datetime import date

from django.core.management.base import BaseCommand

from apps.smartstore.models import SmartStoreAccount, NaverAdProductReport
from apps.smartstore.services.naver_search_ad import fetch_product_stats

logger = logging.getLogger('crawler')


def _upsert_product_stats(account, since_date, until_date, ad_type, rows):
    upserted = 0
    for item in rows:
        NaverAdProductReport.objects.update_or_create(
            account=account,
            since_date=since_date,
            until_date=until_date,
            ad_type=ad_type,
            product_no=item['product_no'],
            defaults={
                'product_name': item.get('product_name', ''),
                'cost': item.get('cost', 0),
                'click': item.get('click', 0),
                'impression': item.get('impression', 0),
                'conversion_count': item.get('conversion_count', 0),
                'conversion_amount': item.get('conversion_amount', 0),
            },
        )
        upserted += 1
    return upserted


class Command(BaseCommand):
    help = '네이버 상품별 광고비 수집 (Naver Search Ad API — SHOPPING_PRODUCT_AD 소재)'

    def add_arguments(self, parser):
        parser.add_argument('--since', type=str, default=None)
        parser.add_argument('--until', type=str, default=None)
        parser.add_argument('--account-id', type=int, default=None)

    def handle(self, *args, **options):
        since_str = options['since']
        until_str = options['until']
        account_id = options['account_id']

        today = date.today()
        since_date = date.fromisoformat(since_str) if since_str else today.replace(day=1)
        until_date = date.fromisoformat(until_str) if until_str else today

        since = str(since_date)
        until = str(until_date)

        qs = SmartStoreAccount.objects.filter(is_active=True)
        if account_id:
            qs = qs.filter(id=account_id)

        for account in qs:
            has_cpc = bool(account.naver_ad_customer_id
                           and account.naver_ad_access_license
                           and account.naver_ad_secret_key)
            has_ai = bool(account.naver_ad_ai_customer_id
                          and account.naver_ad_ai_access_license
                          and account.naver_ad_ai_secret_key)

            if not has_cpc and not has_ai:
                continue

            self.stdout.write(f'\n[{account.display_name or account.store_name}]')

            if has_cpc:
                login_id = account.naver_ad_login_id or ''
                self.stdout.write(f'  CPC 상품별 수집 중 (customer={account.naver_ad_customer_id}, cookie={login_id}) ...')
                if not login_id:
                    self.stderr.write(f'  CPC 스킵: naver_ad_login_id 미설정')
                else:
                    try:
                        rows = fetch_product_stats(
                            account.naver_ad_customer_id,
                            account.naver_ad_access_license,
                            account.naver_ad_secret_key,
                            since, until,
                            login_id=login_id,
                        )
                        n = _upsert_product_stats(account, since_date, until_date, 'cpc', rows)
                        self.stdout.write(f'  CPC → {n}개 상품 저장')
                    except Exception as e:
                        self.stderr.write(f'  CPC 오류: {e}')
                        logger.exception('crawl_naver_product_adcost CPC error account=%s', account.id)

            if has_ai:
                ai_login_id = account.naver_ad_ai_login_id or ''
                self.stdout.write(f'  AI 상품별 수집 중 (customer={account.naver_ad_ai_customer_id}, cookie={ai_login_id}) ...')
                if not ai_login_id:
                    self.stderr.write(f'  AI 스킵: naver_ad_ai_login_id 미설정')
                else:
                    try:
                        rows = fetch_product_stats(
                            account.naver_ad_ai_customer_id,
                            account.naver_ad_ai_access_license,
                            account.naver_ad_ai_secret_key,
                            since, until,
                            login_id=ai_login_id,
                        )
                        n = _upsert_product_stats(account, since_date, until_date, 'ai', rows)
                        self.stdout.write(f'  AI → {n}개 상품 저장')
                    except Exception as e:
                        self.stderr.write(f'  AI 오류: {e}')
                        logger.exception('crawl_naver_product_adcost AI error account=%s', account.id)

        self.stdout.write('\n완료')

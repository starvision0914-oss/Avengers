"""
python manage.py crawl_smartstore [--days N] [--date YYYY-MM-DD] [--account ID] [--skip-sales] [--skip-products]

락: 계정별 /tmp/smartstore_{account_id}.lock — 다른 계정과 동시 실행 가능.
상품 수집: login_pw 있으면 Selenium, 없으면 Commerce API 폴백.
"""
import os
import time
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.smartstore.models import (
    SmartStoreAccount, SmartStoreSales, SmartStoreAdCost,
    SmartStoreProduct, SmartStoreCrawlLog,
)
from apps.smartstore.services.naver_api import sync_sales_api, _get_access_token, _fetch_products_page
from crawlers.browser import create_driver
from crawlers.smartstore_crawler import (
    login_smartstore, switch_store,
    fetch_daily_sales, fetch_ad_cost, fetch_products,
    fetch_merchant_no,
)


def _save_products_delete_insert(account, products, total_elements, ok, log_fn):
    """상품 리스트를 계정 기준으로 전량 삭제 후 재삽입(2026-08-24, 11번가/지마켓과 동일 원칙).
    total_elements(상품 API totalElements = 사전체크)를 계정에 기록해 실제 반영건수와 비교 가능하게 함.
    ok=False(API 자체가 불통)면 기존 데이터를 절대 건드리지 않고 그대로 반환(정합성 필드도 갱신 안 함)."""
    from collections import Counter
    if not ok:
        log_fn('[스마트] 상품 API 응답 자체가 없어 기존 데이터 유지(삭제 안 함)')
        return 0

    account.last_precheck_total = total_elements
    account.last_check_at = timezone.now()

    uniq = {}
    for p in products:
        pno = p.get('product_no')
        if pno:
            uniq[pno] = p

    SmartStoreProduct.objects.filter(account=account).delete()
    if uniq:
        cnt = Counter(p.get('status_type') or '' for p in uniq.values())
        objs = [SmartStoreProduct(
            account=account, product_no=pno,
            channel_product_no=p.get('channel_product_no', ''),
            name=(p.get('name') or '')[:500],
            sale_price=p.get('sale_price') or 0,
            stock_quantity=p.get('stock_quantity') or 0,
            status_type=p.get('status_type') or '',
            seller_management_code=(p.get('seller_management_code') or '')[:200],
            category_id=p.get('category_id') or '',
            product_image_url=p.get('product_image_url') or '',
        ) for pno, p in uniq.items()]
        SmartStoreProduct.objects.bulk_create(objs, batch_size=1000)
    else:
        cnt = Counter()

    account.last_excel_total = len(uniq)
    account.last_excel_selling = cnt.get('SALE', 0)
    account.last_excel_soldout = cnt.get('OUTOFSTOCK', 0)
    account.last_excel_stopped = cnt.get('SUSPENSION', 0)
    account.save(update_fields=[
        'last_precheck_total', 'last_check_at', 'last_excel_total',
        'last_excel_selling', 'last_excel_soldout', 'last_excel_stopped',
    ])
    if total_elements is not None and len(uniq) != total_elements:
        log_fn(f'[스마트] ⚠️ 사전체크({total_elements})와 실제반영({len(uniq)}) 불일치')
    return len(uniq)


def _lock_path(account_id):
    return f'/tmp/smartstore_{account_id}.lock'


def _acquire_lock(account_id):
    path = _lock_path(account_id)
    if os.path.exists(path):
        try:
            pid = int(open(path).read().strip().split('|')[0])
            os.kill(pid, 0)
            return False
        except (ProcessLookupError, OSError, ValueError):
            pass
    with open(path, 'w') as f:
        f.write(f'{os.getpid()}|crawl_smartstore_{account_id}|{timezone.now().isoformat()}')
    return True


def _release_lock(account_id):
    try:
        os.remove(_lock_path(account_id))
    except FileNotFoundError:
        pass


def _save_products_from_api(account, log_fn):
    """Commerce API로 상품 수집 — login_pw 없는 계정 전용."""
    token = _get_access_token(account.commerce_api_key, account.commerce_secret_key)
    all_products = []
    page = 1
    total_elements = None
    ok = False
    while True:
        data = _fetch_products_page(token, page=page, size=100)
        if not data:
            break
        ok = True
        if total_elements is None:
            total_elements = data.get('totalElements', 0) or 0
        contents = data.get('contents', [])
        all_products.extend(contents)
        if data.get('last', True) or not contents:
            break
        page += 1

    products = []
    for p in all_products:
        ch = p.get('channelProducts', [{}])[0]
        pno = str(p.get('originProductNo', ''))
        if not pno:
            continue
        products.append({
            'product_no': pno,
            'channel_product_no': str(ch.get('channelProductNo', '')),
            'name': ch.get('name', ''),
            'sale_price': ch.get('salePrice', 0) or 0,
            'stock_quantity': ch.get('stockQuantity', 0) or 0,
            'status_type': ch.get('statusType', ''),
            'seller_management_code': ch.get('sellerManagementCode', ''),
            'category_id': str(ch.get('categoryId', '')),
            'product_image_url': '',
        })
    saved = _save_products_delete_insert(account, products, total_elements, ok, log_fn)
    log_fn(f'[API] 상품 {saved}건 저장')
    return saved


class Command(BaseCommand):
    help = '스마트스토어 상품 + 판매통계 + 광고비 크롤링 (계정별 독립 락)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--date', type=str, help='YYYY-MM-DD 단일 날짜')
        parser.add_argument('--account', type=int, help='계정 ID (없으면 전체)')
        parser.add_argument('--skip-sales', action='store_true', help='판매통계 건너뜀')
        parser.add_argument('--skip-products', action='store_true', help='상품 수집 건너뜀')

    def handle(self, *args, **options):
        if options['date']:
            start = end = date.fromisoformat(options['date'])
        else:
            end = date.today() - timedelta(days=1)
            start = end - timedelta(days=options['days'] - 1)

        skip_sales = options['skip_sales']
        skip_products = options['skip_products']

        from django.db.models import Q
        qs = SmartStoreAccount.objects.filter(is_active=True)
        if options['account']:
            qs = qs.filter(id=options['account'])
        else:
            # 전체 실행 시 login_pw 또는 commerce_api_key 있는 계정만
            qs = qs.filter(Q(login_pw__gt='') | Q(commerce_api_key__gt=''))

        accounts = list(qs.order_by('display_order'))
        self.stdout.write(f'[smartstore] 대상: {len(accounts)}개, 상품={"skip" if skip_products else "O"} 판매통계={"skip" if skip_sales else f"{start}~{end}"}')

        for account in accounts:
            if not _acquire_lock(account.id):
                self.stdout.write(f'  [{account.display_name}] 이미 실행 중 — 건너뜀')
                continue

            try:
                self._crawl_account(account, start, end, skip_products, skip_sales)
            finally:
                _release_lock(account.id)
                time.sleep(3)

        self.stdout.write('[smartstore] 전체 완료')

    def _crawl_account(self, account, start, end, skip_products, skip_sales):
        log_fn = lambda msg: self.stdout.write('    ' + msg)
        crawl_log = SmartStoreCrawlLog.objects.create(account=account, status='running')
        messages = []

        # login_pw 없는 계정 → API 전용 (상품만, 판매통계 불가)
        if not account.login_pw:
            try:
                if not skip_products and account.commerce_api_key:
                    prod_saved = _save_products_from_api(account, log_fn)
                    messages.append(f'상품:{prod_saved}건(API)')
                if not skip_sales and account.commerce_api_key:
                    result = sync_sales_api(account, start, end)
                    messages.append(f'판매:{result.get("saved", 0)}건(API)')
                crawl_log.status = 'done'
                crawl_log.message = ', '.join(messages) or 'api-only'
            except Exception as e:
                self.stdout.write(f'  [{account.display_name}] API 오류: {e}')
                crawl_log.status = 'error'
                crawl_log.message = str(e)[:500]
            finally:
                crawl_log.ended_at = timezone.now()
                crawl_log.save()
            self.stdout.write(f'  [{account.display_name}] 완료(API): {", ".join(messages)}')
            return

        # Selenium 크롤
        driver = None
        try:
            driver = create_driver(enable_perf_log=True)
            self.stdout.write(f'  [{account.display_name}] 로그인 중...')

            if not login_smartstore(driver, account.login_id, account.login_pw, log_fn=log_fn):
                crawl_log.status = 'error'
                crawl_log.message = '로그인 실패'
                crawl_log.ended_at = timezone.now()
                crawl_log.save()
                return

            if account.store_slug:
                switch_store(driver, account.store_slug, log_fn=log_fn)

            merchant_no = fetch_merchant_no(driver, account, log_fn=log_fn)

            if not skip_products:
                products, total_elements, ok = fetch_products(driver, log_fn=log_fn)
                # Selenium API 자체가 불통이었을 때만 Commerce API 폴백(진짜 0건은 폴백 불필요)
                if not ok and account.commerce_api_key:
                    log_fn('[스마트] Selenium 상품 API 불통 → Commerce API 폴백')
                    prod_saved = _save_products_from_api(account, log_fn)
                    messages.append(f'상품:{prod_saved}건(API폴백)')
                else:
                    prod_saved = _save_products_delete_insert(account, products, total_elements, ok, log_fn)
                    messages.append(f'상품:{prod_saved}건')
                self.stdout.write(f'  [{account.display_name}] 상품 {prod_saved}건 저장')

            if not skip_sales:
                sales = fetch_daily_sales(driver, start, end, log_fn=log_fn, merchant_no=merchant_no)
                sales_saved = 0
                for row in sales:
                    SmartStoreSales.objects.update_or_create(
                        account=account, date=row['date'],
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

                if sales_saved == 0 and account.commerce_api_key:
                    log_fn('[스마트] CDP 0건 → Commerce API 폴백')
                    result = sync_sales_api(account, start, end)
                    sales_saved = result.get('saved', 0)
                    log_fn(f'[스마트] Commerce API 정산 {sales_saved}건 저장')
                messages.append(f'판매:{sales_saved}건')

                ad_costs = fetch_ad_cost(driver, account, start, end, log_fn=log_fn)
                ad_saved = 0
                for row in ad_costs:
                    SmartStoreAdCost.objects.update_or_create(
                        account=account, date=row['date'], ad_type=row.get('ad_type', 'cpc'),
                        defaults={
                            'cost': row['cost'],
                            'impression': row.get('impression', 0),
                            'click': row.get('click', 0),
                            'conversion_count': row.get('conversion_count', 0),
                            'conversion_amount': row.get('conversion_amount', 0),
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

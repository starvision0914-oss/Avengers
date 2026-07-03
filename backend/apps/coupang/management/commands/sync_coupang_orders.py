"""쿠팡 오픈API로 주문 동기화 (브라우저 자동화 없음, IP화이트리스트 등록된 계정만 가능).

사용법:
  python manage.py sync_coupang_orders --account rejoice678 --start 2026-01-01 --end 2026-07-03
"""
import datetime

from django.core.management.base import BaseCommand

from apps.coupang.models import CoupangAccount
from apps.coupang.services import fetch_all_order_sheets, save_orders


class Command(BaseCommand):
    help = '쿠팡 오픈API 주문 동기화'

    def add_arguments(self, parser):
        parser.add_argument('--account', required=True)
        parser.add_argument('--start', required=True, help='YYYY-MM-DD')
        parser.add_argument('--end', required=True, help='YYYY-MM-DD')

    def handle(self, *args, **options):
        acct = CoupangAccount.objects.filter(login_id=options['account']).first()
        if not acct:
            self.stdout.write(self.style.ERROR('계정 없음'))
            return
        if not acct.has_api_key:
            self.stdout.write(self.style.ERROR('오픈API 키 미등록'))
            return

        start = datetime.date.fromisoformat(options['start'])
        end = datetime.date.fromisoformat(options['end'])

        # 쿠팡 ordersheets는 조회기간 제한(최대 31일)이 있어 월 단위로 분할 호출
        total_saved = 0
        cur = start
        while cur <= end:
            chunk_end = min(datetime.date(cur.year, cur.month, 1) + datetime.timedelta(days=31), end)
            self.stdout.write(f'[쿠팡API:{acct.login_id}] {cur} ~ {chunk_end} 조회')
            orders = fetch_all_order_sheets(acct, cur, chunk_end, log_fn=lambda m: self.stdout.write(m))
            saved = save_orders(acct, orders)
            total_saved += saved
            self.stdout.write(f'  → {saved}건 저장')
            cur = chunk_end + datetime.timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f'[쿠팡API:{acct.login_id}] 총 {total_saved}건 저장'))

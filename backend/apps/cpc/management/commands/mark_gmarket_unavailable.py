"""지마켓 판매불가 표시 — 판매불가 상품은 goods/search API에서 통째로 빠지므로
크롤 시 갱신되지 않아 마지막 '판매중' 스냅샷이 박제된다. 각 계정의 최신 크롤보다
synced_at이 한참(12h+) 이전인 상품 = 최신 크롤에서 누락 = 판매목록에서 제외됨(판매불가/삭제)
→ status_type='판매불가'로 표시. (계정별 최신 크롤 기준이라 부분/실패 크롤에도 안전)
상품크롤(02시) 직후 실행해 나의상품 목록·비고를 최신 유지.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db.models import Max


class Command(BaseCommand):
    help = '지마켓 누락(판매불가) 상품을 status_type=판매불가로 표시'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=12, help='최신 크롤 대비 누락 판정 기준(시간)')

    def handle(self, *args, **opts):
        from apps.cpc.models import GmarketMyProduct
        gap = timedelta(hours=opts['hours'])
        latest = {r['account_id']: r['mx'] for r in
                  GmarketMyProduct.objects.values('account_id').annotate(mx=Max('synced_at'))}
        upd = 0
        for aid, mx in latest.items():
            if not mx:
                continue
            upd += (GmarketMyProduct.objects
                    .filter(account_id=aid, synced_at__lt=mx - gap)
                    .exclude(status_type='판매불가')
                    .update(status_type='판매불가'))
        self.stdout.write(self.style.SUCCESS(f'판매불가 표시: {upd}개'))

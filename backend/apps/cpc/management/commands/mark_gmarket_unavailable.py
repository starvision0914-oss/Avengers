"""지마켓 삭제됨 표시 — 크롤에서 3일+ 연속 누락된 상품은 판매자가 삭제한 것으로 판단.
판매중지(22)/판매불가(25)는 수집 시 API에서 직접 구분해 저장하므로 여기서는 건드리지 않음.
→ status_type='삭제됨'으로 표시.
※ 역방향 복구: 최근(3일내) 다시 크롤에 잡혔는데 삭제됨으로 박제된 것 → '판매중'으로 되돌림.
상품크롤(02시) 직후 실행해 나의상품 목록·비고를 최신 유지.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db.models import Max


class Command(BaseCommand):
    help = '지마켓 크롤 누락(삭제) 상품을 status_type=삭제됨으로 표시(3일+ 연속 누락)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=float, default=3,
                            help='최신 크롤 대비 누락 판정 기준(일). 기본 3일.')

    def handle(self, *args, **opts):
        from apps.cpc.models import GmarketMyProduct
        gap = timedelta(days=opts['days'])
        latest = {r['account_id']: r['mx'] for r in
                  GmarketMyProduct.objects.values('account_id').annotate(mx=Max('synced_at'))}
        marked = 0
        restored = 0
        for aid, mx in latest.items():
            if not mx:
                continue
            cutoff = mx - gap
            # 1) 3일+ 누락 → 삭제됨 (판매중지/판매불가는 API에서 직접 수집하므로 제외)
            marked += (GmarketMyProduct.objects
                       .filter(account_id=aid, synced_at__lt=cutoff)
                       .exclude(status_type__in=['판매불가', '판매중지', '삭제됨'])
                       .update(status_type='삭제됨'))
            # 2) 복구: 최근(3일내) 다시 크롤에 잡혔는데 삭제됨으로 박제된 것 → 판매중
            restored += (GmarketMyProduct.objects
                         .filter(account_id=aid, synced_at__gte=cutoff, status_type='삭제됨')
                         .update(status_type='판매중'))
        self.stdout.write(self.style.SUCCESS(
            f'삭제됨 표시: {marked}개 / 복구→판매중: {restored}개'))

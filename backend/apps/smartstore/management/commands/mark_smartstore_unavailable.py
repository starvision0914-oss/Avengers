"""스마트스토어 크롤 누락(삭제 추정) 상품을 status_type=DELETED로 표시(지마켓 mark_gmarket_unavailable과 동일 패턴).
3일+ 연속으로 최신 크롤에 안 잡히면 판매자가 지운 것으로 판단해 대시보드/나의상품에서 숨긴다.
판매중지(SUSPENSION)/품절(OUTOFSTOCK)/판매금지(PROHIBITION)/승인대기(UNADMISSION)는
API가 직접 구분해 저장하므로 여기서는 건드리지 않음. 상품 자체는 지우지 않고 상태만 바꾼다
(상품번호→판매자코드 매핑은 archive_product_codes 보존고에 별도 영구보관).
※ 역방향 복구: 최근(3일내) 다시 크롤에 잡혔는데 DELETED로 박제된 것 → SALE로 되돌림.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db.models import Max


class Command(BaseCommand):
    help = '스마트스토어 크롤 누락 상품을 status_type=DELETED로 표시(3일+ 연속 누락)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=float, default=3,
                            help='최신 크롤 대비 누락 판정 기준(일). 기본 3일.')

    def handle(self, *args, **opts):
        from apps.smartstore.models import SmartStoreProduct
        gap = timedelta(days=opts['days'])
        latest = {r['account_id']: r['mx'] for r in
                  SmartStoreProduct.objects.values('account_id').annotate(mx=Max('synced_at'))}
        marked = 0
        restored = 0
        for aid, mx in latest.items():
            if not mx:
                continue
            cutoff = mx - gap
            marked += (SmartStoreProduct.objects
                       .filter(account_id=aid, synced_at__lt=cutoff)
                       .exclude(status_type__in=['SUSPENSION', 'OUTOFSTOCK', 'PROHIBITION', 'UNADMISSION', 'DELETED'])
                       .update(status_type='DELETED'))
            restored += (SmartStoreProduct.objects
                         .filter(account_id=aid, synced_at__gte=cutoff, status_type='DELETED')
                         .update(status_type='SALE'))
        self.stdout.write(self.style.SUCCESS(
            f'DELETED 표시: {marked}개 / 복구→SALE: {restored}개'))

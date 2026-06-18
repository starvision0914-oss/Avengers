"""지마켓 판매불가 표시 — 판매불가 상품은 goods/search API에서 통째로 빠지므로
크롤 시 갱신되지 않아 마지막 '판매중' 스냅샷이 박제된다. 각 계정의 최신 크롤보다
synced_at이 3일+ 이전인 상품 = 여러 회차 연속 누락 = 판매목록에서 제외됨(판매불가/삭제)
→ status_type='판매불가'로 표시. (계정별 최신 크롤 기준이라 부분/실패 크롤에도 안전)
※ 12h/1일 기준은 크롤 하루 변동·부분실패로 멀쩡한 상품을 오판(가짜 판매불가 ~2천개) → 3일로 강화.
※ 역방향 복구: 최근(3일내) 다시 크롤에 잡힌(=판매목록 복귀) 판매불가 상품은 '판매중'으로 되돌림.
상품크롤(02시) 직후 실행해 나의상품 목록·비고를 최신 유지.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db.models import Max


class Command(BaseCommand):
    help = '지마켓 누락(판매불가) 상품을 status_type=판매불가로 표시(3일+ 연속 누락)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=float, default=3,
                            help='최신 크롤 대비 누락 판정 기준(일). 기본 3일(=여러 회차 연속 누락).')

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
            # 1) 3일+ 누락 → 판매불가
            marked += (GmarketMyProduct.objects
                       .filter(account_id=aid, synced_at__lt=cutoff)
                       .exclude(status_type='판매불가')
                       .update(status_type='판매불가'))
            # 2) 복구: 최근(3일내) 다시 크롤에 잡혔는데 판매불가로 박제된 것 → 판매중(가짜 판매불가 정정)
            restored += (GmarketMyProduct.objects
                         .filter(account_id=aid, synced_at__gte=cutoff, status_type='판매불가')
                         .update(status_type='판매중'))
        self.stdout.write(self.style.SUCCESS(
            f'판매불가 표시: {marked}개 / 가짜→판매중 복구: {restored}개'))

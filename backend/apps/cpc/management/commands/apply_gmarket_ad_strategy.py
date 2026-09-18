from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '옥션광고센터 일반광고 그룹 중 L코드(도매마트) 상품 보유 그룹을 찾아 노출요일/시간 전략 적용'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=30, help='이번 실행에서 새로 확인할 그룹 수')

    def handle(self, *args, **opts):
        from apps.cpc.models import GmarketAdStrategySchedule
        from crawlers.gmarket_ad_strategy_crawler import run_scan_apply

        sched = GmarketAdStrategySchedule.objects.first()
        if not sched:
            self.stdout.write('설정 없음 — GmarketAdStrategySchedule 먼저 생성 필요')
            return
        res = run_scan_apply(sched, limit=opts['limit'], log_fn=self.stdout.write)
        self.stdout.write(str(res))

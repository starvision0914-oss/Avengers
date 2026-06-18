from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = '지마켓 간편광고 ON/OFF 제어'
    def add_arguments(self, parser):
        parser.add_argument('action', choices=['on', 'off'])
        parser.add_argument('--accounts', nargs='*')
        parser.add_argument('--source', default='manual')
        parser.add_argument('--include-cpc1', action='store_true', help='일반광고(일반그룹)도 함께 제어')
    def handle(self, *args, **options):
        from crawlers.gmarket_cpc2_control_crawler import run_control
        accounts = options.get('accounts')
        include_cpc1 = options.get('include_cpc1', False)
        # 예약(크론) 실행: --accounts 미지정이면 예약에 저장된 계정만 대상 + 예약의 include_cpc1 사용.
        # (기존엔 None이라 run_control이 전체 계정을 돌리는 버그 — 예약 계정선택 무시됨)
        if not accounts and options['source'] == 'schedule':
            from apps.cpc.models import Cpc2Schedule
            sc = Cpc2Schedule.objects.first()
            accounts = list(sc.selected_accounts or []) if sc else []
            if sc and sc.include_cpc1:
                include_cpc1 = True
            if not accounts:
                self.stdout.write('예약에 선택된 계정 없음 — 종료(전체 실행 방지)')
                return
            self.stdout.write(f'예약 계정 {len(accounts)}개 대상: {accounts} (일반광고 포함={include_cpc1})')
        results = run_control(options['action'], options['source'],
            log_fn=lambda m: self.stdout.write(m), account_filter=accounts, include_cpc1=include_cpc1)
        self.stdout.write(self.style.SUCCESS(f'{len(results)}건 처리'))

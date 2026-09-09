from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = '지마켓 신규 광고센터(adcenter.esmplus.com) 캠페인 ON/OFF 제어'
    def add_arguments(self, parser):
        parser.add_argument('action', choices=['on', 'off'])
        parser.add_argument('--accounts', nargs='*')
        parser.add_argument('--source', default='manual')
    def handle(self, *args, **options):
        from crawlers.gmarket_new_adcenter_control import run_control
        accounts = options.get('accounts')
        # 예약(크론) 실행: --accounts 미지정이면 예약에 저장된 계정만 대상.
        # (crawl_gmarket_cpc2와 동일 패턴 — 미지정시 전체계정을 돌리는 버그 방지)
        if not accounts and options['source'] == 'schedule':
            from apps.cpc.models import NewAdCenterSchedule
            sc = NewAdCenterSchedule.objects.first()
            accounts = list(sc.selected_accounts or []) if sc else []
            if not accounts:
                self.stdout.write('예약에 선택된 계정 없음 — 종료(전체 실행 방지)')
                return
            self.stdout.write(f'예약 계정 {len(accounts)}개 대상: {accounts}')
        results = run_control(options['action'], options['source'],
            log_fn=lambda m: self.stdout.write(m), account_filter=accounts)
        self.stdout.write(self.style.SUCCESS(f'{len(results)}건 처리'))

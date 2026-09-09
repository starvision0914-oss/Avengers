from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = '지마켓 신규 광고센터(adcenter.esmplus.com) 캠페인별 광고비용 수집(통합운영=AI, 나머지=GM_CPC)'
    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')
        parser.add_argument('--source', default='manual')
    def handle(self, *args, **options):
        from crawlers.gmarket_new_adcenter_control import run_collect_costs
        accounts = options.get('accounts')
        results = run_collect_costs(options['source'],
            log_fn=lambda m: self.stdout.write(m), account_filter=accounts)
        self.stdout.write(self.style.SUCCESS(f'{len(results)}개 계정 처리'))

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 일반광고(파워클릭) ON/OFF 제어'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['on', 'off'])
        parser.add_argument('--accounts', nargs='*')
        parser.add_argument('--source', default='manual')

    def handle(self, *args, **options):
        from crawlers.gmarket_cpc1_control_crawler import run_control
        results = run_control(options['action'], options['source'],
            log_fn=lambda m: self.stdout.write(m), account_filter=options.get('accounts'))
        self.stdout.write(self.style.SUCCESS(f'{len(results)}건 처리'))

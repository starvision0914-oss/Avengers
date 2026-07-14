from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '오너클랜 마이페이지에서 계정정보(예치금/주문현황/구독서비스/최저가선점권) 스크래핑'

    def add_arguments(self, parser):
        parser.add_argument('--login-id', default=None)

    def handle(self, *args, **options):
        from crawlers.ownerclan_web_crawler import crawl_account_info
        from apps.ownerclan.models import OwnerclanApiAccount

        qs = OwnerclanApiAccount.objects.filter(is_active=True)
        if options.get('login_id'):
            qs = qs.filter(login_id=options['login_id'])

        for acct in qs:
            self.stdout.write(f'[{acct.login_id}] 시작')
            try:
                result = crawl_account_info(acct, log_fn=lambda m: self.stdout.write(m))
                self.stdout.write(self.style.SUCCESS(f'[{acct.login_id}] 완료: {result}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[{acct.login_id}] 예외 발생, 다음 계정으로 진행: {e}'))

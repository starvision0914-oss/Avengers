from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '오너클랜 정식 GraphQL API로 신규 상품을 예비상품에 자동 추가'

    def add_arguments(self, parser):
        parser.add_argument('--login-id', default=None, help='특정 계정만 (미지정시 전체 활성계정)')
        parser.add_argument('--max-pages', type=int, default=None)

    def handle(self, *args, **options):
        import time
        from crawlers.ownerclan_api_crawler import crawl_new_items
        from apps.ownerclan.models import OwnerclanApiAccount

        qs = OwnerclanApiAccount.objects.filter(is_active=True)
        if options.get('login_id'):
            qs = qs.filter(login_id=options['login_id'])

        for i, acct in enumerate(qs):
            if i > 0:
                time.sleep(3)  # 계정마다 연속 인증 요청 시 429(Too Many Requests) 발생 — 페이싱 필요
            self.stdout.write(f'[{acct.login_id}] 시작')
            try:
                result = crawl_new_items(acct, log_fn=lambda m: self.stdout.write(m),
                                          max_pages=options.get('max_pages'))
                self.stdout.write(self.style.SUCCESS(f'[{acct.login_id}] 결과: {result}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[{acct.login_id}] 실패(건너뜀): {e}'))

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '오너클랜 주간 인기 상품 다운로드(db저장창고, 계정무관 사이트 전체 랭킹 정적 리포트)'

    def add_arguments(self, parser):
        parser.add_argument('--login-id', default='dlwodb111')

    def handle(self, *args, **options):
        from crawlers.ownerclan_web_crawler import crawl_weekly_popular

        result = crawl_weekly_popular(options['login_id'], log_fn=lambda m: self.stdout.write(m))
        if result.get('error'):
            self.stdout.write(self.style.ERROR(f'실패: {result["error"]}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'완료: {result["saved_path"]}'))

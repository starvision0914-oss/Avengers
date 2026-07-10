from datetime import date

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '네이버 검색어(expKeyword) 리포트 수집 — 계정 단위 월 집계'

    def add_arguments(self, parser):
        parser.add_argument('--ym', help='YYYY-MM (미지정 시 이번달)')
        parser.add_argument('--accounts', nargs='*', type=int, help='특정 계정ID만')
        parser.add_argument('--no-save', action='store_true')

    def handle(self, *args, **options):
        from crawlers.naver_search_term_crawler import run_all_accounts
        today = date.today()
        ym = options.get('ym') or f'{today.year}-{today.month:02d}'
        result = run_all_accounts(
            ym=ym,
            account_filter=options.get('accounts'),
            log_fn=lambda m: self.stdout.write(m),
            save=not options.get('no_save', False),
        )
        self.stdout.write(self.style.SUCCESS(f'완료: {result}'))

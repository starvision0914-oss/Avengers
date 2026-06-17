from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = '11번가 광고비 크롤링'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 계정만 수집')
        parser.add_argument('--force', action='store_true', help='최근 수집 신선도 스킵 무시하고 전체 강제 재수집')
        parser.add_argument('--start-date', help='광고비 수집 시작일 (YYYY-MM-DD). 미지정 시 전월 1일')
        parser.add_argument('--scheduled', action='store_true',
                            help='예약(cron) 실행 — 다른 크롤 중이면 건너뛰지 않고 대기 후 실행, 문제 시 알림')
        parser.add_argument('--focused', action='store_true',
                            help='집중관리(is_focused) 계정만 수집 — 저녁 시간별 크롤용')

    def handle(self, *args, **options):
        from crawlers.eleven_crawler import run_all_accounts
        from apps.cpc import eleven_block_guard as guard
        scheduled = options.get('scheduled', False)
        acct_filter = options.get('accounts')
        if options.get('focused') and not acct_filter:
            from apps.cpc.models import CrawlerAccount
            acct_filter = list(CrawlerAccount.objects.filter(
                platform='11st', is_active=True, is_focused=True
            ).values_list('login_id', flat=True))
            self.stdout.write(f'집중관리(is_focused) {len(acct_filter)}계정만 수집')
        try:
            result = run_all_accounts(
                log_fn=lambda msg: self.stdout.write(msg),
                account_filter=acct_filter,
                force=options.get('force', False),
                start_date=options.get('start_date'),
                scheduled=scheduled,
            )
            self.stdout.write(self.style.SUCCESS(f'완료: {result}'))
        except Exception as e:
            if scheduled:
                guard.notify_problem('11번가광고비', f'예약 크롤 예외 발생 — {e}')
            raise

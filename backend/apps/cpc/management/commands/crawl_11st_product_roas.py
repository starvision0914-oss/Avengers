from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '11번가 adoffice 다운로드보고서 → 상품코드별 ROAS 수집'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*', help='특정 login_id 만')
        parser.add_argument('--daterange', help='YYYYMMDD,YYYYMMDD (미지정 시 전월)')
        parser.add_argument('--period', help='기간 라벨 (예: 2026-05)')
        parser.add_argument('--gsheet', action='store_true',
                            help='받은 보고서를 계정별 구글시트에도 업로드 (GSHEET_CREDENTIALS/GSHEET_11ST_KEY 필요)')
        parser.add_argument('--auto-period', action='store_true',
                            help='날짜 자동: 매월 1일=전월 전체, 그 외=당월(1일~어제)')

    def handle(self, *args, **options):
        import datetime as _dt
        from django.utils import timezone
        from crawlers.eleven_product_roas import run_all_accounts
        daterange = options.get('daterange')
        period_label = options.get('period')
        # --auto-period: 1일이면 전월 전체, 그 외엔 당월(1일~어제). 명시 daterange가 우선.
        if options.get('auto_period') and not daterange:
            today = timezone.localdate()
            if today.day == 1:
                last_day_prev = today - _dt.timedelta(days=1)        # 어제 = 전월 말일
                d0 = last_day_prev.replace(day=1); d1 = last_day_prev
            else:
                d0 = today.replace(day=1); d1 = today - _dt.timedelta(days=1)   # 당월 1일~어제
            daterange = f'{d0:%Y%m%d},{d1:%Y%m%d}'
            period_label = f'{d0:%Y-%m}'
            self.stdout.write(f'[auto-period] {period_label} ({daterange})')
        res = run_all_accounts(
            log_fn=lambda m: self.stdout.write(m),
            account_filter=options.get('accounts'),
            daterange=daterange,
            period_label=period_label,
            gsheet=options.get('gsheet', False),
        )
        self.stdout.write(str(res))

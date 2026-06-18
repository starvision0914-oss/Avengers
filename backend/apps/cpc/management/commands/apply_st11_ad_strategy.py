"""저장된 11번가 광고그룹 노출 스케줄 전략을 자동 재적용(cron용).

St11AdStrategySchedule(enabled=True)이고 오늘 요일이 weekdays에 포함되면 run_strategy(execute=True) 실행.
노출 스케줄은 11번가 측에 주간 단위로 박히지만, 계정/캠페인이 늘거나 초기화될 수 있어 주기 재적용으로 안전망.

사용:
  python manage.py apply_st11_ad_strategy            # 오늘 요일이 맞으면 실제 적용
  python manage.py apply_st11_ad_strategy --dry-run  # 찾기만(드라이런)
  python manage.py apply_st11_ad_strategy --force     # 요일/enabled 무시하고 즉시 적용
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = '저장된 11번가 노출 스케줄 전략을 자동 재적용'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='실제 적용 없이 찾기만')
        parser.add_argument('--force', action='store_true', help='enabled/요일 무시하고 적용')

    def handle(self, *args, **opts):
        from apps.cpc.models import St11AdStrategySchedule
        from crawlers.eleven_ad_strategy import run_strategy

        s = St11AdStrategySchedule.objects.order_by('id').first()
        if not s:
            self.stdout.write('저장된 전략 없음 — 종료')
            return
        if not opts['force'] and not s.enabled:
            self.stdout.write('자동 재적용 OFF(enabled=False) — 종료')
            return
        if not s.accounts or not s.campaigns:
            self.stdout.write('계정/캠페인 미설정 — 종료')
            return

        # 오늘 요일(KST) 1=월..7=일
        now = timezone.localtime()
        today = now.isoweekday()
        weekdays = s.weekdays or [1, 2, 3, 4, 5]
        if not opts['force'] and today not in weekdays:
            self.stdout.write(f'오늘({today}) 적용요일 아님({weekdays}) — 종료')
            return

        execute = not opts['dry_run']
        self.stdout.write(f'전략 적용: 계정 {len(s.accounts)} · 캠페인 {len(s.campaigns)} · '
                          f'{s.on_start}~{s.on_end}시 · 요일 {weekdays} · execute={execute}')
        run_id = run_strategy(
            s.accounts, s.campaigns,
            on_start=s.on_start, on_end=s.on_end, weekdays=weekdays,
            execute=execute, source='schedule',
        )
        if execute:
            s.last_applied_at = timezone.now()
            s.save(update_fields=['last_applied_at'])
        self.stdout.write(self.style.SUCCESS(f'완료 run_id={run_id}'))

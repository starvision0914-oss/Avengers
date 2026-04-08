"""
AI광고 예약 스케줄 실행 (ai100 참조)
- 크론: MM HH * * 1-5 (월~금 지정시간)
- 공휴일이면 스킵
- OFF→ON 실행 (시작일=다음 영업일)
- 수동 OFF 오버라이드: 마지막 히스토리가 manual+OFF면 건너뜀
"""
import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cpc.models import AiSchedule, GmarketAiAdHistory, GmarketAiAdSummary, CrawlerLog

logger = logging.getLogger('crawler')


class Command(BaseCommand):
    help = 'AI광고 예약 스케줄 실행'

    def add_arguments(self, parser):
        parser.add_argument('--action', default='off-on', help='off-on(기본), on, off')
        parser.add_argument('--date', help='시작일 강제 지정 (YYYY-MM-DD)')
        parser.add_argument('--force', action='store_true', help='공휴일/수동OFF 무시하고 강제 실행')

    def handle(self, *args, **options):
        schedule = AiSchedule.objects.filter(platform='gmarket').first()
        if not schedule:
            self.stdout.write('지마켓 AI 스케줄 설정 없음')
            return

        selected = schedule.selected_accounts or []
        if not selected:
            self.stdout.write('선택된 계정 없음')
            return

        today = datetime.now().date()
        today_str = today.isoformat()

        # 공휴일 목록
        holidays = set()
        if schedule.skip_holidays:
            holidays.update(schedule.enabled_holidays or [])
        holidays.update(schedule.custom_holidays or [])

        if not options['force']:
            # 오늘이 공휴일이면 스킵
            if today_str in holidays:
                self.stdout.write(f'{today_str} 공휴일 → 스킵')
                return

        # 시작일 계산
        if options['date']:
            start_date = options['date']
        else:
            start_date = self._next_business_day(today, holidays)

        action = options['action']
        self.stdout.write(f'예약 실행 — 오늘: {today_str}, 시작일: {start_date}, 액션: {action}, 대상: {selected}')

        # 대상 seller_id → gmarket_id 매핑
        summaries = GmarketAiAdSummary.objects.filter(
            seller_id__in=selected
        ).values_list('gmarket_id', flat=True).distinct()

        account_ids = list(summaries)
        if not account_ids:
            # selected_accounts가 gmarket_id일 수도 있음
            account_ids = selected

        # 수동 OFF 오버라이드 체크
        if not options['force']:
            filtered = []
            for aid in account_ids:
                last = GmarketAiAdHistory.objects.filter(gmarket_id=aid).order_by('-event_time').first()
                if last and 'OFF' in (last.history_type or '') and 'manual' in (last.detail or '').lower():
                    self.stdout.write(f'[{aid}] 수동 OFF 상태 → 건너뜀')
                    continue
                filtered.append(aid)
            account_ids = filtered

        if not account_ids:
            self.stdout.write('실행 대상 없음')
            return

        # AI 제어 실행
        from crawlers.gmarket_ai_control_crawler import run_control

        if action == 'off-on':
            # 먼저 OFF
            self.stdout.write('=== OFF 실행 ===')
            run_control('off', source='schedule', log_fn=self._log, account_filter=account_ids)
            # 그 다음 ON (시작일 지정)
            self.stdout.write(f'=== ON 실행 (시작일: {start_date}) ===')
            self._run_on_with_date(account_ids, start_date)
        elif action == 'on':
            self._run_on_with_date(account_ids, start_date)
        else:
            run_control(action, source='schedule', log_fn=self._log, account_filter=account_ids)

        CrawlerLog.objects.create(
            platform='gmarket', level='success',
            message=f'AI 스케줄 실행: {action}, 대상={len(account_ids)}개, 시작일={start_date}',
            account_id='schedule'
        )
        self.stdout.write(f'AI 스케줄 완료: {action}, {len(account_ids)}개 계정')

    def _run_on_with_date(self, account_ids, start_date):
        """ON 실행 시 시작일을 지정"""
        from crawlers.gmarket_ai_control_crawler import (
            _login, _get_group_info, set_ai_onoff, control_account
        )
        from crawlers.browser import create_driver, stop_display
        from apps.cpc.models import CrawlerAccount, GmarketAiAdHistory

        driver = None
        try:
            driver = create_driver()
            for aid in account_ids:
                acct = CrawlerAccount.objects.filter(
                    login_id=aid, platform='gmarket', is_active=True
                ).first()
                if not acct:
                    continue

                driver.delete_all_cookies()
                if not _login(driver, acct.login_id, acct.password_enc):
                    self._log(f'[AI스케줄:{aid}] 로그인 실패')
                    continue

                groups = _get_group_info(driver)
                for g in groups:
                    result = set_ai_onoff(driver, g['group_no'], 'on', start_date=start_date)
                    success = result and result.get('ResultCode') == 0 if result else False
                    self._log(f'[AI스케줄:{aid}] {g["seller_id"]}({g["group_name"]}): ON(시작일:{start_date}) {"성공" if success else "실패"}')

                    GmarketAiAdHistory.objects.create(
                        gmarket_id=aid,
                        seller_id=g['seller_id'],
                        group_name=g['group_name'],
                        event_time=timezone.now(),
                        history_type='AI ON (schedule)',
                        detail=f'시작일={start_date}, {"성공" if success else "실패"}',
                    )
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            stop_display()

    def _next_business_day(self, base_date, holidays):
        d = base_date + timedelta(days=1)
        for _ in range(30):
            if d.weekday() < 5 and d.isoformat() not in holidays:
                return d.isoformat()
            d += timedelta(days=1)
        return d.isoformat()

    def _log(self, msg):
        logger.info(msg)
        self.stdout.write(msg)

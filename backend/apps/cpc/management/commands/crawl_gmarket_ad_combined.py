"""지마켓 광고 통합 제어(크론용) — 한 로그인으로 AI+간편(CPC2) 순차 ON/OFF.
대상 계정은 각 스케줄(AiSchedule/Cpc2Schedule)의 selected_accounts에서 읽는다.
크론은 AI·간편의 시각·요일이 같을 때만 이 통합 명령을 호출한다(views._regenerate_ad_crons).
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 AI+간편광고 통합 제어 (한 로그인 순차)'

    def add_arguments(self, parser):
        parser.add_argument('--action', default='on', help='on / off')

    def handle(self, *args, **opts):
        from apps.cpc.models import Cpc2Schedule, AiSchedule
        from crawlers.gmarket_ad_combined_control import run_combined
        action = opts['action']
        cpc2 = Cpc2Schedule.objects.first()
        ai = AiSchedule.objects.filter(platform='gmarket').first()
        ai_accts = list(ai.selected_accounts or []) if ai else []
        cpc2_accts = list(cpc2.selected_accounts or []) if cpc2 else []
        self.stdout.write(f'통합제어 {action} — AI {len(ai_accts)}계정 / 간편 {len(cpc2_accts)}계정')
        run_combined(action, ai_accounts=ai_accts, cpc2_accounts=cpc2_accts,
                     source='schedule', log_fn=lambda m: self.stdout.write(m))

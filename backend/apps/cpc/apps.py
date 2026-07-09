import sys

from django.apps import AppConfig


class CpcConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cpc'

    def ready(self):
        # runserver가 막 뜬 시점 = 이전 프로세스에 떠있던 백그라운드 스레드는 전부 죽어있음이
        # 보장되는 유일한 순간. 그 순간에만 정리해야 지금 진짜로 도는 실행을 오폭 마감하지 않음.
        if 'runserver' not in sys.argv:
            return
        try:
            self._reconcile_stale_strategy_runs()
        except Exception:
            pass

    def _reconcile_stale_strategy_runs(self):
        """서버 재시작(배포 등)으로 중간에 끊긴 11번가 전략설정 실행을 정리.
        DONE 없이 남으면 대시보드 '진행 내역'에 최대 2시간 동안 유령 '진행중'으로 남던 문제
        (예: pm2 restart가 실제적용 중이던 스레드를 그대로 죽여버림) 방지."""
        from apps.cpc.models import St11AdStrategyLog

        done_ids = set(St11AdStrategyLog.objects.filter(status='DONE').values_list('run_id', flat=True))
        all_ids = set(St11AdStrategyLog.objects.values_list('run_id', flat=True))
        for rid in (all_ids - done_ids):
            St11AdStrategyLog.objects.create(
                run_id=rid, status='DONE',
                detail='서버 재시작으로 중단됨(자동 정리) — 그룹 일부만 적용됐을 수 있음, 필요시 재실행하세요.')

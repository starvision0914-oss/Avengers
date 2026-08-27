"""광고 정기크론에 강제종료됐던 작업을 재개(2026-08-27 사용자 요청).
광고크론 셸스크립트 맨 끝에서 호출."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '강제선점으로 종료됐던 지마켓 작업을 재실행'

    def handle(self, *args, **opts):
        from apps.cpc import eleven_block_guard as guard
        n = guard.resume_preempted('gmarket', log_fn=lambda m: self.stdout.write(m))
        if n:
            self.stdout.write(self.style.SUCCESS(f'{n}건 재개'))
        else:
            self.stdout.write('재개할 작업 없음')

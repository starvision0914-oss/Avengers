"""11번가 만료계정(24h10m+) 실제 OTP 재인증 자동화(2026-09-18 신설).

기존 "만료계정 자동인증" 버튼(ElevenVerifyOtpView, auto=True)과 완전히 동일한 기준·락을
재사용 — 사람이 안 눌러도 자동으로 돌게 크론으로 등록. last_real_otp_at이 24h10m 이상
지난 계정만 실제 OTP 화면까지 통과시켜(verify_11st_logins) 대시보드 만료 표시를 해소한다.
(발단: 실측 결과 다수 계정이 90~166시간째 방치돼 있었음 — 버튼이 자동으로 안 눌렸기 때문.)"""
import os
import subprocess

from django.core.management.base import BaseCommand

_VERIFY_LOCK = '/tmp/eleven_verify_otp_running.lock'


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


class Command(BaseCommand):
    help = '11번가 만료계정(24h10m+) 자동 OTP 재인증'

    def handle(self, *args, **opts):
        from datetime import timedelta
        from django.utils import timezone
        from apps.cpc.models import CrawlerAccount

        if os.path.exists(_VERIFY_LOCK):
            try:
                pid = open(_VERIFY_LOCK).read().strip().split('|', 1)[0]
            except Exception:
                pid = None
            if pid and _pid_alive(pid):
                self.stdout.write('이미 인증 진행 중(수동 버튼 또는 다른 실행) — 스킵')
                return
            try:
                os.remove(_VERIFY_LOCK)
            except Exception:
                pass

        now = timezone.now()
        threshold = timedelta(hours=24, minutes=10)
        expired = [
            a.login_id for a in CrawlerAccount.objects.filter(platform='11st', is_active=True)
            if a.last_real_otp_at is None or (now - a.last_real_otp_at) >= threshold
        ]
        if not expired:
            self.stdout.write('만료된 계정 없음(24h10m 기준)')
            return

        self.stdout.write(f'만료계정 {len(expired)}개 재인증 시작: {expired}')
        cmd = (
            'cd /home/rejoice888/Avengers/backend && '
            f'python3 manage.py verify_11st_logins --only {",".join(expired)} '
            '>> /tmp/eleven_verify_auto.log 2>&1'
        )
        proc = subprocess.Popen(['bash', '-c', cmd], start_new_session=True)
        with open(_VERIFY_LOCK, 'w') as f:
            f.write(f'{proc.pid}|' + ','.join(expired))
        try:
            proc.wait(timeout=7200)
        finally:
            try:
                os.remove(_VERIFY_LOCK)
            except Exception:
                pass
        self.stdout.write(self.style.SUCCESS(f'완료 — {len(expired)}개 계정 재인증 시도'))

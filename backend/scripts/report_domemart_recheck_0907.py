"""도매마트 L코드(품절/미확인 31,348건) 재검증 결과 1회성 텔레그램 보고 (2026-09-07 09:00 예약, 사용자요청)."""
import os
import re
import subprocess
import sys

sys.path.insert(0, '/home/rejoice888/Avengers/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db.models import Count
import requests

from apps.cpc.models import LCodeStatus, TelegramConfig, TelegramRecipient

tail = subprocess.run(['tail', '-n', '50', '/tmp/check_domemart_lcodes.log'],
                      capture_output=True, text=True).stdout
lines = [l for l in tail.splitlines() if l.strip()]
last = lines[-1] if lines else '(로그 없음)'
m = re.search(r'(\d[\d,]*)/(\d[\d,]*) 진행 중', last)
done_line = next((l for l in reversed(lines) if l.startswith('완료:')), None)

running = bool(subprocess.run(['pgrep', '-f', 'check_domemart_lcodes'],
                               capture_output=True, text=True).stdout.strip())

dist = {c['status']: c['n'] for c in LCodeStatus.objects.values('status').annotate(n=Count('id'))}

msg = '\U0001f6d2 도매마트 L코드 재검증(품절/미확인 31,348건) - 2026-09-07 09:00 예약보고\n\n'
if m:
    msg += f'진행상황: {m.group(1)}/{m.group(2)}건\n'
if done_line:
    msg += f'{done_line}\n'
msg += f'프로세스 실행중: {"예" if running else "아니오(종료됨)"}\n\n'
msg += (f'현재 LCodeStatus 상태분포:\n'
        f'판매중 {dist.get("in_stock", 0):,} / 품절 {dist.get("soldout", 0):,} / '
        f'미확인 {dist.get("not_found", 0):,}')

config = TelegramConfig.objects.first()
if config and config.bot_token:
    for r in TelegramRecipient.objects.filter(is_active=True):
        try:
            requests.post(f'https://api.telegram.org/bot{config.bot_token}/sendMessage',
                          json={'chat_id': r.chat_id, 'text': msg}, timeout=10)
        except Exception as e:
            print('전송실패:', e)
print(msg)

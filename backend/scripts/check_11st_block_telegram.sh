#!/bin/bash
# 11번가 실제 접속 가능 여부를 확인해 텔레그램으로 알림 (cron: 매시간)
cd /home/rejoice888/Avengers/backend
python3 manage.py shell -c "
import urllib.request
from apps.cpc.eleven_block_guard import _send_telegram_alert
from django.utils import timezone
now = timezone.localtime().strftime('%m-%d %H:%M')
try:
    r=urllib.request.urlopen(urllib.request.Request('https://www.11st.co.kr/',headers={'User-Agent':'Mozilla/5.0'}),timeout=12)
    msg=f'🟢 [11번가 접속체크 {now}]\n접속 정상 (HTTP {r.status}) — IP 차단 풀렸습니다!'
except urllib.error.HTTPError as e:
    msg=f'🟢 [11번가 접속체크 {now}]\n접속 정상 (HTTP {e.code}) — IP 차단 풀렸습니다!'
except Exception as e:
    msg=f'🔴 [11번가 접속체크 {now}]\n아직 접속 불가 ({type(e).__name__}) — IP 차단 지속 중'
_send_telegram_alert(msg)
print(msg)
" >> /tmp/check_11st_block.log 2>&1

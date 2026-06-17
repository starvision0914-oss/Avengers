#!/bin/bash
# adb(폰) 연결 감시 — 죽어있으면 자동 복구해서 OTP SMS 수신이 끊기지 않게 한다.
# cron 5분마다 실행. 폰이 USB로 꽂혀만 있으면 연결을 자동 회복한다.
LOG=/tmp/adb_watchdog.log
export ANDROID_SERIAL=""

dev=$(adb devices 2>/dev/null | grep -wE 'device' | grep -v 'List')
if [ -n "$dev" ]; then
    # 연결 정상 — reverse 터널만 보장
    if ! adb reverse --list 2>/dev/null | grep -q 'tcp:8010'; then
        adb reverse tcp:8010 tcp:8010 >/dev/null 2>&1
        echo "$(date '+%F %T') reverse 재설정" >> $LOG
    fi
    exit 0
fi

# 연결 끊김 — 복구 시도
echo "$(date '+%F %T') 폰 연결 끊김 감지 → 복구 시도" >> $LOG
adb kill-server >/dev/null 2>&1
sleep 1
adb start-server >/dev/null 2>&1
sleep 2
dev=$(adb devices 2>/dev/null | grep -wE 'device' | grep -v 'List')
if [ -n "$dev" ]; then
    adb reverse tcp:8010 tcp:8010 >/dev/null 2>&1
    pm2 restart avengers-sms-poller >/dev/null 2>&1
    echo "$(date '+%F %T') 복구 성공 ($dev) + sms-poller 재시작" >> $LOG
else
    echo "$(date '+%F %T') 복구 실패 — 폰 USB 물리 연결 확인 필요!" >> $LOG
    cd /home/rejoice888/Avengers/backend
    # smsApp 하트비트가 신선하면(앱이 네트워크로 서버와 통신 중) 문자·알림(OTP 포함)은 앱 경로로
    # 정상 수신되므로 adb가 죽어도 긴급경보는 무의미 → 경보 억제(로그만). 5분마다 도배 방지.
    HB_FRESH=$(/usr/bin/python3 -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup()
from apps.cpc.models import SmsDeviceHeartbeat as H
from django.utils import timezone
h=H.objects.order_by('-last_seen_at').first()
print('1' if (h and (timezone.now()-h.last_seen_at).total_seconds() < 600) else '0')
" 2>/dev/null)
    NOW=$(date +%s); LAST=$(cat /tmp/adb_watchdog_last_alert 2>/dev/null || echo 0)
    if [ "$HB_FRESH" = "1" ]; then
        echo "$(date '+%F %T') adb 끊김이나 앱 하트비트 정상 → 문자/OTP 앱경로로 수신 중, 경보 억제" >> $LOG
    elif [ $((NOW - LAST)) -gt 21600 ]; then
        # adb·앱 하트비트 모두 끊긴 진짜 오프라인 — 6시간에 1회만 경보(도배 방지)
        echo "$NOW" > /tmp/adb_watchdog_last_alert
        /usr/bin/python3 -c "
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup()
from apps.cpc import eleven_block_guard as g
g._send_telegram_alert('🚨 [폰 연결 끊김] adb·앱 하트비트 모두 끊김 — 문자/OTP 수신 불가 가능성. 폰 USB·전원·네트워크를 확인하세요.')
" >/dev/null 2>&1
        echo "$(date '+%F %T') 진짜 오프라인 경보 발송(6h 스로틀)" >> $LOG
    else
        echo "$(date '+%F %T') 오프라인이나 6h 스로틀로 경보 생략" >> $LOG
    fi
fi

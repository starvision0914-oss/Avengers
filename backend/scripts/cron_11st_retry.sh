#!/bin/bash
# 11번가 광고비 수집 — 실패 계정 자동 재시도 + 차단 방지
# 18:00~00:00 매시간 실행

LOCKFILE="/tmp/avengers_crawl_chrome.lock"
LOGFILE="/tmp/cron_11st_cost.log"

# 중복 실행 방지
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "$(date) 다른 크롤러 실행 중 (PID=$PID) — 스킵" >> $LOGFILE
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

cd /home/rejoice888/Avengers/backend

echo "" >> $LOGFILE
echo "========== $(date) 11번가 크롤링 시작 ==========" >> $LOGFILE

# 글로벌 차단 중이면 실행하지 않음 (강제 해제 안 함)
BLOCKED=$(/usr/bin/python3 -c "
import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()
from apps.cpc import eleven_block_guard as guard
blocked, remaining, until = guard.is_blocked()
if blocked:
    print(f'BLOCKED:{remaining}')
else:
    print('OK')
" 2>/dev/null)

if echo "$BLOCKED" | grep -q "BLOCKED"; then
    echo "$(date) ⛔ 글로벌 차단 중 — 크롤링 스킵 ($BLOCKED)" >> $LOGFILE
    exit 0
fi

# 크롤링 실행
/usr/bin/python3 manage.py crawl_11st_cost >> $LOGFILE 2>&1

echo "========== $(date) 11번가 크롤링 완료 ==========" >> $LOGFILE

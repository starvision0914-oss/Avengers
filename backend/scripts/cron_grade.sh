#!/bin/bash
LOCKFILE="/tmp/avengers_grade.lock"
if [ -f "$LOCKFILE" ]; then
    PID=$(cut -d'|' -f1 "$LOCKFILE" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then exit 0; fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT
cd /home/rejoice888/Avengers/backend
# 11번가 등급 수집 중지: 인증문자 방지 요청(2026-07-18). 재개 원하면 아래 두 줄 주석 해제.
# echo "$(date) 11번가 등급" >> /tmp/cron_grade.log
# /usr/bin/python3 manage.py crawl_11st_grade >> /tmp/cron_grade.log 2>&1
echo "$(date) 지마켓 등급" >> /tmp/cron_grade.log
/usr/bin/python3 manage.py crawl_gmarket_grade >> /tmp/cron_grade.log 2>&1

#!/bin/bash
LOCKFILE="/tmp/avengers_crawl_chrome.lock"
if [ -f "$LOCKFILE" ]; then
    PID=$(cut -d'|' -f1 "$LOCKFILE" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then exit 0; fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT
cd /home/rejoice888/Avengers/backend
echo "$(date) 11번가 등급" >> /tmp/cron_grade.log
/usr/bin/python3 manage.py crawl_11st_grade >> /tmp/cron_grade.log 2>&1
echo "$(date) 지마켓 등급" >> /tmp/cron_grade.log
/usr/bin/python3 manage.py crawl_gmarket_grade >> /tmp/cron_grade.log 2>&1

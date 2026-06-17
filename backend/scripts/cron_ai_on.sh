#!/bin/bash
LOCKFILE="/tmp/avengers_crawl_chrome_gmarket.lock"
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" 2>/dev/null; then exit 0; fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py run_ai_schedule --action on >> /tmp/cron_ai.log 2>&1

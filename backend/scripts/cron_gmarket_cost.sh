#!/bin/bash
LOCKFILE="/tmp/avengers_crawl_chrome_gmarket.lock"
if [ -f "$LOCKFILE" ]; then
    PID=$(cut -d'|' -f1 "$LOCKFILE" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then
        echo "$(date) 다른 크롤러 실행 중 — 스킵" >> /tmp/cron_gmarket_cost.log
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py crawl_gmarket_cost >> /tmp/cron_gmarket_cost.log 2>&1

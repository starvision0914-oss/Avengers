#!/bin/bash
# 11번가 통합 수집 (로그인 1회 → 오피스 현황 + 광고비)
# Chrome lock으로 지마켓 크롤러와 중복 방지
LOCKFILE="/tmp/avengers_crawl_chrome.lock"
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "$(date) 다른 크롤러 실행 중 (PID=$PID) — 스킵" >> /tmp/cron_11st_all.log
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

cd /home/rejoice888/Avengers/backend
echo "$(date) === 11번가 통합 수집 시작 (오피스+광고비) ===" >> /tmp/cron_11st_all.log
/usr/bin/python3 manage.py crawl_11st_cost >> /tmp/cron_11st_all.log 2>&1
echo "$(date) === 11번가 통합 수집 완료 ===" >> /tmp/cron_11st_all.log

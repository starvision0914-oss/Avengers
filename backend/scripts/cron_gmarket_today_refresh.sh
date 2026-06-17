#!/bin/bash
# 지마켓 오늘 광고비 새로고침(엑셀+판매예치금, gmkt_today.py) — 대시보드 신선도 유지.
# 다른 지마켓 수집(gmkt_*) 실행 중이면 스킵(중복/크롬충돌 방지).
cd /home/rejoice888/Avengers/backend
if pgrep -f 'import crawlers.gmkt_' >/dev/null 2>&1; then
    echo "$(date '+%F %T') 지마켓 수집 실행중 — 스킵" >> /tmp/cron_gmkt_today.log
    exit 0
fi
echo "$(date '+%F %T') 오늘 새로고침 시작" >> /tmp/cron_gmkt_today.log
bash /home/rejoice888/Avengers/backend/scripts/orch_gmkt_today.sh >> /tmp/cron_gmkt_today.log 2>&1
echo "$(date '+%F %T') 오늘 새로고침 완료" >> /tmp/cron_gmkt_today.log

#!/bin/bash
# 11번가 판매상태 야간갱신 — 개선판(계정당 5분 리미트+스킵후 1회재시도+실패시 텔레그램).
# 이미 크롤/오케스트레이터 실행중이면 중복 방지로 스킵.
cd /home/rejoice888/Avengers/backend
if pgrep -f 'orch_11st_status.sh' >/dev/null 2>&1 || pgrep -f 'crawl_11st_products' >/dev/null 2>&1; then
    echo "$(date '+%F %T') 이미 실행중 — 스킵" >> /tmp/cron_11st_status_orch.log
    exit 0
fi
bash /home/rejoice888/Avengers/backend/scripts/orch_11st_status.sh

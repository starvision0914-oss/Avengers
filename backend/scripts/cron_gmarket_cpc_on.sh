#!/bin/bash
# 지마켓 CPC 광고 ON — 평일 08:00. 파워클릭 일반 + 간편(스마트) 모두 ON.
#  직렬화는 run_control 내부 guard 전역락(wait=True)이 처리(크롤과 충돌 시 대기).
cd /home/rejoice888/Avengers/backend
LOG=/tmp/cron_gmkt_cpc_on.log
echo "$(date '+%F %T') === CPC 광고 ON 시작 ===" >> "$LOG"
/usr/bin/python3 manage.py crawl_gmarket_cpc1 on --source schedule >> "$LOG" 2>&1
/usr/bin/python3 manage.py crawl_gmarket_cpc2 on --source schedule >> "$LOG" 2>&1
echo "$(date '+%F %T') === CPC 광고 ON 완료 ===" >> "$LOG"

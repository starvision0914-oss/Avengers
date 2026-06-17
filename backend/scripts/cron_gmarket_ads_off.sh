#!/bin/bash
# 지마켓 광고 17시 OFF — 평일 16:50 시작(25계정 순차라 17:00경 완료).
#  간편(스마트) OFF + AI OFF + 일반(파워클릭) OFF(보험·대부분 이미 OFF).
#  직렬화는 각 run_control 내부 guard 전역락(wait=True)이 처리 → 크롤과 충돌 없음.
cd /home/rejoice888/Avengers/backend
LOG=/tmp/cron_gmkt_ads_off.log
echo "$(date '+%F %T') === 17시 광고 OFF 시작 ===" >> "$LOG"
/usr/bin/python3 manage.py crawl_gmarket_cpc2 off --source schedule >> "$LOG" 2>&1
/usr/bin/python3 manage.py crawl_gmarket_ai_control off --source schedule >> "$LOG" 2>&1
/usr/bin/python3 manage.py crawl_gmarket_cpc1 off --source schedule >> "$LOG" 2>&1
echo "$(date '+%F %T') === 17시 광고 OFF 완료 ===" >> "$LOG"

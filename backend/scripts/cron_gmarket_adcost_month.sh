#!/bin/bash
# 지마켓/옥션 거래내역(광고비) 최근 한달 수집 → DB(22시, 대기형).
# 거래내역이 1~2일 지연 기록되므로 최근 35일을 재수집해 누락/지연분을 보강.
# 다른 지마켓 크롤이 돌면 끝날 때까지 대기(--wait, 스킵 방지).
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
FROM=$(date -d '35 days ago' +%Y-%m-%d)
TO=$(date +%Y-%m-%d)
echo "$(date '+%F %T') 거래내역 월수집 시작 ${FROM}~${TO}" >> /tmp/cron_gmkt_adcost_month.log
/usr/bin/python3 manage.py crawl_gmarket_adcost --from "$FROM" --to "$TO" --wait >> /tmp/cron_gmkt_adcost_month.log 2>&1
echo "$(date '+%F %T') 완료" >> /tmp/cron_gmkt_adcost_month.log

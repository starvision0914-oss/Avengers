#!/bin/bash
# 지마켓/옥션 거래내역(광고비) 수집 → DB(9/11/15/17/18/19/20/22시, 대기형).
# 거래내역이 1~2일 지연 기록되므로, 22시 회차만 최근 35일 전체를 재수집해 누락/지연분을 보강.
# 그 외 시간대는 최근 3일만 훑어 계정당 소요시간을 줄이고(오늘자 반영 목적), 락 경합도 줄인다.
# (2026-07-15: 매회 35일 전체를 훑느라 계정당 ~2분 x 30계정 ≈ 1시간 걸려 하루 대부분을 이 크롤이
#  락을 잡고 있었고, 그 사이 다른 시간별 광고비 크론이 반복 스킵됐던 문제를 이 방식으로 완화.)
# 다른 지마켓 크롤이 돌면 끝날 때까지 대기(--wait, 스킵 방지).
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
if [ "$(date +%H)" = "22" ]; then
    FROM=$(date -d '35 days ago' +%Y-%m-%d)
else
    FROM=$(date -d '3 days ago' +%Y-%m-%d)
fi
TO=$(date +%Y-%m-%d)
echo "$(date '+%F %T') 거래내역 수집 시작 ${FROM}~${TO}" >> /tmp/cron_gmkt_adcost_month.log
/usr/bin/python3 manage.py crawl_gmarket_adcost --from "$FROM" --to "$TO" --wait >> /tmp/cron_gmkt_adcost_month.log 2>&1
echo "$(date '+%F %T') 완료" >> /tmp/cron_gmkt_adcost_month.log

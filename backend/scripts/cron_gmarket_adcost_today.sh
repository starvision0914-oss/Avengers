#!/bin/bash
# 지마켓 거래내역(광고비) '당일 보장 수집' — 다른 크롤 겹치면 대기(스킵 방지).
# 대시보드 광고비가 거래내역 기준이라, 이게 누락되면 어제 광고비가 0으로 뜸 → 매일 보장.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
TODAY=$(date +%Y-%m-%d)
/usr/bin/python3 manage.py crawl_gmarket_adcost --from "$TODAY" --to "$TODAY" --wait >> /tmp/cron_gmkt_adcost_today.log 2>&1

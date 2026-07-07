#!/bin/bash
# 스마트스토어 광고비 시간별 수집 (11:10 / 15:10 / 17:10 / 22:10)
# 11번가/지마켓 정각(0분) 크론과 겹치지 않도록 10분 오프셋.
# 상품/판매통계 재크롤 없이 광고비만 가볍게 갱신.

LOG=/tmp/cron_smartstore_adcost_hourly.log
DJANGO=/home/rejoice888/Avengers/backend

echo "$(date '+%Y-%m-%d %H:%M:%S') ===== 스마트스토어 시간별 광고비 시작 =====" >> "$LOG"

cd "$DJANGO" || exit 1
python3 manage.py crawl_smartstore_adcost >> "$LOG" 2>&1
STATUS=$?

echo "$(date '+%Y-%m-%d %H:%M:%S') ===== 완료 (exit=$STATUS) =====" >> "$LOG"

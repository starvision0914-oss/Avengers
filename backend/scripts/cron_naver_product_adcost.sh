#!/bin/bash
# 네이버 상품별 광고비 수집 (매일 08:30)
# 당월 누적 상품별 CPC/AI 비용 저장

LOG=/tmp/cron_naver_product_adcost.log
DJANGO=/home/rejoice888/Avengers/backend

echo "$(date '+%Y-%m-%d %H:%M:%S') ===== 네이버 상품별 광고비 수집 시작 =====" >> "$LOG"

cd "$DJANGO" || exit 1
python3 manage.py crawl_naver_product_adcost >> "$LOG" 2>&1
STATUS=$?

echo "$(date '+%Y-%m-%d %H:%M:%S') ===== 완료 (exit=$STATUS) =====" >> "$LOG"

#!/bin/bash
# 스마트스토어 상품 + 판매통계 + 광고비 크롤링 (01:00)
# 11번가/지마켓 락과 완전 독립 (/tmp/smartstore_crawl.lock)

LOG=/tmp/cron_smartstore.log
DJANGO=/home/rejoice888/Avengers/backend

echo "$(date '+%Y-%m-%d %H:%M:%S') ===== 스마트스토어 크롤링 시작 =====" >> "$LOG"

cd "$DJANGO" || exit 1
python3 manage.py crawl_smartstore --days 7 >> "$LOG" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') [정리] 크롤 3일+ 누락 상품 DELETED 표시" >> "$LOG"
python3 manage.py mark_smartstore_unavailable >> "$LOG" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') [광고비] 네이버 검색광고 API 수집 시작" >> "$LOG"
python3 manage.py crawl_smartstore_adcost --with-gsheet >> "$LOG" 2>&1
STATUS=$?

echo "$(date '+%Y-%m-%d %H:%M:%S') ===== 완료 (exit=$STATUS) =====" >> "$LOG"

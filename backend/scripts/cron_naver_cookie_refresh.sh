#!/bin/bash
# 네이버 광고센터 쿠키 자동 갱신 (3시간마다)
# NAVER_ADS_AVAILABLE_USER ~4h 만료 방지

LOG=/tmp/cron_naver_cookie_refresh.log
DJANGO=/home/rejoice888/Avengers/backend

echo "$(date '+%Y-%m-%d %H:%M:%S') ===== 네이버 광고 쿠키 갱신 시작 =====" >> "$LOG"

cd "$DJANGO" || exit 1
python3 naver_ads_cookie_refresh.py >> "$LOG" 2>&1
STATUS=$?

echo "$(date '+%Y-%m-%d %H:%M:%S') ===== 완료 (exit=$STATUS) =====" >> "$LOG"

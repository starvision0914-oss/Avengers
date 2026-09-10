#!/bin/bash
# 11번가 AI 캠페인 광고비 수집 — 매일 07:00 (2026-09-10 신규 등록).
# cron_11st_product_daily.sh(07:20)가 같은 날 St11AdofficeCampaign 최신분을 구글시트
# 하단에 덧붙이므로 그보다 먼저 끝나야 한다. 동시실행 방지는 --scheduled로 eleven_block_guard
# 락이 풀릴 때까지 대기(스킵 안 함).
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 11번가 AI 캠페인 수집 시작" >> /tmp/cron_11st_ai.log
/usr/bin/python3 manage.py crawl_11st_ai --scheduled >> /tmp/cron_11st_ai.log 2>&1
echo "$(date '+%F %T') 11번가 AI 캠페인 수집 완료" >> /tmp/cron_11st_ai.log

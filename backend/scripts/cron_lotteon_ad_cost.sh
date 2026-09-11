#!/bin/bash
# 롯데온 광고비(클릭광고+스마트광고) 수집 — 매일 01:20, 최근 7일 갱신(default range).
# cron_lotteon_products.sh(01:00)와 겹치면 guard.preflight(platform='lotteon', wait=True)가
# 끝날 때까지 대기 후 수집(스킵 안 함). 2026-09-11 신규 등록(그동안 크론 미등록으로 07-09 이후 방치).
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 롯데온 광고비 수집 시작" >> /tmp/cron_lotteon_ad_cost.log
/usr/bin/python3 manage.py crawl_lotteon_ad_cost >> /tmp/cron_lotteon_ad_cost.log 2>&1
echo "$(date '+%F %T') 롯데온 광고비 수집 완료" >> /tmp/cron_lotteon_ad_cost.log

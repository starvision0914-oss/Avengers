#!/bin/bash
# 오너클랜 '주간 인기 상품' 다운로드 — 매일 09:00, db저장창고(media/ownerclan_weekly_popular/에 파일만 보관).
# 판매자별 상품이 아닌 사이트 전체 랭킹 정적 리포트라 계정 무관(dlwodb111 고정 사용).
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 오너클랜 주간인기상품 다운로드 시작" >> /tmp/cron_ownerclan_weekly.log
python3 manage.py crawl_ownerclan_weekly_popular >> /tmp/cron_ownerclan_weekly.log 2>&1
echo "$(date '+%F %T') 오너클랜 주간인기상품 다운로드 완료" >> /tmp/cron_ownerclan_weekly.log

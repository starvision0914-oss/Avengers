#!/bin/bash
# 17시 11번가 광고비 발생 체크 — 신선도 무시 강제수집(--force)으로 당일 최신화 후,
# 발생 여부를 텔레그램으로 통지. (일반 17시 cost 크론은 6h 신선도로 스킵될 수 있어 별도 운영)
# 동시실행 방지(락)는 Python preflight(eleven_block_guard 통합 락)가 관리.
cd /home/rejoice888/Avengers/backend

# 이미 크롤 실행중이면 강제수집은 건너뛰고(중복 방지) 현재 데이터로 체크만 발송
RUNNING=$(pgrep -f "manage.py crawl_11st_cost")
if [ -z "$RUNNING" ]; then
    /usr/bin/python3 manage.py crawl_11st_cost --force >> /tmp/cron_11st_cost.log 2>&1
fi
/usr/bin/python3 manage.py notify_11st_adcost_check --label "17시 광고비 체크" >> /tmp/cron_11st_adcost_check.log 2>&1

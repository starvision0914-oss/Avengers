#!/bin/bash
# 나의상품(지마켓/11번가/스마트스토어) W코드 오너클랜 실제 판매상태 순환점검 — 주5일(월~금) 1/5씩, 매일 05:30.
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 오너클랜 상태 순환점검 시작" >> /tmp/cron_ownerclan_status.log
python3 manage.py sync_ownerclan_status >> /tmp/cron_ownerclan_status.log 2>&1
echo "$(date '+%F %T') 오너클랜 상태 순환점검 완료" >> /tmp/cron_ownerclan_status.log

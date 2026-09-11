#!/bin/bash
# 도매마트 예치금+주문상태 현황 수집 — 매일 08:50(2026-09-11 신규등록).
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 도매마트 계정현황 수집 시작" >> /tmp/cron_domemart_info.log
/usr/bin/python3 manage.py crawl_domemart_account_info >> /tmp/cron_domemart_info.log 2>&1
echo "$(date '+%F %T') 도매마트 계정현황 수집 완료" >> /tmp/cron_domemart_info.log

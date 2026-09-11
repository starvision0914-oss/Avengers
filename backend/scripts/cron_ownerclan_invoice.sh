#!/bin/bash
# 오너클랜 '플레이오토 송장 정보' 자동 수집 — 하루 5회(09/11/15/16/18시), 전체계정 순차.
# /owner 대시보드 "주문/배송조회" 섹션에 저장되며, 화면에서 회차(시간)별로 골라 다운로드 가능.
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 오너클랜 송장 자동수집 시작" >> /tmp/cron_ownerclan_invoice.log
python3 manage.py crawl_ownerclan_orders --type invoice >> /tmp/cron_ownerclan_invoice.log 2>&1
echo "$(date '+%F %T') 오너클랜 송장 자동수집 완료" >> /tmp/cron_ownerclan_invoice.log

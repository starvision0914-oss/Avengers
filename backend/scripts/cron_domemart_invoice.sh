#!/bin/bash
# 도매마트 송장정보(받는분휴대폰/배송사/송장번호, 최근 1개월) 자동수집 — 하루 5회
# (09/11/15/16/18시, 오너클랜 송장수집과 동일 시간대, 2026-09-11 신규등록).
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 도매마트 송장정보 수집 시작" >> /tmp/cron_domemart_invoice.log
/usr/bin/python3 manage.py crawl_domemart_invoice >> /tmp/cron_domemart_invoice.log 2>&1
echo "$(date '+%F %T') 도매마트 송장정보 수집 완료" >> /tmp/cron_domemart_invoice.log

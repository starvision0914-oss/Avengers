#!/bin/bash
# 11번가 OTP 인증 갱신 (매일 05:00)
# verify_11st_fast: 쿠키 유효성 체크 → 만료된 것만 Chrome OTP (빠름)
# 전계정 만료 시 Chrome 1개 재사용으로 72개 처리 (~40분)
# 대부분 유효 시 쿠키 체크만 (~2분)

cd /home/rejoice888/Avengers/backend
LOG=/tmp/cron_11st_verify.log

echo "$(date '+%F %T') ===== 11번가 OTP 인증 갱신 시작 =====" >> "$LOG"

pkill -9 -f 'undetected_chromedriver' 2>/dev/null
pkill -9 -f 'chromedriver' 2>/dev/null
pkill -9 -f 'chrome --' 2>/dev/null
sleep 3

/usr/bin/python3 manage.py verify_11st_fast --out /tmp/11st_verify_result.json >> "$LOG" 2>&1

echo "$(date '+%F %T') ===== 11번가 OTP 인증 갱신 완료 =====" >> "$LOG"

#!/bin/bash
# 11번가 만료계정(24h10m+) 실제 OTP 재인증 — 자동화(2026-09-18 신설).
# 기존 "만료계정 자동인증" 버튼은 사람이 직접 눌러야만 동작해서, 아무도 안 누르면
# last_real_otp_at이 며칠씩 방치되는 문제가 실측으로 확인됨(최대 166시간 방치).
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
LOG=/tmp/cron_11st_verify_expired.log
echo "$(date '+%F %T') 만료계정 자동인증 시작" >> "$LOG"
/usr/bin/python3 manage.py cron_verify_11st_expired >> "$LOG" 2>&1
echo "$(date '+%F %T') 만료계정 자동인증 완료" >> "$LOG"

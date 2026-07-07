#!/bin/bash
# 11번가 OTP/쿠키 상태 매일 점검 — 쿠키체크 후 만료된 것만 실제 OTP 인증(빠른 방식)
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py verify_11st_fast >> /tmp/cron_11st_otp_check.log 2>&1

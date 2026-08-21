#!/bin/bash
# 도매마트 L코드 판매중/품절 조회 진행상황 텔레그램 알림 — 1시간마다(사용자 요청, 2026-08-21).
cd /home/rejoice888/Avengers/backend
python3 manage.py notify_lcode_progress >> /tmp/cron_lcode_progress.log 2>&1

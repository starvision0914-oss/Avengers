#!/bin/bash
# L코드 도매마트 조회 워치독 — 10분마다 실행중 여부만 조용히 확인, 멈춰있으면 즉시 재개(알림은 재개시에만).
# 사람 눈에 보이는 진행상황 알림(1시간마다)은 cron_lcode_progress.sh가 별도로 계속 담당.
cd /home/rejoice888/Avengers/backend
python3 manage.py notify_lcode_progress --watchdog >> /tmp/cron_lcode_watchdog.log 2>&1

#!/bin/bash
# 11번가 저녁 시간별 광고비(17~20시) 수집 + 계정별 CPC 증가분 텔레그램.
# 집중관리(is_focused) 45계정만 수집 — 시간별 부담 경감(정기 11·15시는 전계정).
# 충돌방지: crawl_11st_cost 실행 중이면 스킵(중복/IP 방지).
LOG=/tmp/cron_11st_cost_hourly.log
cd /home/rejoice888/Avengers/backend
if pgrep -f "manage.py crawl_11st_cost" >/dev/null 2>&1; then
    echo "$(date '+%F %T') 11번가 광고비 크롤 실행중 — 스킵" >> "$LOG"; exit 0
fi
START=$(date '+%T')
echo "$(date '+%F %T') 11번가 시간별 광고비 수집 시작(집중관리 45)" >> "$LOG"
/usr/bin/python3 manage.py crawl_11st_cost --force --focused >> "$LOG" 2>&1
echo "$(date '+%F %T') CPC 증가분 텔레그램" >> "$LOG"
/usr/bin/python3 manage.py notify_11st_adcost_hourly --always >> "$LOG" 2>&1
echo "$(date '+%F %T') 전계정 크롤 종료 알림" >> "$LOG"
/usr/bin/python3 manage.py notify_crawl_done --platform 11st --started "$START" >> "$LOG" 2>&1
echo "$(date '+%F %T') 완료" >> "$LOG"

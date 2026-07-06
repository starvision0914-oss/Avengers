#!/bin/bash
# 11번가 시간별 광고비(대시보드 수집시간과 동일: 11,15,17,18,20,22시) 수집 + 계정별 CPC 증가분 텔레그램.
# 집중관리(is_focused) 45계정만 수집 — 11·15시는 전계정 크롤(cron_11st_cost.sh)이 이미 돌고 있어
# pgrep 가드로 자동 스킵되고 알림만 그 데이터를 읽어 발송됨.
# 충돌방지: crawl_11st_cost 실행 중이면 "수집"만 스킵(중복/IP 방지) — 텔레그램 알림은
# ElevenCostHistory를 읽기만 하므로 크롤 충돌과 무관하게 매시간 반드시 실행한다.
# (2026-07-06 수정: 예전엔 충돌시 알림까지 통째로 스킵되어 그 시간대 알림 누락됨)
LOG=/tmp/cron_11st_cost_hourly.log
cd /home/rejoice888/Avengers/backend
START=$(date '+%T')
if pgrep -f "manage.py crawl_11st_cost" >/dev/null 2>&1; then
    echo "$(date '+%F %T') 11번가 광고비 크롤 실행중 — 수집만 스킵(알림은 진행)" >> "$LOG"
else
    echo "$(date '+%F %T') 11번가 시간별 광고비 수집 시작(집중관리 45)" >> "$LOG"
    /usr/bin/python3 manage.py crawl_11st_cost --force --focused >> "$LOG" 2>&1
fi
echo "$(date '+%F %T') CPC 증가분 텔레그램" >> "$LOG"
/usr/bin/python3 manage.py notify_11st_adcost_hourly --always >> "$LOG" 2>&1
echo "$(date '+%F %T') 전계정 크롤 종료 알림" >> "$LOG"
/usr/bin/python3 manage.py notify_crawl_done --platform 11st --started "$START" >> "$LOG" 2>&1
echo "$(date '+%F %T') 완료" >> "$LOG"

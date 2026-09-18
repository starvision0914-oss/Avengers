#!/bin/bash
# 지마켓 AI 광고 상태 크롤링(09/12/18시, 평일).
# 기존엔 전역락이 잡혀있으면 조용히 exit 0(로그 한 줄도 안 남김)하는 구조라, 다른 지마켓
# 작업들에 락이 거의 항상 잡혀있어 9일 내내 이 크론이 사실상 안 돈 채로 방치됐던 문제
# (2026-09-18 발견) — 다른 광고크론들과 동일하게 강제선점/재개 방식으로 교체.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
LOG=/tmp/cron_gmarket_ai.log

echo "$(date '+%F %T') 지마켓 AI 상태 크롤 시작(강제선점)" >> "$LOG"
/usr/bin/python3 manage.py gmarket_ad_priority_preempt >> "$LOG" 2>&1
/usr/bin/python3 manage.py crawl_gmarket_ai >> "$LOG" 2>&1
/usr/bin/python3 manage.py gmarket_resume_preempted >> "$LOG" 2>&1
echo "$(date '+%F %T') 지마켓 AI 상태 크롤 완료" >> "$LOG"

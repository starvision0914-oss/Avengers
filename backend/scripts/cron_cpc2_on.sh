#!/bin/bash
# 신규광고센터 ON + 간편+일반광고 ON 통합(08:00, 정시실행 최우선 — 2026-09-14 사용자 요청).
# 원래 신규광고센터ON(08:00 별도크론)과 간편광고ON(08:10 별도크론)이 10분 간격으로 따로 돌면서
# 08:10 강제선점이 아직 실행 중이던 08:00 작업을 그대로 죽여버리는 충돌이 반복됨(2026-09-16 발견) —
# 하나의 크론으로 합쳐 순차실행함으로써 서로 죽일 여지 자체를 없앰.
cd /home/rejoice888/Avengers/backend
SKIP_DATE=$(cat /tmp/avengers_gmarket_ad_on_skip 2>/dev/null)
if [ -n "$SKIP_DATE" ] && [ "$SKIP_DATE" = "$(date +%F)" ]; then
    echo "$(date) 오늘($SKIP_DATE) 광고ON 스킵설정 — 종료" >> /tmp/cron_gmarket_ad_on_skip.log
    exit 0
fi
export PATH="/home/rejoice888/.local/bin:$PATH"
LOG=/tmp/cron_cpc2.log

echo "$(date '+%F %T') [1/2] 신규광고센터 ON 시작" >> "$LOG"
/usr/bin/python3 manage.py crawl_gmarket_new_adcenter on --source schedule >> /tmp/cron_newad.log 2>&1
echo "$(date '+%F %T') [1/2] 신규광고센터 ON 완료" >> "$LOG"

echo "$(date '+%F %T') [2/2] 간편+일반광고 ON 시작(강제선점)" >> "$LOG"
/usr/bin/python3 manage.py gmarket_ad_priority_preempt >> "$LOG" 2>&1
/usr/bin/python3 manage.py crawl_gmarket_cpc2 on --source schedule >> "$LOG" 2>&1
/usr/bin/python3 manage.py gmarket_resume_preempted >> "$LOG" 2>&1
echo "$(date '+%F %T') [2/2] 간편+일반광고 ON 완료" >> "$LOG"

#!/bin/bash
# 11번가 광고비 수집 — 집중관리(is_focused) 45계정만 (--focused)
# (정기 11·15시 + 저녁 시간별 모두 45계정만 수집)
# 특정 날짜 1회 스킵: /tmp/avengers_11st_cost_skip 의 날짜와 오늘이 같으면 종료 (내일은 자동 정상)
SKIP_DATE=$(cat /tmp/avengers_11st_cost_skip 2>/dev/null)
if [ -n "$SKIP_DATE" ] && [ "$SKIP_DATE" = "$(date +%F)" ]; then
    echo "$(date) 오늘($SKIP_DATE) 스킵 설정 — 종료" >> /tmp/cron_11st_cost.log
    exit 0
fi
# 중복/행(hang) 누적 방지: 이미 도는 크롤이 있으면 — 90분 초과(행 의심)면 강제정리, 아니면 이번 회차 스킵.
RUNNING=$(pgrep -f "manage.py crawl_11st_cost")
if [ -n "$RUNNING" ]; then
    for pid in $RUNNING; do
        ET=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
        if [ -n "$ET" ] && [ "$ET" -gt 5400 ]; then
            echo "$(date) 행 의심 크롤(pid $pid, ${ET}s) 강제정리" >> /tmp/cron_11st_cost.log
            kill -9 "$pid" 2>/dev/null
            pkill -9 -f chromedriver 2>/dev/null
        else
            echo "$(date) 크롤 이미 실행중(pid $pid, ${ET}s) — 이번 회차 스킵" >> /tmp/cron_11st_cost.log
            exit 0
        fi
    done
fi
# 동시실행 방지(락)는 Python preflight(eleven_block_guard, 통합 락)가 관리.
# --scheduled: 다른 크롤 실행 중이면 건너뛰지 않고 락이 풀릴 때까지 대기 후 반드시 실행, 문제 시 텔레그램 알림.
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py crawl_11st_cost --scheduled --focused >> /tmp/cron_11st_cost.log 2>&1

#!/bin/bash
# 지마켓 시간별 광고비(09~19시) 수집 + 계정별 증가분 텔레그램.
# 직전 스냅샷 대비 CPC/AI 증가분 + 현재 누적을 텔레그램 발송.
# 충돌방지: ① 광고비 파일락  ② today_refresh/17check(gmkt_*) pgrep — 둘 중 하나라도 돌면 스킵.
LOCKFILE="/tmp/avengers_crawl_chrome_gmarket.lock"
LOG=/tmp/cron_gmkt_cost_hourly.log
cd /home/rejoice888/Avengers/backend

# ② 다른 지마켓 수집(gmkt_today / 상품별광고비 / 키워드) 실행 중이면 스킵
# 실제 python 크롤만 감지(manage.py 실행형). 'while pgrep …' 디버그/모니터 셸 오탐 방지(2026-06-17 수정).
if pgrep -f 'import crawlers.gmkt_' >/dev/null 2>&1 \
   || pgrep -f 'manage.py crawl_gmarket_ad_report' >/dev/null 2>&1 \
   || pgrep -f 'manage.py crawl_gmarket_keywords' >/dev/null 2>&1 \
   || pgrep -f 'manage.py crawl_gmarket_grade' >/dev/null 2>&1; then
    echo "$(date '+%F %T') 다른 지마켓 크롤 실행중 — 스킵" >> "$LOG"; exit 0
fi
# ① 광고비 파일락 점유 중이면 스킵
if [ -f "$LOCKFILE" ]; then
    PID=$(cut -d'|' -f1 "$LOCKFILE" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then
        echo "$(date '+%F %T') 광고비 크롤 실행중 — 스킵" >> "$LOG"; exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

START=$(date '+%T')
echo "$(date '+%F %T') 시간별 광고비 수집 시작" >> "$LOG"
/usr/bin/python3 manage.py crawl_gmarket_cost >> "$LOG" 2>&1
echo "$(date '+%F %T') 증가분 텔레그램 발송" >> "$LOG"
/usr/bin/python3 manage.py notify_gmarket_adcost_hourly >> "$LOG" 2>&1
echo "$(date '+%F %T') 전계정 크롤 종료 알림" >> "$LOG"
/usr/bin/python3 manage.py notify_crawl_done --platform gmarket --started "$START" >> "$LOG" 2>&1
echo "$(date '+%F %T') 완료" >> "$LOG"

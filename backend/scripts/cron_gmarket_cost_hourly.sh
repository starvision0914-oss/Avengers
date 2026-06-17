#!/bin/bash
# 지마켓 시간별 광고비(09~19시) 수집 + 계정별 증가분 텔레그램.
# 직전 스냅샷 대비 CPC/AI 증가분 + 현재 누적을 텔레그램 발송.
# 충돌방지: 다른 지마켓 크롤/광고비 락이 돌면 끝날 때까지 대기 후 수집(스킵 안 함, 최대 50분).
LOCKFILE="/tmp/avengers_crawl_chrome_gmarket.lock"
LOG=/tmp/cron_gmkt_cost_hourly.log
cd /home/rejoice888/Avengers/backend

# 다른 지마켓 크롤(통합/키워드/today)이나 광고비 락이 잡혀 있으면 — 스킵하지 않고
# 끝날 때까지 대기 후 수집(스냅샷은 누적값이라 늦게라도 그 시간대까지 다 잡힘).
# 최대 50분 대기(다음 정시 전까지). 실제 python 크롤만 감지(셸 오탐 방지).
_busy() {
    pgrep -f 'import crawlers.gmkt_' >/dev/null 2>&1 && return 0
    pgrep -f 'manage.py crawl_gmarket_ad_report' >/dev/null 2>&1 && return 0
    pgrep -f 'manage.py crawl_gmarket_keywords' >/dev/null 2>&1 && return 0
    pgrep -f 'manage.py crawl_gmarket_grade' >/dev/null 2>&1 && return 0
    if [ -f "$LOCKFILE" ]; then
        local P=$(cut -d'|' -f1 "$LOCKFILE" 2>/dev/null)
        kill -0 "$P" 2>/dev/null && return 0
    fi
    return 1
}
WAITED=0; MAXWAIT=3000
while _busy; do
    [ "$WAITED" -eq 0 ] && echo "$(date '+%F %T') 다른 크롤 실행중 — 끝날 때까지 대기" >> "$LOG"
    if [ "$WAITED" -ge "$MAXWAIT" ]; then
        echo "$(date '+%F %T') 대기 ${MAXWAIT}s 초과 — 이번 회차 스킵" >> "$LOG"; exit 0
    fi
    sleep 60; WAITED=$((WAITED + 60))
done
[ "$WAITED" -gt 0 ] && echo "$(date '+%F %T') 다른 크롤 종료 확인(대기 ${WAITED}s) — 수집 진행" >> "$LOG"
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

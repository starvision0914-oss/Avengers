#!/bin/bash
# 지마켓 시간별 광고비(09~21시) 수집 + 계정별 증가분 텔레그램.
# 직전 스냅샷 대비 CPC/AI 증가분 + 현재 누적을 텔레그램 발송.
# 16~20시는 정시실행 최우선(2026-08-27 사용자 요청): 다른 지마켓 작업이 돌고 있으면
# 강제종료 후 즉시 수집, 끝나면 강제종료됐던 작업 재개.
# 그 외 시간대는 기존대로 — 다른 지마켓 크롤이 돌면 끝날 때까지 대기 후 수집(최대 50분, 스킵 안 함).
LOCKFILE="/tmp/avengers_crawl_chrome_gmarket.lock"
LOG=/tmp/cron_gmkt_cost_hourly.log
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"

HOUR=$(date '+%H')
if [ "$HOUR" -ge 16 ] && [ "$HOUR" -le 20 ]; then
    echo "$(date '+%F %T') ${HOUR}시 — 정시실행 최우선(강제선점)" >> "$LOG"
    /usr/bin/python3 manage.py gmarket_ad_priority_preempt >> "$LOG" 2>&1
else
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

# (2026-08-31) 16~19시에 재개하면 바로 다음시각 강제선점에 또 죽어 매시간
# "재개→즉시재종료"만 반복하며 adcost_month가 며칠째 사실상 수집을 못 했다(주말 데이터 누락 원인).
# 우선순위 창(16~20시)이 완전히 끝나는 20시 회차 이후에만 1회 재개해 방해받지 않고 끝까지 돌게 한다.
if [ "$HOUR" -eq 20 ]; then
    /usr/bin/python3 manage.py gmarket_resume_preempted >> "$LOG" 2>&1
fi

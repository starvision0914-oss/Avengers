#!/bin/bash
# 11번가 상품코드별 ROAS (adoffice 다운로드보고서) — 최근 한달 누적관리, 매일 1회.
# Chrome lock 공유로 광고비/다른 크롤러와 겹침 방지.
cd /home/rejoice888/Avengers/backend
# 정규크론 우선선점(2026-09-11 사용자 요청) — 락을 쥔 다른(전략가드 등) 작업을 먼저 정리.
/usr/bin/python3 manage.py st11_priority_preempt >> /tmp/cron_11st_product_roas.log 2>&1
LOCKFILE="/tmp/avengers_crawl_chrome.lock"
if [ -f "$LOCKFILE" ]; then
    PID=$(cut -d'|' -f1 "$LOCKFILE" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then
        echo "$(date) 다른 크롤러 실행 중 (PID=$PID) — 스킵" >> /tmp/cron_11st_product_roas.log
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT
# 인자 없음 = 활성 11번가 전체, 기간 자동(최근 한달, 어제 기준 30일)
/usr/bin/python3 manage.py crawl_11st_product_roas >> /tmp/cron_11st_product_roas.log 2>&1
/usr/bin/python3 manage.py st11_resume_preempted >> /tmp/cron_11st_product_roas.log 2>&1

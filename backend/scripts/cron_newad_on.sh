#!/bin/bash
# 지마켓 신규광고센터(adcenter.esmplus.com) ON — 예약 계정만 대상(--source schedule). 동시실행은 python guard가 대기.
cd /home/rejoice888/Avengers/backend
SKIP_DATE=$(cat /tmp/avengers_gmarket_ad_on_skip 2>/dev/null)
if [ -n "$SKIP_DATE" ] && [ "$SKIP_DATE" = "$(date +%F)" ]; then
    echo "$(date) 오늘($SKIP_DATE) 광고ON 스킵설정 — 종료" >> /tmp/cron_gmarket_ad_on_skip.log
    exit 0
fi
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py crawl_gmarket_new_adcenter on --source schedule >> /tmp/cron_newad.log 2>&1

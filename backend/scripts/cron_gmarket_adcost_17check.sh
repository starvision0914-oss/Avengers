#!/bin/bash
# 지마켓 17시 이후 광고비 발생 체크 — 오늘치 강제 새로고침(엑셀) 후, 17시 이후 발생분을 텔레그램 통지.
cd /home/rejoice888/Avengers/backend
# 다른 지마켓 수집 실행중이 아니면 새로고침(최신화)
if ! pgrep -f 'import crawlers.gmkt_' >/dev/null 2>&1; then
    echo "$(date '+%F %T') 17시체크용 새로고침 시작" >> /tmp/cron_gmkt_adcost_check.log
    bash /home/rejoice888/Avengers/backend/scripts/orch_gmkt_today.sh >> /tmp/cron_gmkt_today.log 2>&1
fi
# 17시 이후 발생 광고비 텔레그램 알림
/usr/bin/python3 manage.py notify_gmarket_adcost_check --label "17시 광고비 체크" --since-hour 17 >> /tmp/cron_gmkt_adcost_check.log 2>&1

#!/bin/bash
# 1회성: sglobal2(테스트-타사) 2025년(1~12월) 상품별 광고비 크롤 — 7/10 실행 후 자기 자신을 crontab에서 제거.
cd /home/rejoice888/Avengers/backend
LOG=/tmp/oneshot_sglobal2_2025.log
echo "$(date '+%F %T') sglobal2 2025년 상품별 광고비 크롤 — 시작" >> "$LOG"

# 지마켓 락이 풀릴 때까지 대기(최대 60분)
WAITED=0
while [ -f /tmp/avengers_crawl_chrome_gmarket.lock ] && [ "$WAITED" -lt 3600 ]; do
    sleep 30
    WAITED=$((WAITED+30))
done

/usr/bin/python3 manage.py crawl_gmarket_ad_report --eid sglobal2 --year 2025 --months 1-12 >> "$LOG" 2>&1
echo "$(date '+%F %T') sglobal2 2025년 상품별 광고비 크롤 — 완료" >> "$LOG"

# 1회성 — 실행 후 자기 crontab 줄 제거
crontab -l | grep -v 'oneshot_sglobal2_2025.sh' | crontab -
echo "$(date '+%F %T') 1회성 크론 자동 제거 완료" >> "$LOG"

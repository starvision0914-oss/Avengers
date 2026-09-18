#!/bin/bash
# 지마켓 신규광고센터 상품별 광고비 전계정 수집(06:30, 2026-09-18 신설).
# 07:20/08:00 등 다른 지마켓 크론들과 겹치기 전에 실행 — 락 잡혀있으면 wait=True로 순서대기.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
LOG=/tmp/cron_gmarket_newad_product_cost.log

echo "$(date '+%F %T') 지마켓 신규광고센터 상품별 광고비 수집 시작" >> "$LOG"
/usr/bin/python3 manage.py collect_gmarket_newad_product_cost >> "$LOG" 2>&1
echo "$(date '+%F %T') 지마켓 신규광고센터 상품별 광고비 수집 완료" >> "$LOG"

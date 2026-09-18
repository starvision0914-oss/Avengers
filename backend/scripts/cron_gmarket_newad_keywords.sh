#!/bin/bash
# 지마켓 신규광고센터 ROAS 100%+ 상품 키워드 자동 수집(10:30, 2026-09-19 신설).
# 상품별 광고비 수집(09:00 시작)이 끝난 뒤 그날 ROAS로 정확히 뽑히도록 늦게 예약.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
LOG=/tmp/cron_gmarket_newad_keywords.log

echo "$(date '+%F %T') 지마켓 신규광고센터 키워드(ROAS100%+) 수집 시작" >> "$LOG"
/usr/bin/python3 manage.py collect_gmarket_newad_keywords >> "$LOG" 2>&1
echo "$(date '+%F %T') 지마켓 신규광고센터 키워드(ROAS100%+) 수집 완료" >> "$LOG"

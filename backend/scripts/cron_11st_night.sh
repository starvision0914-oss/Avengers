#!/bin/bash
# 11번가 야간 통합(02:00): 판매상태 갱신(전계정, 쿠키워밍) → 완료 즉시 상품코드 보존(체이닝).
# 보존은 반드시 판매상태 갱신이 끝난 뒤 실행 → 항상 '최신 데이터' 스냅샷 보장(동시실행/시각어긋남 방지).
cd /home/rejoice888/Avengers/backend
LOG=/tmp/cron_11st_night.log
echo "$(date '+%F %T') ===== 11번가 야간 통합 시작 =====" >> "$LOG"

# 중복 실행 방지(다른 11번가 상품크롤 진행중이면 스킵)
if pgrep -f 'orch_11st_status.sh' >/dev/null 2>&1 || pgrep -f 'crawl_11st_products' >/dev/null 2>&1; then
    echo "$(date '+%F %T') 이미 실행중 — 스킵" >> "$LOG"
    exit 0
fi

# 1) 판매상태 갱신(전계정 72) — 동시에 전계정 로그인으로 쿠키 워밍(아침 광고비 OTP 회피)
echo "$(date '+%F %T') [1/2] 판매상태 갱신 시작" >> "$LOG"
bash /home/rejoice888/Avengers/backend/scripts/orch_11st_status.sh
echo "$(date '+%F %T') [1/2] 판매상태 갱신 완료" >> "$LOG"

# 2) 상품코드 보존 — 위에서 갱신한 최신 카탈로그 기준 영구 스냅샷
echo "$(date '+%F %T') [2/2] 상품코드 보존 시작" >> "$LOG"
/usr/bin/python3 manage.py archive_product_codes --snapshot >> "$LOG" 2>&1
echo "$(date '+%F %T') [2/2] 상품코드 보존 완료" >> "$LOG"

echo "$(date '+%F %T') ===== 11번가 야간 통합 완료 =====" >> "$LOG"

#!/bin/bash
# L코드(도매마트) 품절/미확인 재조사 — 매주 금요일 10시. 품절·미확인으로 저장된 코드만 다시 조회.
# 이미 L코드 조회(전체/워치독 재개 포함)가 돌고 있으면 겹치지 않도록 건너뛴다.
LOCKFILE=/tmp/avengers_domemart_lcode.lock
LOG=/tmp/check_domemart_lcodes.log
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
if [ -f "$LOCKFILE" ]; then
    P=$(cut -d'|' -f1 "$LOCKFILE" 2>/dev/null)
    if kill -0 "$P" 2>/dev/null; then
        echo "$(date '+%F %T') L코드 조회 실행 중(PID=$P) — 금요일 품절/미확인 재조사 건너뜀" >> "$LOG"
        exit 0
    fi
fi
echo "===== $(date '+%F %T') 금요일 정기 — 품절/미확인 재조사 시작 (--only-status soldout,not_found)" >> "$LOG"
/usr/bin/python3 -u manage.py check_domemart_lcodes --only-status soldout,not_found >> "$LOG" 2>&1

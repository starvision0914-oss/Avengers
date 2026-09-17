#!/bin/bash
# 도매마트 L코드 품절/미확인 상태를 전체 99,703건 대상으로 무한반복 재조회(2026-09-17 사용자요청).
# --recheck-days 0 = 마지막 확인일과 무관하게 전체 코드를 매번 재확인 대상으로 삼음(정상품 포함
# 전수조사) — 특정 상태만 골라서 보면 "정상"이던 상품이 새로 품절돼도 못 잡아내므로 전체를 돈다.
# 한 바퀴(99,703건) 다 돌면 바로 다음 바퀴 시작 — 멈추지 않음.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"

while true; do
    python3 -u manage.py check_domemart_lcodes --recheck-days 0
    sleep 30
done

#!/bin/bash
# 11번가 상품코드별 ROAS 일별 누적 — 매일 09:00, 오늘 제외 최근 7일(7일전~어제) 재수집(upsert).
# 대상: 집중관리(is_focused) 45계정만 (--focused).
# 광고비 집계가 늦게 확정돼도 7일 윈도우 재수집으로 자동 보정. Chrome lock 공유.
# 동시실행 방지(락)는 Python preflight(eleven_block_guard, 통합 락)가 관리 → bash 락 불필요.
cd /home/rejoice888/Avengers/backend
YEST=$(date -d "yesterday" +%F)
DFROM=$(date -d "7 days ago" +%F)
# 통합: 계정당 adoffice 로그인 1회로 상품별 ROAS + 기간별 보고서(구글시트)까지 한 번에 수집.
# (--with-gsheet: 같은 세션에서 기간별 보고서 다운로드 후 계정별 구글시트 업로드. 매월 1일=전월/그외=당월 자동)
/usr/bin/python3 manage.py crawl_11st_product_daily --from "$DFROM" --to "$YEST" --with-gsheet --focused >> /tmp/cron_11st_product_daily.log 2>&1

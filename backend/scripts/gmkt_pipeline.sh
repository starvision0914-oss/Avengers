#!/bin/bash
# 지마켓 순차 파이프라인 — 충돌 방지(동시 아님, 락 직렬화).
# 통합크롤 → 적자OFF → 진단 → 시간별광고비(거래원장) → 시간별 텔레그램.
cd /home/rejoice888/Avengers/backend
exec >> /tmp/gmkt_pipeline.log 2>&1
echo "========== 파이프라인 시작 $(date '+%H:%M:%S') =========="

echo "[1/5] 통합크롤(상품별광고비+키워드+시트, 전계정) 시작 $(date '+%H:%M:%S')"
/usr/bin/python3 manage.py crawl_gmarket_ad_report --with-keywords --with-gsheet
echo "[1/5] 통합크롤 완료 $(date '+%H:%M:%S')"

echo "[2/5] 적자광고 OFF 탐지+텔레그램 $(date '+%H:%M:%S')"
/usr/bin/python3 manage.py gmarket_loss_ad_off
echo "[2/5] 적자OFF 완료 $(date '+%H:%M:%S')"

echo "[3/5] 광고효율 진단+텔레그램 $(date '+%H:%M:%S')"
/usr/bin/python3 manage.py gmarket_ad_diagnose
echo "[3/5] 진단 완료 $(date '+%H:%M:%S')"

echo "[4/5] 시간별 광고비(거래원장+스냅샷, 전계정) 시작 $(date '+%H:%M:%S')"
/usr/bin/python3 manage.py crawl_gmarket_cost
echo "[4/5] 시간별 광고비 완료 $(date '+%H:%M:%S')"

echo "[5/5] 시간별 광고비 증가분 텔레그램 $(date '+%H:%M:%S')"
/usr/bin/python3 manage.py notify_gmarket_adcost_hourly
echo "[5/5] 텔레그램 완료 $(date '+%H:%M:%S')"

echo "========== 파이프라인 완료 $(date '+%H:%M:%S') =========="

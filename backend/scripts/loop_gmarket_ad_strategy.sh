#!/bin/bash
# 옥션광고센터 L코드(도매마트) 광고그룹 전략(노출요일/시간) 스캔+적용 — 무한반복(2026-09-18 사용자요청).
# 계정당 그룹이 수백 개라 한 번에 못 돌리므로 30개씩 나눠 계속 이어서 진행.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"

while true; do
    python3 -u manage.py apply_gmarket_ad_strategy --limit 30
    sleep 30
done

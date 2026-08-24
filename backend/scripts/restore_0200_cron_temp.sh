#!/bin/bash
# [임시 1회성] 8/24 새벽 상품수집을 5시로 미룬 것 원복 — 이 스크립트가 실행되면서
# 자기 자신을 포함한 임시 크론 라인들을 지우고 원래 02:00 스케줄을 되돌려놓는다.
crontab -l | grep -v "임시.*오늘만 5시 이동" | grep -v "restore_0200_cron_temp" > /tmp/crontab_restore_tmp.txt
echo "0 2 * * * /home/rejoice888/Avengers/backend/scripts/cron_gmarket_products.sh  # 지마켓/옥션 상품수집(야간 02:00, 상품수·판매상태 갱신)" >> /tmp/crontab_restore_tmp.txt
echo "0 2 * * * /home/rejoice888/Avengers/backend/scripts/cron_11st_night.sh  # 11번가 야간통합(02:00, 판매상태 전계정+쿠키워밍 → 완료후 상품코드보존 체이닝)" >> /tmp/crontab_restore_tmp.txt
crontab /tmp/crontab_restore_tmp.txt
echo "$(date '+%F %T') 02:00 상품수집 크론 원복 완료" >> /tmp/cron_restore_0200.log

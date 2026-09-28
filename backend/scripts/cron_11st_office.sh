#!/bin/bash
# 11번가 셀러오피스 현황(셀러캐시/셀러포인트/상품수/AI캠페인 상태) 전계정(비활성 포함) 일 1회 수집.
# AI캠페인 열 = '알아서 해주는 AI캠페인 시작' / '1주 무료! 지금 광고 시작' / 'ON으로 설정 변경' 구분용.
# --scheduled: 다른 11번가 크롤이 락 잡고 있으면 끝날 때까지 대기 후 실행. 6h 내 수집분은 자동 스킵.
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py crawl_11st_office --all --scheduled >> /tmp/cron_11st_office.log 2>&1

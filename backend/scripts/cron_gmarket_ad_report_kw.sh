#!/bin/bash
# 지마켓 상품별 광고비(CPC/AI) + ROAS≥200 키워드 + 일자별 구글시트 통합 수집 — 매일 08:00.
# 계정 로그인 1회로 광고비+키워드+일자별시트 모두 수집(IP 절약). 09:00 잔액크롤 전에 끝나도록 08:00 시작.
# 수동 락 만들지 않음: crawl_gmarket_ad_report 내부 guard.preflight가 전역락 자동 관리.
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 통합크롤(상품별광고비+키워드+일자별시트) 시작" >> /tmp/cron_gmkt_adkw.log
/usr/bin/python3 manage.py crawl_gmarket_ad_report --with-keywords --with-gsheet >> /tmp/cron_gmkt_adkw.log 2>&1
echo "$(date '+%F %T') 통합크롤 종료" >> /tmp/cron_gmkt_adkw.log

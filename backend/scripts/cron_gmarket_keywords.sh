#!/bin/bash
# 지마켓 CPC 키워드 수집(ROAS≥200 상품) — 매일 03:30.
# 수동 락 만들지 않음: crawl_gmarket_keywords 내부 guard.preflight가 전역락을 스스로 획득·해제.
# (수동으로 echo $$>락 하면 preflight가 self-오판해 스킵됨 — 주의)
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 지마켓 키워드 수집 시작" >> /tmp/cron_gmkt_keywords.log
/usr/bin/python3 manage.py crawl_gmarket_keywords --roas-min 200 >> /tmp/cron_gmkt_keywords.log 2>&1
echo "$(date '+%F %T') 지마켓 키워드 수집 종료" >> /tmp/cron_gmkt_keywords.log

#!/bin/bash
# 토스쇼핑 파트너스 광고비 수집 — 전일(어제) 확정치 1일 1회
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py crawl_toss_adcost --when=yesterday >> /tmp/cron_toss_adcost.log 2>&1

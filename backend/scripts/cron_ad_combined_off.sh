#!/bin/bash
# 지마켓 광고 통합 제어 (off) — 한 로그인으로 AI+간편 순차. guard 전역락이 동시실행 차단.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py crawl_gmarket_ad_combined --action off >> /tmp/cron_ad_combined.log 2>&1

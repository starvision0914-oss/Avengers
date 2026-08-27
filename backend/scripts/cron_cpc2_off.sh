#!/bin/bash
# 간편광고 OFF(16:22, 정시실행 최우선 — 2026-08-27 사용자 요청).
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py gmarket_ad_priority_preempt >> /tmp/cron_cpc2.log 2>&1
/usr/bin/python3 manage.py crawl_gmarket_cpc2 off --source schedule >> /tmp/cron_cpc2.log 2>&1
/usr/bin/python3 manage.py gmarket_resume_preempted >> /tmp/cron_cpc2.log 2>&1

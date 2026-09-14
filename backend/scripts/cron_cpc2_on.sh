#!/bin/bash
# 간편+일반광고 ON(08:10, 정시실행 최우선 — 2026-09-14 사용자 요청).
# 다른 지마켓 작업이 돌고 있으면 강제종료 후 즉시 ON, 끝나면 강제종료됐던 작업 재개.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py gmarket_ad_priority_preempt >> /tmp/cron_cpc2.log 2>&1
/usr/bin/python3 manage.py crawl_gmarket_cpc2 on --source schedule >> /tmp/cron_cpc2.log 2>&1
/usr/bin/python3 manage.py gmarket_resume_preempted >> /tmp/cron_cpc2.log 2>&1

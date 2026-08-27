#!/bin/bash
# 지마켓 간편+일반광고 전체계정 ON 점검(2026-08-27 사용자 요청) — 17시 이후에만 동작.
# 정시실행 최우선: 다른 지마켓 작업이 돌고 있으면 강제종료 후 즉시 실행, 끝나면 재개.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py gmarket_ad_priority_preempt >> /tmp/cron_gmarket_cpc2_full_sweep.log 2>&1
/usr/bin/python3 -u manage.py check_gmarket_cpc2_full_sweep >> /tmp/cron_gmarket_cpc2_full_sweep.log 2>&1
/usr/bin/python3 manage.py gmarket_resume_preempted >> /tmp/cron_gmarket_cpc2_full_sweep.log 2>&1

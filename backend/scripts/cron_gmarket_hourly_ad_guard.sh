#!/bin/bash
# 지마켓 시간별 광고비 가드(2026-08-27 사용자 요청) — 17~21시 매시간, 직전시간 대비
# 광고비가 늘어난 계정만 간편+일반광고 OFF. crawl_gmarket_cost(정시)가 끝난 뒤 15분 후 실행.
# 정시실행 최우선(2026-08-27 사용자 요청): 다른 지마켓 작업이 돌고 있으면 강제종료 후 즉시 실행,
# 끝나면 강제종료됐던 작업을 재개.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py gmarket_ad_priority_preempt >> /tmp/cron_gmarket_hourly_ad_guard.log 2>&1
/usr/bin/python3 -u manage.py check_gmarket_hourly_ad_guard >> /tmp/cron_gmarket_hourly_ad_guard.log 2>&1
/usr/bin/python3 manage.py gmarket_resume_preempted >> /tmp/cron_gmarket_hourly_ad_guard.log 2>&1

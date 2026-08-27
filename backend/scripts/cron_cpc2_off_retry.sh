#!/bin/bash
# 재시도용 — 16:22 OFF가 다른 광고제어와 겹쳐 '중복 방지'로 스킵된 경우를 위한 안전망.
# (2026-08-27 실측: 16:22 실행이 try_acquire_adcontrol 충돌로 0건 처리되고 그대로 방치돼
#  저녁까지 간편광고가 계속 켜진 채 광고비가 나감 — ON쪽 20:15 재시도(cron_ai_on_retry.sh)엔
#  있었는데 OFF쪽엔 없었던 게 원인)
# run_control()이 계정별로 이미 OFF면 건너뛰므로(멱등) 이미 성공했어도 재실행 안전함.
# 정시실행 최우선(2026-08-27 사용자 요청): 다른 지마켓 작업 강제종료 후 즉시 실행, 끝나면 재개.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py gmarket_ad_priority_preempt >> /tmp/cron_cpc2.log 2>&1
/usr/bin/python3 manage.py crawl_gmarket_cpc2 off --source schedule >> /tmp/cron_cpc2.log 2>&1
/usr/bin/python3 manage.py gmarket_resume_preempted >> /tmp/cron_cpc2.log 2>&1

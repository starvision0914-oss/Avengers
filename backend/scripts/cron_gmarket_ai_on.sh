#!/bin/bash
# 지마켓 AI 광고 ON — 일~목 20:30.
#  AI ON은 익일 적용(StartDate=내일)이라 전일 저녁 실행 → 일ON=월적용 … 목ON=금적용(평일 노출).
#  20:00 마감체크(orch_gmkt_today) 회피 위해 20:30. 분 단위는 익일적용이라 무관.
#  직렬화는 run_control 내부 guard 전역락(wait=True)이 처리.
cd /home/rejoice888/Avengers/backend
LOG=/tmp/cron_gmkt_ai_on.log
echo "$(date '+%F %T') === AI광고 ON(익일적용) 시작 ===" >> "$LOG"
/usr/bin/python3 manage.py crawl_gmarket_ai_control on --source schedule >> "$LOG" 2>&1
echo "$(date '+%F %T') === AI광고 ON 완료 ===" >> "$LOG"

#!/bin/bash
# 지마켓 부가세 연간 누적 수집 (22:20 daily).
# 1월~당월까지 재수집해 누락/지연분 보강.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
FROM=$(date +%Y01)
TO=$(date +%Y%m)
echo "$(date '+%F %T') 지마켓 부가세 수집 시작 ${FROM}~${TO}" >> /tmp/cron_gmkt_vat.log
python3 manage.py crawl_gmarket_vat --start "$FROM" --end "$TO" >> /tmp/cron_gmkt_vat.log 2>&1
echo "$(date '+%F %T') 완료" >> /tmp/cron_gmkt_vat.log

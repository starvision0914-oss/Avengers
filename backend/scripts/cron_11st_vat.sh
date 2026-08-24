#!/bin/bash
# 11번가 부가세 연간 누적 수집 (매달 11일).
# 1월~당월까지 재수집해 누락/지연분 보강.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
FROM=$(date +%Y01)
TO=$(date +%Y%m)
echo "$(date '+%F %T') 11번가 부가세 수집 시작 ${FROM}~${TO}" >> /tmp/cron_11st_vat.log
python3 manage.py crawl_11st_vat --start "$FROM" --end "$TO" >> /tmp/cron_11st_vat.log 2>&1
echo "$(date '+%F %T') 완료" >> /tmp/cron_11st_vat.log

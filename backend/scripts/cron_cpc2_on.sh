#!/bin/bash
# 간편광고 ON — 예약 계정만 대상(--source schedule). 동시실행은 python guard가 대기.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py crawl_gmarket_cpc2 on --source schedule >> /tmp/cron_cpc2.log 2>&1

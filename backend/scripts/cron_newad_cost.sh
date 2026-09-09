#!/bin/bash
# 지마켓 신규광고센터(adcenter.esmplus.com) 캠페인별 광고비용 수집 — 전체 활성계정 대상.
# 동시실행은 python guard(gmarket_newad 락)가 대기/스킵 처리.
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py crawl_gmarket_newad_cost --source schedule >> /tmp/cron_newad_cost.log 2>&1

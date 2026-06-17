#!/bin/bash
# 지마켓 광고 효율 진단(읽기전용) + 텔레그램 — 매일 09:30 (08시 광고비 통합크롤 후)
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py gmarket_ad_diagnose --months 2 --telegram >> /tmp/cron_gmkt_diagnose.log 2>&1

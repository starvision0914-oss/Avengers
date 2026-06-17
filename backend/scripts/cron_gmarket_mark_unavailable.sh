#!/bin/bash
# 지마켓 판매불가(누락) 상태 DB 반영 — 매일 05:30 (02시 상품크롤 종료 후)
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py mark_gmarket_unavailable >> /tmp/cron_gmkt_mark.log 2>&1

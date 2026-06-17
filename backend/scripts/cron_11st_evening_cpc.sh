#!/bin/bash
# 11번가 17시 이후 발생 광고비를 시간당 체크해 텔레그램 알림 (없으면 미발송).
# DB만 읽음(크롤 없음) — 데이터 신선도는 광고비 cost 크론(18/20/22시)에 따름.
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py notify_11st_evening_cpc --after-hour 17 >> /tmp/cron_11st_evening_cpc.log 2>&1

#!/bin/bash
# 지마켓 적자상품 광고 OFF 대상 자동 탐지 + 텔레그램 알림 — 매일 09:15(08:00 통합크롤 09:00 완료 후).
# DB만 읽음(로그인 없음). 실제 OFF는 검증 후 별도 활성화.
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py gmarket_loss_ad_off >> /tmp/cron_gmkt_loss_off.log 2>&1

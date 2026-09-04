#!/bin/bash
# 네이버 상품별 ROAS 실매출 기준 적자상품 자동 광고 OFF — 매일 1회(저녁, 당일 광고비 누적 후)
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py auto_naver_loss_adoff >> /tmp/cron_naver_loss_adoff.log 2>&1

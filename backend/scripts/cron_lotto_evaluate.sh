#!/bin/bash
# 매주 토요일 21시 — 로또 예측 자동 평가 (추첨 ~20:45 직후)
# crontab: 0 21 * * 6 /home/rejoice888/Avengers/backend/scripts/cron_lotto_evaluate.sh
set -u
export PYTHONPATH="/home/rejoice888/.local/lib/python3.12/site-packages"
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py evaluate_lotto >> /tmp/cron_lotto_eval.log 2>&1

#!/bin/bash
# AI 광고 OFF — 동시실행은 python guard(preflight wait=True)가 대기 처리(스킵 아님)
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py run_ai_schedule --action off >> /tmp/cron_ai.log 2>&1

#!/bin/bash
# 재시도용 — 19:33 실행이 락 대기초과로 스킵된 경우를 위한 안전망(이미 성공했으면 즉시 스킵)
# AI 광고 ON — 동시실행은 python guard(preflight wait=True)가 대기 처리(스킵 아님)
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
/usr/bin/python3 manage.py run_ai_schedule --action on >> /tmp/cron_ai_retry.log 2>&1

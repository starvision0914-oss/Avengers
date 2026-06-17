#!/bin/bash
# 계정별 독립 실행 오케스트레이터 — 각 계정마다 크롬 정리 후 독립 프로세스로 수집(타임아웃 격리)
cd /home/rejoice888/Avengers/backend
LOG=/tmp/gmkt_orch.log
: > "$LOG"
# 로그인 계정 목록(서브 제외)
ACCTS=$(/usr/bin/python3 -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from apps.cpc.models import CrawlerAccount as C;print(' '.join(a.login_id for a in C.objects.filter(platform='gmarket',is_active=True) if not (a.gmarket_origin_id and a.gmarket_origin_id!=a.login_id)))" 2>/dev/null)
N=$(echo $ACCTS | wc -w)
echo "[ORCH] 대상 $N계정: $ACCTS" >> "$LOG"
i=0
for a in $ACCTS; do
  i=$((i+1))
  # gmarket 전용 크롬/프로필만 정리(11번가 동시크롤 불침해)
  pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null
  rm -rf /tmp/gmkt_chrome_* 2>/dev/null
  rm -f /tmp/avengers_crawl_chrome_gmarket.lock
  sleep 2
  echo "[ORCH $i/$N] START $a $(date +%H:%M:%S)" >> "$LOG"
  timeout 1200 /usr/bin/python3 -u -c "import crawlers.gmkt_balance_full" "$a" >> "$LOG" 2>&1
  echo "[ORCH $i/$N] DONE $a exit=$? $(date +%H:%M:%S)" >> "$LOG"
done
pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null; rm -rf /tmp/gmkt_chrome_* 2>/dev/null
echo "[ORCH] === ALL DONE $(date +%H:%M:%S) ===" >> "$LOG"

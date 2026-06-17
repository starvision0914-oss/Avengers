#!/bin/bash
# 오늘 지마켓 광고비 — 전 계정 격리실행(하루치라 빠름). 300초 충분.
cd /home/rejoice888/Avengers/backend
LOG=/tmp/gmkt_today_orch.log
: > "$LOG"
ACCTS=$(/usr/bin/python3 -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from apps.cpc.models import CrawlerAccount as C;print(' '.join(a.login_id for a in C.objects.filter(platform='gmarket',is_active=True) if not (a.gmarket_origin_id and a.gmarket_origin_id!=a.login_id)))" 2>/dev/null)
N=$(echo $ACCTS | wc -w)
echo "[ORCH] 오늘 지마켓 $N계정: $ACCTS" >> "$LOG"
i=0
for a in $ACCTS; do
  i=$((i+1))
  pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null
  rm -rf /tmp/gmkt_chrome_* 2>/dev/null
  rm -f /tmp/avengers_crawl_chrome_gmarket.lock
  sleep 2
  echo "[ORCH $i/$N] START $a $(date +%H:%M:%S)" >> "$LOG"
  timeout 300 /usr/bin/python3 -u -c "import crawlers.gmkt_today" "$a" >> "$LOG" 2>&1
  echo "[ORCH $i/$N] DONE $a exit=$? $(date +%H:%M:%S)" >> "$LOG"
done
pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null; rm -rf /tmp/gmkt_chrome_* 2>/dev/null
echo "[ORCH] === ALL DONE $(date +%H:%M:%S) ===" >> "$LOG"

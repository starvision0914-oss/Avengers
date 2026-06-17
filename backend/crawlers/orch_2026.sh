#!/bin/bash
# 2026 지마켓 광고비 — 계정별 독립실행(격리). 6개월/gmarket만이라 600초로 충분.
cd /home/rejoice888/Avengers/backend
LOG=/tmp/gmkt_2026_orch.log
: > "$LOG"
ACCTS=$(/usr/bin/python3 -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from apps.cpc.models import CrawlerAccount as C;print(' '.join(a.login_id for a in C.objects.filter(platform='gmarket',is_active=True) if not (a.gmarket_origin_id and a.gmarket_origin_id!=a.login_id)))" 2>/dev/null)
N=$(echo $ACCTS | wc -w)
echo "[ORCH] 2026 지마켓 대상 $N계정: $ACCTS" >> "$LOG"
i=0
for a in $ACCTS; do
  i=$((i+1))
  pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null
  rm -rf /tmp/gmkt_chrome_* 2>/dev/null
  rm -f /tmp/avengers_crawl_chrome_gmarket.lock
  sleep 2
  echo "[ORCH $i/$N] START $a $(date +%H:%M:%S)" >> "$LOG"
  timeout 600 /usr/bin/python3 -u -c "import crawlers.gmkt_2026" "$a" >> "$LOG" 2>&1
  echo "[ORCH $i/$N] DONE $a exit=$? $(date +%H:%M:%S)" >> "$LOG"
done
pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null; rm -rf /tmp/gmkt_chrome_* 2>/dev/null
echo "[ORCH] === ALL DONE $(date +%H:%M:%S) ===" >> "$LOG"

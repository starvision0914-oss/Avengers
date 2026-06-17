#!/bin/bash
# 로그인 실패한 4계정 2026 지마켓 재시도(격리·600초).
cd /home/rejoice888/Avengers/backend
LOG=/tmp/gmkt_retry4_orch.log
: > "$LOG"
ACCTS="rejoice678 dlwodbs222 rejoice794 tmxkql222"
N=$(echo $ACCTS | wc -w)
echo "[ORCH] 재시도 $N계정: $ACCTS" >> "$LOG"
i=0
for a in $ACCTS; do
  i=$((i+1))
  pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null
  rm -rf /tmp/gmkt_chrome_* 2>/dev/null
  rm -f /tmp/avengers_crawl_chrome_gmarket.lock
  sleep 3
  echo "[ORCH $i/$N] START $a $(date +%H:%M:%S)" >> "$LOG"
  timeout 600 /usr/bin/python3 -u -c "import crawlers.gmkt_2026" "$a" >> "$LOG" 2>&1
  echo "[ORCH $i/$N] DONE $a exit=$? $(date +%H:%M:%S)" >> "$LOG"
done
pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null; rm -rf /tmp/gmkt_chrome_* 2>/dev/null
echo "[ORCH] === ALL DONE $(date +%H:%M:%S) ===" >> "$LOG"

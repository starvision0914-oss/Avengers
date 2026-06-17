#!/bin/bash
# 2026 지마켓 — 절단(월20행)된 22계정만 엑셀 재수집(666/222/234는 이미 정상이라 제외). 격리·600초.
cd /home/rejoice888/Avengers/backend
LOG=/tmp/gmkt_2026_orch.log
: > "$LOG"
ACCTS="rejoice999 tmxkqlwus dlrmsgh012 rejoice444 rejoice987 rejoice321 dlwodb111 rejoice678 rejoice567 rejoice911 dlwodbs222 dlwodbs333 rejoice794 dlwodbs444 dlwoddbs55 dlwodbs666 dlwodb777 dlwodb888 dlwodb999 dlwodb000 tmxkql111 tmxkql222"
N=$(echo $ACCTS | wc -w)
echo "[ORCH] 2026 지마켓 절단계정 재수집 $N개: $ACCTS" >> "$LOG"
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

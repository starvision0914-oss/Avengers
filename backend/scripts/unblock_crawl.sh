#!/bin/bash
# 크롤 막힘 즉시 해제 — 스테일 락/차단상태/고아 프로세스 전부 정리.
# 강제종료(-9)나 크래시 후 "다른 크롤 실행중 / 이미 차단 중"으로 막힐 때 실행.
# 실행중인 정상 크롤은 건드리지 않음(고아 PPID=1만 정리, 락은 죽은 PID만 회수).
self=$$

echo "[unblock] 1) 차단상태 파일(blocked_until) — 스테일이면 제거"
for f in /tmp/avengers_11st_blocked_until /tmp/avengers_gmarket_blocked_until \
         /tmp/avengers_gmarket_b_blocked_until /tmp/avengers_auction_blocked_until; do
  [ -e "$f" ] && echo "   - $f ($(cat "$f" 2>/dev/null))" && rm -f "$f"
done

echo "[unblock] 2) 크롤 락 — 잡은 PID가 죽었으면 회수"
for f in /tmp/avengers_crawl_chrome.lock /tmp/avengers_crawl_chrome_gmarket.lock \
         /tmp/avengers_crawl_chrome_gmarket_b.lock; do
  if [ -e "$f" ]; then
    pid=$(cut -d'|' -f1 "$f" 2>/dev/null)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "   - $f → PID $pid 살아있음(정상 크롤) → 유지"
    else
      echo "   - $f → PID '$pid' 죽음 → 회수" && rm -f "$f"
    fi
  fi
done

echo "[unblock] 3) 고아(PPID=1) chrome/Xvfb/chromedriver 정리"
n=0
for p in $(ps -eo pid,ppid,comm | awk '$2==1 && ($3 ~ /chrome|Xvfb|chromedriver/){print $1}'); do
  [ "$p" != "$self" ] && kill -9 "$p" 2>/dev/null && n=$((n+1))
done
echo "   - 고아 $n개 정리"

echo "[unblock] 완료 — 이제 크롤 재시작 가능"

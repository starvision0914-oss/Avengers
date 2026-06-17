#!/bin/bash
# 고아 브라우저 정리 (A: 누수 예방) — 크롤 락이 비어있을(=실행 중 크롤 없음) 때만
# Xvfb/chromedriver/chrome 잔재를 정리한다. 락이 살아있으면(크롤 실행 중) 아무것도 안 함.
LOCK="/tmp/avengers_crawl_chrome.lock"
if [ -f "$LOCK" ]; then
    PID=$(cut -d'|' -f1 "$LOCK" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        exit 0    # 크롤 실행 중 → 정리하지 않음
    fi
fi
# 실행 중 크롤 없음 → 고아 정리
killed=0
for pat in "Xvfb" "chromedriver" "scoped_dir" "chrome_crashpad"; do
    pkill -9 -f "$pat" 2>/dev/null && killed=1
done
# 죽은 락 파일 회수
[ -f "$LOCK" ] && rm -f "$LOCK"
exit 0

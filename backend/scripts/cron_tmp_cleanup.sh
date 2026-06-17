#!/bin/bash
# 임시파일 자동정리 — 다운로드 엑셀/오래된 크롬프로필/로그 누적 방지(디스크 보호).
find /tmp/avengers_11st_downloads /tmp/avengers_11st_product_downloads /tmp/avengers_downloads \
     /tmp/gmkt_*_xl /tmp/gmkt_auc_*_xl /tmp/diag_*_xl -type f -mmin +360 -delete 2>/dev/null
find /tmp -maxdepth 1 -name 'org.chromium.*' -mmin +180 -exec rm -rf {} + 2>/dev/null
find /tmp -maxdepth 1 \( -name 'st_one_*.log' -o -name 'gmkt_chrome_*' \) -mmin +360 -exec rm -rf {} + 2>/dev/null
# 고아 chrome/Xvfb/chromedriver(부모 죽음) 정리
for p in $(ps -eo pid,ppid,comm | awk '$2==1 && ($3 ~ /chrome|Xvfb|chromedriver/){print $1}'); do kill -9 $p 2>/dev/null; done

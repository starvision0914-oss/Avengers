#!/bin/bash
# 롯데온 나의상품 수집(LotteonMyProduct) — 판매자센터 세션토큰 방식(soapi).
# 다른 롯데온 크롤(광고비/부가세)과 겹치면 guard.preflight(wait=True)가 끝날 때까지 대기 후 수집(스킵 안 함).
cd /home/rejoice888/Avengers/backend
echo "$(date '+%F %T') 롯데온 상품수집 시작" >> /tmp/cron_lotteon_products.log
/usr/bin/python3 manage.py crawl_lotteon_products >> /tmp/cron_lotteon_products.log 2>&1
echo "$(date '+%F %T') 롯데온 상품수집 완료" >> /tmp/cron_lotteon_products.log

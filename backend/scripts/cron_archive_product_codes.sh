#!/bin/bash
# 상품번호→판매자코드 영구 보존 — 매일 카탈로그 스냅샷(삭제 전에 코드 보관).
# 나의상품 수집(지마켓 02:00 / 11번가 01:00) 이후 03:00 실행.
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py archive_product_codes --snapshot >> /tmp/cron_archive_codes.log 2>&1

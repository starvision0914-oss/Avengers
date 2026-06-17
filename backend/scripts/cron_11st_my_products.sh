#!/bin/bash
# 11번가 나의상품(판매중/판매중지/품절/판매금지) 상태 정기 동기화 — api_key 보유 전체 계정.
# 적자판단·삭제의 status 정확도 유지용. OpenAPI 기반(브라우저 불필요).
# 동시실행 방지(락)는 Python preflight(eleven_block_guard, 통합 락)가 관리 → bash 락 불필요.
cd /home/rejoice888/Avengers/backend
/usr/bin/python3 manage.py sync_eleven_my_products --api-all >> /tmp/cron_11st_my_products.log 2>&1

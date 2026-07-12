---
name: project-gmarket-adcost-collected-at-gotcha
description: gmarket_product_adcost/keyword_report 테이블 collected_at 단순 날짜그룹핑 시 가짜 결측일 오판 함정
metadata: 
  node_type: memory
  type: project
  originSessionId: 88045d6c-b9b8-4d0c-a791-3652c19433ed
---

GmarketProductAdCost/GmarketKeywordReport는 (login_id, ad_type, product_no, year, month) 유니크 → 매일 크롤 시 해당 (login_id, ad_type, year, month) 범위를 삭제 후 재삽입한다. 따라서 **당월(예: 2026-07) 데이터는 항상 "가장 최근 크롤일"의 collected_at만 남고, 그 이전 날짜의 collected_at은 사라진다** — 이게 정상 설계다.

**Why:** 2026-07-12 지마켓/11번가 7월 크롤 진단 중, `collected_at >= '2026-07-01'`로 단순 DATE 그룹핑했더니 7/3~7/11 구간이 통째로 비어있어 "9일간 크롤 중단"으로 오판할 뻔했다. 실제로는 7/1~7/2에 찍힌 대량 row가 2025년 전체+2026년 1~6월 **과거월 백필**이었고, 당월(2026-07, year/month 필드) 데이터는 매일 delete+reinsert되어 조회 시점 기준 "가장 최근 1일치"만 존재하는 게 정상이었다. cron 로그(`/tmp/cron_gmkt_adkw.log`)엔 매일 정상 시작/종료 기록이 있었고, 계정별 GROUP BY로 재확인하니 전 계정이 최신일자로 정상 갱신돼 있었다.

**How to apply:** 이 두 테이블(또는 유사하게 "당월 범위 delete+reinsert" 패턴을 쓰는 테이블)의 크롤 정상여부를 진단할 땐 `collected_at` 날짜별 COUNT만 보지 말고, (1) `year`/`month` 필드까지 함께 그룹핑해 당월 데이터인지 백필인지 구분하고, (2) cron 로그의 시작/종료 기록과 계정별 MAX(collected_at)로 교차검증할 것. 관련: [[project_11st_cost_partial_loss]] (비슷하게 range-delete 재삽입 패턴이라 유실 위험 있는 다른 테이블).

---
name: project_gmarket_dashboard_cost_column
description: "지마켓 대시보드에 \"구매가\" 항목 추가(2026-09-10) — 11번가와 동일한 역산 방식"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4c6cd55d-0535-40f3-8d75-3377621bd2b2
  modified: 2026-09-09T23:10:05.338Z
---

지마켓 대시보드(`GmarketDashboardView`, `GmarketDashboard.tsx`)에 계정별/합계 "구매가" 컬럼을 추가. `cost = revenue - profit`로 계산 — [[project_eleven_purchase_cost]]의 11번가 대시보드와 동일한 역산 방식 채택(SalesRecord 기간 매출·순수익 기반).

**Why:** `GmarketMyProduct.purchase_cost`(상품 카탈로그 원가, [[project_gmarket_esm_products]])도 있었지만 이는 "현재 등록상품 재고성 원가"라 대시보드가 보여주는 기간별 매출/순수익과 성격이 달라 제외. 11번가 방식이 기존 코드 구조·의미와 정합.
**How to apply:** 지마켓/11번가 대시보드의 "구매가"는 항상 매출-순수익 역산값이며, 상품 단위 `purchase_cost`(ownerclan market_price 매칭)와는 다른 지표임을 혼동하지 말 것.

---
name: project_gmarket_esm_order_endpoint
description: ESM 주문/배송 직접크롤 엔드포인트 — Home/v2/new-order 안의 post-tx.esmplus.com iframe(JSON API). 샵마인 불필요
metadata: 
  node_type: memory
  type: project
  originSessionId: e6d44da8-ed92-4870-82a7-b8f14310a58c
---

지마켓/옥션 ESM 주문(판매실적·배송상태)을 샵마인 없이 직접 크롤 가능. 캡처 확정(2026-06-12, crawlers/diag_esm_orders.py 읽기전용, dlrmsgh012).

- 주문관리 페이지 = `www.esmplus.com/Home/v2/new-order`
- 실제 데이터 iframe = **`https://post-tx.esmplus.com/shipping/new-order`** (현대식 JSON-API 마이크로프론트엔드)
- 크롤 방식 = 상품크롤(`item.esmplus.com` iframe → `/api/ea/goods/search` 동일오리진 fetch)과 **동일 패턴**: ESM PLUS 로그인(쿠키재사용) → new-order 진입 → post-tx iframe 전환 → 내부 주문조회 API 상태별 호출(또는 엑셀다운).
- 주문상태 버킷(네비 dashboardKey): `todayNewOrderCount`(신규주문) `todaySendCount`(오늘발송) `starOrderCount`(스타배송) `transDueDateCount`(정산예정).
- 정산상태(정산지연 등)는 별도 — 이미 크롤 중인 `www.esmplus.com/Member/Settle/GmktSellBalanceManagement`(옥션=IacSellBalanceManagement)와 결합.
- 추측 라우트(order-manage/delivery-manage/order)는 가짜(홈셸만 뜸). 진짜는 new-order.

**미완**: post-tx iframe 내부 주문조회 API 정확한 URL/파라미터(상태필터값)는 iframe 컨텍스트 진입해 추가 캡처 필요(다음 읽기전용 단계).

**원가 주의**: ESM은 판매금액·수수료·정산금액은 주지만 매입원가(SalesRecord.cost) 없음 → 순익계산은 위탁/도매 데이터 보강 필요. 공유ESM 1로그인=복수 서브 seller_id 섞여나옴(seller_id별 분리 필요, [[project_gmarket_esm_groups]] [[project_11st_sales_match_global]] 맥락). [[project_gmarket_esm_products]] [[feedback_crawling_rule]] 준수.

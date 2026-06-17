---
name: project_sales_revenue_def
description: "매출 데이터 정의 - SalesRecord.total_price=정산받는금액(엑셀 컬럼 직접), 11번가 대시보드는 platform 필터 필수"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9cf8d0c5-70a3-44cf-8a41-52304540e393
---

매출데이터(SalesRecord) 컬럼 의미 (2026-06-07 원본 엑셀로 확정):

- **total_price = 정산받는금액** — 업로드 시 엑셀의 `정산받는금액` 컬럼을 그대로 저장(apps/sales/views.py). **이미 수수료가 차감된 순매출**이므로 여기서 commission을 또 빼면 안 됨(이중차감 실수 주의).
- **net_profit = total_price − cost = 정산받는금액 − 구매가** (상품순익). 구매가(cost)는 엑셀 `판매사 주문관리 메모` 컬럼.
- **unit_price = 판매가**(리스팅가, gross), **commission = 마켓수수료**(별도 참고용).
- 대시보드 순수익 = 상품순익(net_profit) − 광고비(CPC).
- **플랫폼 분류**: 엑셀 `쇼핑몰` 컬럼(`01.지마켓`/`02.옥션`/`03.11번가`)이 기준 → 11st/gmarket/auction. 11번가 대시보드는 반드시 `platform='11st'`만 집계(안 하면 전 쇼핑몰 합산되어 부풀려짐).
- **order_date = 결제일시**.
- 셀러 조인: SalesRecord.seller.seller_name == CrawlerAccount.seller_name.

주의: 업로드가 과거에 누적(append)이라 같은 파일을 여러 번 올려 중복 적재됨(11번가 동일행 최대 32회 중복 발견). 2026-06-07 업로드를 (platform, 날짜범위) 기준 delete-insert(idempotent)로 수정함. 재적재 시 깨끗이 덮어씀. [[feedback_crawling_rule]]

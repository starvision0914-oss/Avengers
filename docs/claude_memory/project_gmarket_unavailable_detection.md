---
name: project_gmarket_unavailable_detection
description: 지마켓 판매불가 상품이 비고에 판매중으로 박제되던 문제 — 누락=판매불가 탐지로 해결
metadata: 
  node_type: memory
  type: project
  originSessionId: e76d08ca-b676-492c-8ef3-735797020404
---

지마켓 **판매불가 상품은 goods/search API(crawl_gmarket_products가 쓰는)에서 통째로 제외**된다. sellStatus 코드는 11(판매중)/21/22(판매중지)뿐이고 25(판매불가)는 0건. 그래서 판매불가가 된 상품은 크롤에서 안 잡혀 **마지막 "판매중" 스냅샷이 영구 박제**됨(예: 4525942554는 06-12에 멈춤).

**해결(2026-06-17)**: 누락=판매불가 규칙. `_gmarket_realsales`(views.py)에서 상품 synced_at이 그 계정 최신 크롤보다 12h+ 이전이면 status='판매불가'로 표시. DB엔 `mark_gmarket_unavailable` 명령으로 영구 반영(계정별 최신크롤 기준이라 부분크롤에도 안전). 오판 검증: 플래깅된 18,526개 중 1회누락(<24h)=0%, 95%가 4일+ 연속누락 = 진짜 드롭.

적자리스트(2,447개) 재조사: 77.6%가 실은 판매불가였음. 판매불가 광고비는 "지금 새는 돈"이 아님 — 판매불가되면 G마켓이 노출 끊어 광고비 자연감소(641만→85만). [[project_gmarket_product_status]]

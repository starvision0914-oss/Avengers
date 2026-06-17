---
name: project_gmarket_product_status
description: "지마켓 상품상태(비고) 출처·코드매핑. GmarketMyProduct.status_type은 코드/한글 혼재, 카탈로그 미존재=삭제"
metadata: 
  node_type: memory
  type: project
  originSessionId: 27de0a9f-0150-4513-bcfb-18f7653ffd2a
---

지마켓 상품 ROAS 출력(CSV export + 상세모달)의 **비고(상품상태)** 컬럼 출처와 매핑.

**출처**: `GmarketMyProduct.status_type` (다리: GmarketProductAdCost.product_no → GmarketMyProduct.product_no, 최신 synced_at 1행). 헬퍼 `_gmarket_realsales`가 status_by_pno도 함께 반환(3-튜플: code_by_pno, real_by_pno, status_by_pno) — 호출부 GmarketProductRoasView/GmarketRoasAccountsView 둘 다 3개 언패킹.

**값이 코드/한글 혼재**(크롤러 버전차): DB 실측 분포 = `'11'`(코드,판매중) 325k, `'판매중'` 248k, `'판매중지'` 1.1k, `'01'` 5, `'판매불가'` 1. crawler `gmarket_product_crawler.py:23` SELL_STATUS는 `21~25`만 매핑해서 `'11'/'01'`이 raw로 저장됨(=ESM sellStatus 11=판매중, 01=판매대기).

**정규화** `_gmkt_status_label(raw, in_catalog)` + `_GMKT_STATUS`(views.py): 11/21→판매중, 22→판매중지, 23→품절, 24→판매종료, 25→판매불가, 한글은 그대로 통과. **카탈로그(MyProduct)에 product_no 없으면 '삭제'**, 빈값은 '미상'. 프론트 `statusColor`(판매중=녹/삭제·판매불가=적/중지·종료·품절=주황).

검증(2026-06, rejoice666): ROAS200%↑ 대상품 전부 판매중, 전체 대상품 판매중900/삭제14. CSV 헤더 끝열 '비고(상품상태)', 모달 끝열 '비고(상태)'(colSpan 12). [[project_gmarket_roas_page]] [[project_11st_myproduct_status_source]]

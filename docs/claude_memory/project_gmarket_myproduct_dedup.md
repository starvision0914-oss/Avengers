---
name: project_gmarket_myproduct_dedup
description: 지마켓/옥션 나의상품(GmarketMyProduct) 중복 정의·중복제외/정렬/계정다운로드 구현
metadata: 
  node_type: memory
  type: project
  originSessionId: ecfd8451-6046-498a-a6e4-32b9cd436ffc
---

지마켓/옥션 **나의 상품** 페이지(`/gmarket-my`, GmarketMyProductsPage.tsx + GmarketMyProductListView).

**중복 정의(2026-06-12 점검)**: 총 460,082행.
- **상품번호(product_no) 기준 중복 0건** (모델 unique=(account,market,product_no), 마켓상품번호는 전역고유).
- **판매자코드(seller_product_code=자체코드) 기준 중복 38,925행**: 같은 자체코드(=같은 상품)가 여러 상품번호/마켓(지마켓+옥션)으로 등록됨. distinct 자체코드 279,778, (account+code) 2행이상 그룹 36,924개.

**구현**:
- 백엔드 GmarketMyProductListView에 `dedup` 파라미터: 같은 (account_id, seller_product_code) 중 Min(id) 1개만 유지(Q(code='')|id__in=keep_ids로 코드없는행 보존). list+export 공통. 중복제외 total=421,157.
- 정렬: 이미 sort/order 파라미터 지원(_GMKT_SORT 매핑). 프론트 헤더 클릭정렬 연결(서버사이드, 전체기준). 정렬가능: market/login_id/product_no/product_name/sale_price/stock_quantity/status_type/seller_product_code.
- 아이디선택(account_id)·해당아이디 다운로드(export가 account_id+dedup 반영)는 기존 존재, 라벨/파일명에 계정명 표시 추가.
- api: fetchGmarketMyProducts(...,sort,order,dedup), exportGmarketMyProducts(...,dedup).

관련: [[project_gmarket_esm_products]](상품수집), [[project_gmarket_roas_page]](판매자코드 매칭).

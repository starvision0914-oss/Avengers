---
name: project_11st_sales_match_global
description: 11번가 상품ROAS 매출 매칭은 판매자코드 전역 기준(계정한정 금지)
metadata: 
  node_type: memory
  type: project
  originSessionId: 8cfc5d0f-21a9-45a7-8307-c0179c4ca099
---

11번가 상품별 ROAS의 매출 매칭은 **판매자코드(product_code) 전역 기준**이어야 한다. 계정한정(`seller__seller_id==광고계정`) 매칭 금지.

**Why:** 같은 상품(같은 판매자코드)을 여러 11번가 계정에 함께 등록하고, 광고는 한 계정에서 집행하지만 매출은 다른 계정에 기록되는 구조가 흔하다. 예: 맥심 화이트골드(코드 3922267) 광고=tmxk24인데 매출=tmxk26; 담라 캔디(코드 WF6AB11) 광고=tmxk26인데 매출=tmxk24·rejoice777 등. 계정한정 매칭 시 매출 0 → 적자 오분류.

**How to apply:** `_eleven_product_rows`(apps/cpc/views.py)의 sales_by_code는 `SalesRecord.filter(platform='11st', product_code__in=codes, 기간)`로 셀러 필터 없이 집계. 상품번호→판매자코드 다리(ElevenMyProduct)도 전역조회(account 필터 제거). 판매자코드 매핑 없는 상품은 매출불명이라 ROAS필터(적자)에서 제외(mapped 플래그).

**판매자코드 접두어 정규화(2026-06-09):** 내상품DB seller_product_code에 `WDM_`(도매)·`auto_` 접두어 붙은 코드가 있는데 매출자료엔 접두어 없는 W코드로 저장됨 → exact 매칭 시 매출 누락→거짓적자(예: starvisi WDM_WFJF6XK 매출 92,221원인데 0). 수정: `_bare_seller_code()`로 WDM_/auto_ 접두어 제거, 매출=원본코드+벗긴코드 합산(set으로 중복방지). **LCE_ 등 다른 접두어는 매출자료에도 있어 벗기면 안 됨 — WDM_/auto_만.** 상품명 매칭은 금지(다른 옵션/상품 오매칭). 실제 판매자코드는 W+6자(7자) 형태. 안전성: 매출 판매자코드 ~1만개 중 상품명 2개이상 1%뿐(옵션 1EA/3EA 차이)이라 코드=상품 1:1.

**적자상품 기준(2026-06-09 확정):** ROAS≤100% + 광고비≥2,000원 + 클릭≥10 (이전 3000/15에서 변경). 분석결과 단가는 영향 미미(2천vs3천 9개차이)·클릭이 핵심레버(15→10시 적자 280→592개, 추가분 97% 매출0). 프론트 St11RoasPage.tsx의 cost_min/clicks_min 3곳 + 안내문구. [[project_sales_revenue_def]] 참고.

**매출 업로드 매칭(2026-06-09):** 쇼핑몰명(이름) 대신 쇼핑몰id(=로그인id=seller_id)로 매칭. apps/sales/views.py 업로드뷰: 값이 11번가 로그인id와 일치하는 컬럼 자동탐지→by_sid 정확매칭(이름은 보조), 없는 SellerAccount 자동생성, 중복제거도 (platform,seller) 기준. 1차 '03.11번가'→플랫폼, 2차 쇼핑몰id→셀러.

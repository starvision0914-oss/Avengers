---
name: reference_naver_ad_account_mapping
description: "네이버광고 별칭계정(rejoice999 등)은 SmartStoreAccount.login_id가 아니라 naver_ad_login_id 필드에 있음 — 검색 함정"
metadata:
  type: reference
  originSessionId: 3a442b17-84db-4700-800a-337d103e410d
  modified: 2026-09-11T02:59:37.597Z
---

사용자가 "rejoice999" 같은 별칭으로 부르는 네이버 검색광고 계정은 `apps.smartstore.models.SmartStoreAccount`의 `login_id`가 아니라 **`naver_ad_login_id` 필드**(광고센터 내부API 쿠키세션 키, `crawlers/naver_ads_cookies.json`의 dict 키와 동일)에 들어있다.

**실측 사례(2026-09-11)**: "rejoice999 계정 네이버 광고 단가 조정" 요청 → `SmartStoreAccount.objects.filter(login_id='rejoice999')`로 찾은 계정(id=6, login_id=`rejoice999@naver.com`)은 **엉뚱한 계정**이었다(네이버광고 API 키 전부 공란, 데이터 0건). 진짜 계정은 **id=7**: `login_id=starvis7783@gmail.com`, `store_name/display_name="아이리스"`, `naver_ad_login_id="rejoice999"`, `naver_ad_account_id="988184"`(billing/광고센터 ad-account ID), `naver_ad_customer_id="2761225"`(공식 NCC API customer ID — access_license/secret_key도 이 레코드에 정상 등록돼 있음).

**Why**: login_id(스토어 가입 이메일)와 naver_ad_login_id(광고주가 편의상 부르는 별칭, 대행사/공유로그인 쿠키 키)가 서로 무관한 값이라 이름이 우연히 같은 다른 계정(id=6)과 헷갈리기 매우 쉽다. 약 20분간 "API 키가 없다"고 오판했던 원인.

**How to apply**: 앞으로 "네이버 [닉네임] 계정" 관련 요청이 오면 `SmartStoreAccount`를 `login_id` 하나로만 필터하지 말고 **`login_id` OR `naver_ad_login_id` OR `store_name` OR `display_name`** 전부 조회해서 어느 필드에 매칭되는지 먼저 확인할 것. naver_ad_account_id(billing용)와 naver_ad_customer_id(공식 API용)도 서로 다른 값이니 혼동 주의.

**캠페인/입찰가 구조(id=7, 2026-09-11 확인)**: 캠페인 3개 중 "2.0↑_251120"(SHOPPING)만 ELIGIBLE(나머지 2개 PAUSED). 활성 캠페인 안 광고그룹 8개 전부 `bidAmt=50`(원, 최저가 수준). **네이버 쇼핑검색광고는 입찰가가 키워드 단위가 아니라 광고그룹(adgroup) 단위**로 설정된다 — 상품소재(ads)는 그룹의 bidAmt를 그대로 따름.

**입찰가 변경 API**: `apps/smartstore/services/naver_search_ad.py`의 `set_adgroup_bid(customer_id, access_license, secret_key, ncc_adgroup_id, bid_amt)` (2026-09-11 신규 추가) — `PUT /ncc/adgroups/{nccAdgroupId}?fields=bidAmt`, body `{"nccAdgroupId": ..., "bidAmt": N}` (`set_ad_lock()`처럼 부분수정 시 `fields` 쿼리파라미터 필수 — 안 붙이면 400 에러, 2026-08-28 실측 확인된 NCC API 공통 제약). id=7 계정 8개 그룹 50원→70원 실제 적용·검증 완료.

관련: [[project_naver_ad_product_roas]] [[project_smartstore_api_setup]]

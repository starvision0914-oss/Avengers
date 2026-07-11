---
name: ownerclan-api-discovery
description: 오너클랜 정식 GraphQL API 확인·인증 테스트 성공(2026-07-11) — 크롤러 구축 진행 중(미완료)
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

오너클랜(https://ownerclan.com)은 화면스크래핑이 아니라 **정식 GraphQL API**를 제공한다. ownerclan.com 우측상단 "오너클랜 API" 메뉴 → api-center-guest-view.php에서 매뉴얼 ZIP 로그인 없이 다운로드 가능(`https://cdn.ownerclan.com/API%20매뉴얼.zip`, Seller/Partner/Vendor/상품정보고시 4종 PDF).

**인증**: 별도 API키 발급 불필요 — ownerclan.com 로그인과 동일한 판매사 ID/PW로 JWT 발급.
- 인증 엔드포인트: `POST https://auth.ownerclan.com/auth`, body `{"service":"ownerclan","userType":"seller","username":"...","password":"..."}` → JWT 토큰 반환(유효기간 30일, exp-iat=2592000초)
- GraphQL 엔드포인트: `https://api.ownerclan.com/v1/graphql` (READ는 GET+query파라미터, WRITE는 POST), 헤더 `Authorization: Bearer <토큰>`

**테스트 계정(실계정, 실제 사용 중)**: login_id=`dlwodbs999`, password=`@dlwodbs0`. 2026-07-11 인증 성공 확인 + `allItems(first:3)` 쿼리로 실제 상품데이터(키/이름/가격/상태) 조회 성공.

**핵심 쿼리**:
- `item(key: "W코드")` — 단일 상품
- `allItems(first, after, category, search, minPrice, maxPrice, status, vendor, dateFrom, dateTo, sortBy, ...)` — 최대 1000개/페이지, cursor 페이지네이션(`after`+`first` 권장, `before`/`last`는 불안정)
- `itemHistories` — 품절/단종/재입고 변경이력(41종 유형), `itemKey` 지정 시 날짜제한 없음, 미지정시 최대 7일

**필드→기존 sale_status 매핑**: API status `available`=1(판매중), `soldout`=2(품절), `unavailable`≈2로 처리 권장(진열제외), `discontinued`=3(단종). 기존 [[project_ownerclan_reserve_pipeline]]의 `EXCEL_COL_MAP`(apps/ownerclan/services.py) 필드셋 그대로 재사용 가능.

**Why**: 사용자가 "오너클랜 크롤링사이트" 요청 → 화면스크래핑보다 정식 API가 훨씬 안정적이라 이 경로로 결정.
**How to apply**: 다음 세션에서 이어가려면 — (1) OwnerclanAccount 모델(login_id/pw/토큰캐시) 신설, (2) 위 인증+allItems로 신규상품만 골라 예비상품(ownerclan_product) INSERT하는 서비스함수(기존 `ingest_playauto`의 INSERT 패턴 재사용), (3) management command, (4) /blog(="오너클랜크롤러" 메뉴, [[project_sidebar_reorg_2026-07-11]]) 페이지에 버튼 연결. 계정모델·크롤러 서비스·커맨드·UI 전부 아직 미작성 상태에서 중단됨.

---
name: project_lotteon_nomatch_suspend
description: "롯데온 미매칭(W코드 카탈로그미존재) 판정 인프라 구축완료, 실제 판매중지 자동클릭은 2FA막혀 보류"
metadata: 
  node_type: memory
  type: project
  originSessionId: bde93fa4-f2ed-49c3-bbc9-edaf62785b13
  modified: 2026-08-23T10:00:26.538Z
---

롯데온에 11번가/지마켓/스마트스토어와 동일한 "미매칭"(W코드 오너클랜 소싱인데 예비상품 카탈로그에 코드 자체가 없음) 판정 인프라를 구축함(2026-08-23).

**구축한 것:**
- `LotteonMyProduct.purchase_cost` 필드 신설(migration 0004) — 오너클랜 마켓가, NULL=미매칭
- `apps/cpc/eleven_my_product_service.py`의 `refresh_lotteon_purchase_costs(codes=None)` — 기존 11번가/지마켓/스마트스토어 3종과 완전히 동일한 SQL JOIN 패턴(seller_product_code의 WDM_/AUTO_ 접두어 제거 후 ownerclan_product.product_code 매칭)
- `ownerclan_upload.py`(예비상품 업로드시 증분갱신)와 `crawl_lotteon_products.py`(상품크롤 후 전체갱신) 양쪽에 자동 연결
- `apps/lotteon/views.py`의 `LotteonMyProductListView`에 `no_match=1` 필터 + `no_match_total` 캐시(120초) 카운트 추가 — 다른 플랫폼과 동일 UI 패턴

**실측 결과(2026-08-23):** 전체 24,786개 중 W코드 4,339개, 매칭 2,979개, 미매칭 1,360개 — 단 미매칭 1,360개 전부 이미 END/STP/SOUT 상태이고 **판매중(SALE)인 미매칭은 0건**. 지금 당장 판매중지 조치할 대상이 없음.

**미완성 부분(보류):** 11번가/지마켓/스마트스토어처럼 "미매칭 전체 판매중지" 버튼(Selenium 자동클릭)까지는 못 만듦 — 롯데온 판매자센터 상품관리 UI의 실제 검색/전체선택/판매중지 버튼 셀렉터를 확인하려고 rejoice234 계정으로 라이브 탐색 시도했으나 세션이 만료돼 **2FA(OTP) 재인증이 필요**한 상태에서 막힘. 실사이트 셀렉터를 추측으로 만들면 잘못된 상품에 클릭이 갈 위험이 있어 보류함(참고: [[feedback_verify_before_overwrite]]).

**Why:** 사용자가 4개 플랫폼 전체에 동일한 미매칭 판매중지 기능을 원함. 지금은 SALE 상태 미매칭이 0건이라 급하지 않다고 판단, 사용자가 "나중에 필요할 때 알려주겠다"고 보류함.

**How to apply:** 다음에 이 작업 이어갈 때: (1) 먼저 `no_match=1` 필터로 SALE 상태 미매칭이 실제로 생겼는지 확인, (2) 생겼으면 사용자에게 롯데온 2FA(OTP) 인증 도움 요청(채팅 릴레이, [[project_lotteon_login_success]] 방식) → 세션 확보 → 상품관리 페이지 실탐색으로 셀렉터 확인 → `crawlers/lotteon_loss_delete.py` 같은 파일로 gmarket_loss_delete.py 패턴 미러링해서 구현(단, 판매중지 후 반드시 재조회 검증 단계 포함할 것 — [[project_gmarket_suspend_success_not_sticking]] 버그 재발 방지).

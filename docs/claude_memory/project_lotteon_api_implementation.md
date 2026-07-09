---
name: project_lotteon_api_implementation
description: "롯데온 apps/lotteon 실제 구현 완료 상태(2026-07-08) — 상품/광고비 API 엔드포인트, 인증방식, 모델 전체 목록"
metadata: 
  node_type: memory
  type: project
  originSessionId: 60268d08-a098-4f17-be89-c7ede2bacb5c
---

[[project_lotteon_integration_attempt]]·[[project_lotteon_login_success]]가 "미작성"이라 기록했던 것과 달리,
**apps/lotteon이 이미 완성되어 있음**(2026-07-08 실측 검증). 다음 세션에서 롯데온 진행상황 확인 시 이 파일을
최신으로 보고, 위 두 메모리는 과거 시행착오 기록으로만 참고.

## 위치
`/home/rejoice888/Avengers/backend/apps/lotteon/` (models.py, views.py, urls.py, management/commands/)
`/home/rejoice888/Avengers/backend/crawlers/lotteon_product_crawler.py`, `lotteon_ad_crawler.py`

## 외부(롯데온) API — 인증방식이 서로 다름
- 상품: `soapi.lotteon.com/soapi/v1/product/information/selectProductList` — 로그인 후 XHR에서 탈취한 **Bearer 토큰**(performance 로그로 추출, 브라우저는 닫고 requests로 페이지네이션)
- 광고 일자별: `ad.lotteon.com/advRpt/advClickRptDay/loadList`(클릭광고), `.../advSadRptDay/loadList`(스마트매출업) — **세션 쿠키**(브라우저 in-page fetch, credentials:include)
- 광고 상품별: `.../advClickRptItem/loadList`, `.../advSadRptItem/loadList` — 세션 쿠키, 일단위 페이지네이션
- 공식 오픈API(`api.lotteon.com/apiGuide/`, 계정별 발급키)는 **미사용** — soapi 내부API와 인증스킴이 달라 403/401만 뜸
- 필드명 camelCase 실측 검증 완료: basicDate/adspend/clickCnt/impCnt/sellQt/sellCost 등(2026-06 tmxkql111/tmxkql222 실데이터로 확인). 클릭광고 상품별(advClickRptItem)은 3계정 다 미등록이라 실측 미검증(raw_json 보존해둠)

## 내부 Django API (`config/urls.py`에 `api/lotteon/` 마운트)
- `GET /api/lotteon/dashboard/` — 계정별 매출(SalesRecord, 엑셀업로드)+구매가+광고비(LotteonAdCost)+ROAS
- `GET /api/lotteon/accounts/` — 활성 계정 목록

## 모델
LotteonAccount(login_id/pw, seller_no=trNo, api_key 필드는 있으나 미사용, cookie_data), LotteonAdCost(계정×일자×ad_type),
LotteonProductAdCost(계정×일자×seller_item_no), LotteonMyProduct(계정×pd_no)

## management command
`crawl_lotteon_products`, `crawl_lotteon_ad_cost` — 둘 다 eleven_block_guard 전역락(platform='lotteon') 사용.
**cron 미등록**(수동 실행만 확인된 상태, 2026-07-09 기준).

**Why:** 메모리가 실제 진행상황보다 크게 뒤처져 있어서(2FA 실패 기록까지만 있고 그 이후 완성된 크롤러/API를 놓침) 사용자가 "롯데온 API 알려줘"라고 물었을 때 코드를 직접 확인해야 했음.
**How to apply:** 롯데온 작업 요청 오면 먼저 이 파일로 현재 구현 상태 파악 → 필요시 코드 재확인(cron 등록 여부, 필드 매핑 정확도 등은 시간이 지나면 바뀔 수 있음).

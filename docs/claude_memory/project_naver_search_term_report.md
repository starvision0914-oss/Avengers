---
name: naver-search-term-report
description: "네이버 검색어 리포트 구축(2026-07-10) — 상품별 매칭은 API 제약으로 불가, 계정 단위만 가능"
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

`/naver-roas` 페이지에 "검색어" 탭 추가. `crawlers/naver_search_term_crawler.py` + `crawl_naver_search_term` 명령, `NaverSearchTermReport` 모델(계정+월+검색어 단위).

**핵심 발견**: ads.naver.com 내부 API(`/apis/sa/api/advanced-report/values`)에서 "키워드"(keyword) 차원은 쇼핑검색광고가 자동타겟팅이라 전부 빈값("-") — 의미 없음. 실사용 데이터는 "검색어"(expKeyword) 차원에 있음(계정당 월 5~10만 행, 클릭/매출 있는 것만 필터하면 1000~2000행).

**API 제약(중요, 재확인 불필요)**: expKeyword는 상품/소재(nccAdId) 차원과 상호배타 — 같은 요청에 동시 조회 불가. 광고그룹(nccAdgroupId) 단위는 결합 가능하나 그룹 하나에 상품 수십~수백개 묶여있어(실측: 광고그룹 53개 vs 상품 26,221개) 상품별이라 보기 어려움. **"이 검색어가 어떤 상품을 팔았는지"는 네이버가 API로 제공하지 않음** — 사용자에게 재확인 없이 이 전제로 답해도 됨.

계정 매핑: `naver_ads_cookies.json`에 쿠키 있는 계정만(rejoice888/666/999 — [[project_smartstore_adcost_scope]]와 동일 3계정). 2026년 1~7월 백필 완료(총 18,123건).

**Why**: 사용자가 "우수상품도 키워드 뽑아줘" 요청 → API 제약 설명 후 계정단위로 축소 합의.
**How to apply**: 이후 "상품별 검색어/키워드" 요청 오면 이 제약부터 설명하고 계정단위 대안 제시.

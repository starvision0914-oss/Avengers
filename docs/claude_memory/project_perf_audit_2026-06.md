---
name: project_perf_audit_2026-06
description: 어벤저스 전 페이지 로딩속도 감사·수정 (2026-06-14). 인덱스·N+1·캐시
metadata: 
  node_type: memory
  type: project
  originSessionId: 2652a85c-f4de-41b6-8478-ea5e69ec25ed
---

2026-06-14 전 페이지 성능 감사·수정 완료(병렬 에이전트 조사→실측 검증). 측정 전/후:
- /gmarket-my 중복제외 **353초→4.2초**(캐시 0.18초): id_in 거대서브쿼리→loser id만 캐시 후 exclude (views.py GmarketMyProductListView)
- /gmarket-roas 연단위 **178초→3.2초**(캐시 0초): `_gmkt_month_q` OR체인→(year,month) 범위 + 응답 300초 캐시(`_gmkt_cache_key`, GmarketRoasAccountsView/GmarketProductRoasView)
- /dashboard ProfitDashboard **9.2초(367쿼리)→1.1초**: 11번가 계정루프 5쿼리×71 일괄집계화
- /overview·11번가요약 ElevenSummary **21.8초→1.3초**: 최신잔액·CPC델타 N+1 일괄화, CrawlerLog .values 경량화
- /st11-roas **27초→0.45초**, /st11-killlist **25초→0.35초**: st11_product_daily 커버링인덱스
- /sales-dashboard **41초→1.1초**, /net-profit **24.8초→0.03초**: sales_records 인덱스
- /crawler eleven-costs **~30초→0.13초**: ViewSet pagination_class=None 전량덤프→limit 기본200, 프론트 limit=50
- /myproduct(11번가)는 직전에 수정 [[project_eleven_my_query_perf]]

**추가한 인덱스**(migration cpc 0034, sales 0005): sales_records(platform,order_date)/(status,order_date)/(platform,status,order_date)/(-order_date)/(product_code); st11_product_daily(stat_date,eleven_id,product_no,cost,conv_amount) 커버링; eleven_sellerpoint_history(transaction_type,transaction_datetime); crawler_logs(-created_at)/(platform,level,-created_at); gmarket_deposit_snapshots(gmarket_id,-collected_at); gmarket_my_product(account,seller_product_code,id).

**캐시**: LocMemCache(단일 runserver). COUNT·ROAS집계·dedup loser를 필터/기간별 120~300초 TTL. 동기화(크롤) 때만 데이터 변함.

**죽은코드 제거**: ownerclan/keyword 페이지가 changed-field 56회 풀스캔 호출→결과 미사용(렌더안되는 패널용)이라 프론트 호출 제거.

**교훈/패턴**: ①큰테이블 작은차원조인필터는 정렬인덱스 무력화(filesort)→id IN으로 풀기 ②OR(year,month) 체인→범위조건 ③계정루프 N+1→GROUP BY + id IN(Max(id) per seller) ④무거운 집계는 EXPLAIN 'Using temporary; Using filesort'/type=ALL 확인 후 캐시. 미적용 후순위: st11 ProductRoas 전체계정 CSV/적자모달 루프(마운트 아님, 인덱스로 완화됨).

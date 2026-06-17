---
name: project_eleven_my_query_perf
description: /myproduct(ElevenMyProductsPage) 느림 원인=조인필터 filesort+COUNT. 수정완료
metadata: 
  node_type: memory
  type: project
  originSessionId: 2652a85c-f4de-41b6-8478-ea5e69ec25ed
---

`/myproduct`=ElevenMyProductsPage, 백엔드 `eleven_my_product_service.get_my_products`. eleven_my_product ~60만행(포커스 45계정 ~45만행).

**느렸던 근본원인 2가지(2026-06-14 수정):**
1. **filesort** — `account__is_focused=True` 조인으로 필터하면 옵티마이저가 crawler_accounts부터 조인해 ~45만행을 temp+filesort(synced_at 인덱스 무력화) → 페이지당 **268초**. 해결: 조인 대신 `account_id IN (포커스 id 리스트)` → synced_at 인덱스 역방향 스캔, LIMIT 50만 읽음 → **0.08초**.
2. **COUNT(*)** 45만행이 매 페이지 4~10초 → 필터별 `emp_count:` 키 120초 TTL 캐시(LocMemCache). 동기화 때만 데이터 변함.
3. **계정요약(get_account_summary)** = /myproduct 마운트가 products와 함께 부르는 두번째 호출이 5.86초로 새 병목이었음(2026-06-14 추가수정). 잔액 계산이 focused 셀러 거래 20.8만행 전량을 파이썬으로 끌어와 셀러별 첫행만 남김(4.36초) → `id IN (셀러별 Max(id))` 배치(0.31초) + 함수전체 'eleven_acct_summary' 120초 캐시 → 5.86초→1.75초(캐시 0초). 주의: "products 0.08초"는 목록쿼리만이고 페이지 체감은 accounts 호출 포함.

**교훈**: 큰 테이블에서 작은 차원테이블 조인필터(is_focused 등)는 정렬 인덱스를 못 쓰게 만들어 filesort 유발. `account_id IN (...)`로 풀어내면 정렬 인덱스 사용 가능. 진단은 EXPLAIN의 'Using temporary; Using filesort'.

관련: ownerclan delete_all_products는 TRUNCATE로 변경(DELETE FROM이 대용량 TEXT라 201k행에 ~12분). [[project_ownerclan_reserve_pipeline]]

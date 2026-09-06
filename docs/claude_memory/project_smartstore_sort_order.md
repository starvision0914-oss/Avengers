---
name: project_smartstore_sort_order
description: 스마트스토어 대시보드 계정목록 정렬 = 매출desc → 등록상품수desc 고정(2026-09-06 사용자요청)
metadata: 
  node_type: memory
  type: project
  originSessionId: 5819c9b5-4ebb-4c4b-bfb1-e856ab5bec3c
  modified: 2026-09-06T12:08:10.961Z
---

`/smartstore` 대시보드의 계정별 요약 테이블(`DashboardView.by_account`, 프론트 `SmartStorePage.tsx`의 `byAcc`)은 **항상** 다음 순서로 정렬한다:
1. 매출(sales) 많은 순
2. 동률이면 등록상품수(status_type='SALE' 개수) 많은 순

**구현:** `backend/apps/smartstore/views.py` DashboardView — `account_list.sort(key=lambda x: (-x['sales'], -x['product_count']))`. `product_count`는 `SmartStoreProduct.objects.filter(status_type='SALE').values('account_id').annotate(cnt=Count('id'))`로 계정별 집계해 추가함(기존엔 없던 필드).

**Why:** 사용자가 "매출이 많은순서로 하고 다음은 등록상품이 많은 순서로 항상 정렬해줘"라고 명시적으로 요청. 프론트(`SmartStorePage.tsx`)는 `byAcc`를 재정렬하지 않고 백엔드 순서 그대로 렌더링하므로, 백엔드 정렬만 지키면 "항상" 조건이 보장됨.

**How to apply:** 이 테이블 관련 버그/요청이 오면 정렬기준이 이미 고정되어 있음을 전제로 확인. 등록상품수 집계 기준(판매중만, DELETED 제외)은 `ProductStatsView`와 동일 컨벤션.

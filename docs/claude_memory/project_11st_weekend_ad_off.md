---
name: project_11st_weekend_ad_off
description: 11번가 주말(토/일) 광고 OFF는 의도적 — 상품ROAS 리포트 주말 데이터 없음은 정상
metadata: 
  node_type: memory
  type: project
  originSessionId: 2652a85c-f4de-41b6-8478-ea5e69ec25ed
---

11번가는 **주말(토/일) 광고를 의도적으로 OFF** 함(2026-06-17 사용자 확정, "일단 그냥 놔두자").

그 결과 St11ProductDaily(상품별 광고 리포트, 09시 ROAS크론 출처)에서 **주말 날짜가 0행/누락**으로 나옴 = 크론 실패 아님, 11번가 원본에 광고 데이터가 없는 것(노출·클릭 있어야 행 생성). 예: 06-06(토) 240행·전환0 vs 평일 ~2,000행. 5/2·5/3·5/23·5/24·6/7·6/13·6/14 등 누락 전부 주말.

**How to apply:** 매출/광고 분석 시 주말 공백은 정상으로 간주(왜곡 거의 없음 — 주말은 광고비 자체가 0). "전환0 광고 OFF 리스트" 산출 시 남는 변수는 **최근 3~5일 전환 정산 시차**뿐이므로 최근일 제외한 윈도우로 집계. 거래내역 광고비(ElevenCostHistory, 정산시차)와 상품ROAS리포트(St11ProductDaily)는 출처가 다름 — 혼동 금지. [[project_sales_revenue_def]] [[project_11st_cost_partial_loss]]

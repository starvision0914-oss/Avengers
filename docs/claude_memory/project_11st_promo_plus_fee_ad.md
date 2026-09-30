---
name: 11st-promo-plus-fee-ad
description: "11번가 순수익 = 매출이익 − 광고비(수수료결제 포함) + '광고 매출 활성화 프로모션' 지원금 (2026-09-30 사용자 지시)"
metadata:
  node_type: memory
  type: project
  originSessionId: 7132ddd9-17a6-4554-8812-41a93294d4eb
  modified: 2026-09-29T17:50:07.350Z
---

11번가 손익 기준 (2026-09-30 사용자 확정): 수수료결제는 광고비(CPC)에 포함해 차감하고, ElevenCostHistory REWARD 중 `raw_description`에 '매출 활성화 프로모션'이 든 지원금만 순수익에 플러스로 가산. 7월 -3,906,486 → -1,506,486. 다른 리워드(전시입찰 239,546, 셀러포인트 지급 10만, 5월 신규광고주 프로모션 등)는 미포함.

**Why:** 수수료결제는 리워드 받은 12계정에서만 7/13~ 발생(2,633,950원), 무료 지원금 2,400,000원과 짝. 사용자가 "각각 계산해서 플러스와 광고비 차감"으로 지시.
**How to apply:** ElevenSummaryView(promo_total/seller.promo)·OverviewView(e_promo)·AllMallProfitView(st11_promo)·OverviewDailyView(promo_by_date) 4곳 + OverviewDashboard 카드(fee_payment/promo 줄). 광고비 표시는 총CPC 그대로, 프로모션은 별도 줄. 다른 리워드 추가 여부는 사용자 확인 후. 원본 백업: 스크래치패드 views.before_promo.py. 관련: [[project_overview_dashboard_fixes]], [[feedback_gmarket_hidden_account_excluded]]

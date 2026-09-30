---
name: gmarket-hidden-account-excluded
description: 지마켓 숨김계정(sglobal2 등) 광고비는 손익에서 제외가 맞음 — 점검 시 오류로 보고 금지
metadata:
  node_type: memory
  type: feedback
  originSessionId: 7132ddd9-17a6-4554-8812-41a93294d4eb
  modified: 2026-09-29T17:39:43.446Z
---

지마켓 숨김(hide_from_dashboard) 계정의 광고비는 손익/통합현황에서 **제외하는 것이 의도된 동작**이다. 2026-09-30 사용자가 "sglobal2는 빼는 게 맞다"고 확인함. 7월 sglobal2 광고비 450,318원(매출 0)이 손익에 없는 것은 오류가 아님.

**Why:** 숨김계정은 매출 0인데 광고비 이력만 남아 있어 포함하면 /gmarket 대시보드와 합계가 어긋난다. AllMallProfitView가 `is_active=True, hide_from_dashboard=False` 계정만 집계.
**How to apply:** 전수조사/정합성 점검에서 숨김계정 광고비 차이는 "발견"으로 보고하지 말고 참고사항으로만 언급. 코드 수정 금지. 관련: [[project_gmarket_dashboard_cost_column]]

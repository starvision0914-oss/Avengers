---
name: feedback_timezone_pitfalls
description: "날짜 처리 타임존 함정 2가지 - toISOString 금지, MySQL __date 조회 금지 (KST 환경)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9cf8d0c5-70a3-44cf-8a41-52304540e393
---

Avengers는 KST(+9) 환경이라 날짜 처리에 두 가지 함정이 있다. 둘 다 2026-06-07 실제 버그로 확인됨(5월 매출 5/31 누락, 통합대시보드 11번가 광고비 0원).

**1) 프론트엔드: `Date.toISOString().slice(0,10)` 금지**
toISOString()은 UTC로 변환하므로 KST 자정이 전날로 밀린다. 예: `new Date(2026,5,0)`(5월 말일 KST 00:00) → toISOString → '2026-05-30'. 월말 하루가 통째로 누락됨.
→ 반드시 로컬 기준 `ymd(d)` 사용 (src/utils/format.ts: getFullYear/getMonth/getDate 직접 조합). monthEnd/prevDate/nextDate/엑셀다운로드/costRange 등 날짜범위 계산 전부 적용.

**Why:** 월간/기간 조회 시 말일 데이터가 빠져 매출·광고비 합계가 틀림.

**2) 백엔드: `transaction_datetime__date` 조회 금지 (MySQL + USE_TZ=True)**
MySQL 타임존 테이블 미적재 상태에서 `__date` lookup은 0건을 반환(에러도 안 남). ProfitDashboardView가 이 때문에 11번가 광고비를 0으로 표시했음.
→ 반드시 aware datetime 범위로: `transaction_datetime__gte=kst.localize(...), __lt=...` (ElevenSummaryView 방식).

**How to apply:** 날짜 경계 계산은 항상 KST 로컬 기준으로, DB 조회는 aware datetime 범위로. [[project_sales_revenue_def]]

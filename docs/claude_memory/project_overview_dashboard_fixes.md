---
name: overview-dashboard-fixes
description: "/overview 페이지 개선(2026-07-10) — 쿠팡·롯데온 누락 버그 수정, 구매가 표시, 쇼핑몰 클릭 상품별 손익 모달 추가"
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

**버그 발견·수정**: `OverviewView`(`/api/cpc/overview/`, "기간별 실적" 섹션)가 `markets` 배열에 지마켓/11번가/스마트스토어만 있고 **쿠팡·롯데온이 처음부터 빠져있었음**. `AllMallProfitView`(`/api/cpc/all-mall-profit/`, "종합 순수익"/"쇼핑몰별 손익")는 SalesRecord 전체 플랫폼을 정상 포함 — 그래서 페이지 안에서 두 섹션 합계가 어긋났음("숫자가 약간 차이나는 것 같다"는 사용자 감지가 정확했음). SalesRecord 기준으로 coupang/lotteon 항목을 OverviewView에 추가해 격차 526,028원→340,689원으로 축소.

**남은 차이(의도된 것, 미해결)**: 스마트스토어의 "정산"(Commerce API 정산데이터, OverviewView가 씀)과 "매출"(SalesRecord 매칭데이터, AllMallProfitView가 씀)은 서로 다른 소스라 완전히 일치하지 않음(월 기준 34만원 안팎). 임의로 통일하면 다른 화면(스마트스토어 대시보드)과 어긋날 수 있어 보류.

**신규 기능**: 쇼핑몰별 손익 카드에 "구매가" 행 추가(이미 백엔드가 갖고 있던 SalesRecord.cost 노출만 하면 됐음). 카드 클릭 → 모달(`MallProductModal`)로 상품별 목록, 전체/적자/우수 필터(순익 기준, ROAS 아님 — SalesRecord엔 상품별 광고비가 없어서), 엑셀다운(클라이언트 Blob, [[feedback_window_open_bearer_auth]] 패턴 준수). 백엔드 `MallProfitProductsView`(`/api/cpc/mall-profit-products/`) 신규.

**Why**: 사용자가 새 플랫폼(롯데온 등) 추가 시 이런 대시보드/집계 뷰들을 놓치기 쉬움.
**How to apply**: 새 플랫폼을 SalesRecord/TaxVatMonthly에 연결할 때, `OverviewView`·`AllMallProfitView`·`MallProfitProductsView`처럼 플랫폼 목록을 하드코딩한 곳이 여러 군데 있으니 grep으로 전부 찾아 함께 갱신할 것.

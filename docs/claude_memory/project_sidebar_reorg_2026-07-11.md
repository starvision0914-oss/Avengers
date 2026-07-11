---
name: sidebar-reorg-2026-07-11
description: "사이드바 정리 — 통합현황/대시보드 병합, 쿠팡·롯데ON을 스마트스토어에 통합, 오너클랜크롤러 메뉴 신설"
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

사용자가 "/dashboard와 /overview 헷갈린다", "쿠팡·롯데온은 매출·계정 작으니 스스에 통합"이라 요청해 2026-07-11 UI 정리:

1. **/dashboard(수익대시보드) → /overview(통합현황)에 흡수**. `OverviewDashboard.tsx` 하단에 접이식 "계정별 상세현황" 섹션으로 `<DashboardPage/>`를 그대로 렌더(코드 재작성 없이 컴포넌트 합성). `/dashboard` 라우트는 `/overview`로 리다이렉트. 사이드바 "대시보드" 메뉴 삭제, "Avengers" 로고를 `/overview` 링크로 만들어 대체.
2. **쿠팡·롯데ON을 스마트스토어 페이지 안 탭으로 통합**. `SmartStorePage.tsx` 상단에 스마트스토어/쿠팡/롯데ON 탭바(`PlatformTabBar`) 추가, 비-스마트스토어 탭은 조기 반환으로 `<CoupangDashboard/>`/`<LotteonDashboard/>` 렌더. 사이드바에서 "쿠팡"/"롯데ON" 메뉴 삭제, `/coupang`·`/lotteon` 라우트는 `/smartstore`로 리다이렉트.
3. **`/blog` 라우트(GamePage, 실제로는 "야구단 매니저" iframe — 다른 프로그램)를 사이드바에서 "오너클랜크롤러"로 재명명**. 기존 `/ownerclan`(예비상품)과 이름 겹칠 뻔해서 "오너클랜크롤러"로 구분(사용자가 직접 지적해서 수정함). 이 페이지 콘텐츠는 아직 게임 iframe 그대로 — [[project_ownerclan_api_discovery]] 크롤러 완성되면 이 자리에 새 UI를 넣어야 함.

**Why**: 사용자가 저사양 기술이해도라 여러 페이지가 뭐가 다른지 구분 못해 혼란스러워함([[feedback_low_tech_literacy_guidance]]).
**How to apply**: 이후 페이지 통폐합 요청 시 "코드 재작성"보다 "기존 컴포넌트를 그대로 하위 섹션/탭으로 합성"하는 방식이 리스크가 적고 빠름 — 이번에도 이 패턴으로 처리해 정상 동작 확인함.

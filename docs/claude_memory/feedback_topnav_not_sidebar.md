---
name: feedback_topnav_not_sidebar
description: "Avengers 앱에는 세로 사이드바가 없고 상단 가로 TopNav만 있음, 페이지별로 숨기지 말 것"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a2d588dd-a8ef-4b9d-9ed0-0fd113039ab2
---

Avengers 프론트엔드(`frontend/src/components/Layout/`)에는 세로 `<aside>` 사이드바가 없다. `Sidebar.tsx` 파일은 존재하지만 어디서도 import되지 않는 죽은 코드다. 사용자가 "사이드바"라고 부르는 것은 실제로는 `TopNav.tsx`(상단 가로 네비게이션 바, `MainLayout.tsx`가 모든 라우트에 공통으로 렌더링)를 가리킨다.

**Why:** 2026-07-14 `/owner` 페이지 작업 중 "사이드바가 옆으로 밀렸다"는 말을 듣고 실제로는 표(table)가 너무 넓어져 페이지 전체가 가로로 밀린 것이었는데, 이를 오인해 "사이드바를 없애줘" 요청에 따라 `/owner` 라우트에서만 TopNav를 조건부로 숨겼다가, 곧바로 "항목이 사라졌다, 추가해줘"라는 정정 지시를 받고 되돌렸다. TopNav는 전체 앱 공용 네비게이션이라 특정 페이지에서만 숨기면 사용자가 다른 메뉴로 이동할 방법이 없어져 불편했던 것으로 보임.

**How to apply:** "사이드바"라는 단어가 나오면 먼저 TopNav를 가리키는지, 아니면 페이지 내부의 넓은 콘텐츠(표 등)가 화면을 밀어내는 문제인지 구분할 것. 레이아웃이 밀리는 문제는 TopNav를 숨기기보다 콘텐츠 쪽에 `overflow-x-hidden`/`min-w-0`을 적용해 해결하는 편이 안전하다. TopNav 자체를 특정 라우트에서만 숨기는 변경은 신중히 — 사용자가 명시적으로 재확인하기 전엔 하지 말 것. TopNav 글자 크기는 2026-07-14 기준 20px(`text-[20px]`, 아이콘 20)로 전체 앱 공통 확대됨.

---
name: window-open-bearer-auth-bug
description: window.open()으로 백엔드 API 직접 열면 Bearer 토큰 인증 실패 — 엑셀다운로드 등에서 반복 발생 가능한 패턴
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

이 프로젝트 인증방식은 Bearer 토큰(axios 인터셉터가 localStorage의 access_token을 Authorization 헤더로 첨부, `frontend/src/api/client.ts`). `window.open('/api/...')`처럼 axios를 거치지 않고 브라우저가 직접 URL을 열면 토큰이 안 실려 401 → 사용자에겐 "다운로드가 안 된다"로 보임.

실제 사례: `/naver-roas` 엑셀↓ 버튼이 이 패턴이라 깨져있었음(2026-07-10 발견·수정).

**Why**: axios 인터셉터는 axios 인스턴스를 통한 요청에만 적용되고, `window.open`/`<a href>` 직접 네비게이션은 인터셉터를 우회함.
**How to apply**: 새 "엑셀다운로드"/CSV 내보내기 버튼을 만들 때 백엔드 export 엔드포인트로 `window.open`하지 말 것. `TaxVatPage.tsx`의 `handleExportExcel`처럼 **이미 화면에 로드된 데이터로 클라이언트에서 Blob CSV를 만들어 `<a download>`로 다운로드**하는 패턴을 기본으로 쓸 것(인증 문제 원천 차단, 서버 왕복도 없음). 서버측 필터링이 꼭 필요한 대용량 export만 예외적으로 axios(`responseType:'blob'`)로 받아 Blob URL 생성.

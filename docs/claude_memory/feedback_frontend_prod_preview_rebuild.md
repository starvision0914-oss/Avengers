---
name: feedback_frontend_prod_preview_rebuild
description: avengers-frontend는 2026-09-11부터 vite dev가 아니라 프로덕션 빌드(dist)를 vite preview로 서빙 — 코드 수정 후 반드시 재빌드 필요
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3e9ec29b-6bb4-4c71-a87c-87e2c3fec4b6
  modified: 2026-09-20T15:45:35.827Z
---

avengers-frontend(포트 5173)는 vite dev 서버가 아니라 `vite preview --host 0.0.0.0 --port 5173`로 dist/ 프로덕션 빌드를 서빙 중(ecosystem.config.cjs). 이유: dev 서버(수백개 미번들 모듈 개별요청)가 서버 과부하 시 로딩이 느려서 2026-09-11에 전환.

**Why**: 이 사실을 모르고 프론트 .tsx/.ts를 수정한 뒤 "반영됐다"고 보고했다가, 사용자가 "안 보여"라고 지적함 — HMR이 동작하지 않고, `/src/...` 경로 요청도 실제로는 SPA index.html(구버전 번들)을 200으로 돌려줘서 겉보기엔 정상처럼 보임(상태코드만 보고 검증하면 안 속아넘어감).

**How to apply**: frontend/src 파일을 수정할 때마다 반드시 `bash /home/rejoice888/Avengers/scripts/rebuild_frontend.sh` (내부: `npx vite build && pm2 restart avengers-frontend --update-env`) 실행 후 "완료"라고 보고할 것. 빌드 성공 여부(새 해시 번들명 생성, `pm2 restart` 성공)까지 확인하고 나서 사용자에게 확인을 요청. 단순히 파일 저장/HMR 로그 유무로 반영 여부를 판단하지 말 것.

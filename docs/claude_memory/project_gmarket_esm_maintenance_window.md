---
name: project_gmarket_esm_maintenance_window
description: 지마켓 ESM+ 새벽 정기 서비스 점검(02:00~05:00 관측) — 이 시간대 지마켓 크롤/판매중지/가격조정 등은 전부 실패함(버그 아님)
metadata: 
  node_type: memory
  type: project
  originSessionId: 2b25ce04-399d-4dcc-bcb0-8937fe2c40ef
  modified: 2026-08-26T19:17:39.052Z
---

2026-08-27 새벽 지마켓 가격맞추기(확인필요) 재시도가 10계정 전부 "상품관리 iframe 진입 실패"로 실패. 실시간 확인 결과 signin.esmplus.com/error/siteoff로 리다이렉트되며 "ESM+ 정기 서비스 점검 2026-08-27 02:00:00 ~ 05:00:00" 안내 페이지가 뜸. 코드/로그인/세션 문제가 아니라 사이트 자체가 완전히 접근 불가한 상태였음.

**Why:** 이 시간대에 지마켓 관련 어떤 작업(판매중지, 가격조정, 상품수집 등)을 돌려도 계정 문제로 오판하면 안 됨 — 전부 이 점검 때문일 가능성 우선 의심.

**How to apply:** 새벽 2~5시(관측된 1회, 매일 반복인지는 미확인) 지마켓 작업 실패 시 가장 먼저 `driver.current_url`에 `esmplus.com/error/siteoff`가 포함되는지 확인. 포함되면 재시도하지 말고 점검 종료 시각까지 대기 후 재개.

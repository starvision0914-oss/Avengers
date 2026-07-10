---
name: smartstore-product-sync-outage
description: "스마트스토어 상품동기화 12일간 조용히 중단(--skip-products cron 플래그), 2026-07-10 발견·수정"
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

`scripts/cron_smartstore.sh`(매일 01:00)에 `--skip-products` 플래그가 붙어 있어 2026-06-28경부터(git `9a09e83 auto backup`, 의도 기록 없음) 상품 12만여건이 전혀 갱신 안 되고 있었음. crontab 주석은 여전히 "상품+판매통계+광고비"라 겉보기엔 정상— 대시보드/판매통계 크론은 정상이라 눈에 안 띔.

**Why**: 자동백업 커밋이라 왜 껐는지 이유 불명. 사용자 확인 후 플래그 제거+즉시 전체 재수집(2026-07-10).
**How to apply**: 이런 종류의 "조용한 회귀"는 로그 성공/실패가 아니라 **DB 최신도(synced_at)**로만 드러남 — 플랫폼 점검 시 계정상태·로그뿐 아니라 상품 synced_at 신선도(3일 기준)를 반드시 함께 확인할 것. 전체 크론 스크립트에서 `--skip/--dry-run/--no-save/--test/--limit` 같은 플래그를 주기적으로 grep해 의도치 않게 박혀있는지 점검하는 습관 필요([[project_system_audit_2026-07-07]] 계열 점검에 편입).

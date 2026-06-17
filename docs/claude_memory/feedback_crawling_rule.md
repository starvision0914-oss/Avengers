---
name: feedback-crawling-rule
description: 크롤링 필수 원칙 — 사람처럼 보수적 페이싱 + 접속 3회 실패 시 중지하고 다음 계정 진행
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9cf8d0c5-70a3-44cf-8a41-52304540e393
---

모든 마켓 크롤러(11번가/G마켓 등)는 반드시 지킬 것:
- **사람이 하는 것처럼** 보수적 페이싱(계정간 랜덤 대기, 쿠키 재사용으로 OTP 우회 등)으로 동작 — 차단 회피
- **접속(로그인) 3회 실패 시 해당 계정 즉시 중지하고 다음 계정으로 진행** (`MAX_CONNECT_ATTEMPTS=3`), 누적 시 `crawling_status='실패'` 표시
- 문제 발생 시 텔레그램 알림

**Why:** 사용자가 반복적으로 강조한 차단방지 핵심 규칙. 반복 로그인 시도가 11번가 계정 차단을 유발하므로.
**How to apply:** 신규/수정 크롤러 작성 시 cost/grade/product/ai/office 크롤러에 이미 적용된 3-strike 재시도 루프 패턴을 그대로 따를 것. [[reference-domeggook]] 등 다른 마켓 자동화에도 동일 적용.

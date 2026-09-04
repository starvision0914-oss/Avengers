---
name: smartstore-wcode-regex-gap
description: "스마트스토어 오너클랜 W코드 판별 정규식(^W[0-9A-F]+$)이 비16진수 W코드를 놓침"
metadata: 
  node_type: memory
  type: project
  originSessionId: 72798bef-7b95-4ff6-9ea6-b86c367edb55
  modified: 2026-09-03T23:16:36.212Z
---

`apps/smartstore/management/commands/sync_ownerclan_stock.py`를 비롯한 기존 코드가 오너클랜
W코드 판별에 쓰는 정규식 `^W[0-9A-F]+$`(W+16진수만 인정)는 실제로는 W+전체영숫자
코드(예: `WFFJ13R`, `WFFG27F` — J,R 등 16진수 아닌 문자 포함)를 놓친다.

**Why:** 2026-09-04 스타주노(starvis9942) 분석 중 발견 — "기타(비W코드)" 1,051건으로 집계했던 것 중
42건이 실제로는 W로 시작하는 오너클랜 코드였음(길이는 7자리로 정상 W코드보다 1자 짧고 비16진수
문자 포함). 정정 결과: 스타주노 진짜 W코드 7,858건(16진수 7,816 + 비16진수 42), 진짜 기타 1,010건.

**How to apply:** 스마트스토어 상품의 오너클랜 소싱 여부를 정확히 판별해야 할 때(재고동기화,
품절처리 등) `^W[0-9A-F]+$` 대신 더 넓은 `^W[0-9A-Za-z]+$`를 쓰거나, 최소한 두 정규식의 차이만큼
누락 가능성을 감안할 것. 기존 프로덕션 커맨드(sync_ownerclan_stock.py)는 아직 좁은 정규식을 그대로
쓰고 있어 이런 코드들은 자동 재고동기화 대상에서 빠져 있음 — 필요시 별도 처리 필요.

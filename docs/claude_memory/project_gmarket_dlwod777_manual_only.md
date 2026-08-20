---
name: project_gmarket_dlwod777_manual_only
description: "지마켓 dlwod777 계정은 상품삭제/판매중지 자동화 금지, 사용자가 직접 관리"
metadata: 
  node_type: memory
  type: project
  originSessionId: c542d3cb-e67a-45e9-aae7-066621cd34f2
  modified: 2026-08-20T01:02:44.777Z
---

dlwod777 지마켓 계정은 기존 상품을 모두 삭제하고 사용자가 직접 올린 상품들만 남아있는 상태(2026-08-20 확인). 상품삭제나 판매중지는 사용자가 직접 할 예정이므로 자동화/크롤러/스크립트가 건드리면 안 됨.

**Why:** 사용자가 계정을 초기화하고 새로 큐레이션한 상품 목록이라, 자동화(예: [[project_11st_loss_delete]] 류의 적자삭제, [[project_smartstore_clean_violation_system]] 류의 판매중지 자동화, 지마켓 광고제어 등)가 무단으로 개입하면 사용자의 수동 작업과 충돌·훼손될 수 있음.

**How to apply:** 지마켓 관련 상품삭제/판매중지/광고OFF 등 계정 단위 자동화 작업을 실행하거나 제안할 때 dlwod777 계정은 대상에서 제외할 것. 사용자가 명시적으로 이 계정에 대해 재요청하기 전까지는 읽기(조회)만 허용.

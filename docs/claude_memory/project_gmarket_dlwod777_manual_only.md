---
name: project_gmarket_dlwod777_manual_only
description: "지마켓 dlwodb777 계정은 상품삭제/판매중지 자동화 금지(수동관리) — 단 신규광고센터 on/off는 2026-09-07부터 예외 허용"
metadata: 
  node_type: memory
  type: project
  originSessionId: c542d3cb-e67a-45e9-aae7-066621cd34f2
  modified: 2026-09-07T01:00:49.017Z
---

dlwodb777(로그인ID, DB상 실제 값) 지마켓 계정은 기존 상품을 모두 삭제하고 사용자가 직접 올린 상품들만 남아있는 상태(2026-08-20 확인). 상품삭제나 판매중지는 사용자가 직접 할 예정이므로 자동화/크롤러/스크립트가 건드리면 안 됨. `CrawlerAccount.is_test_account=True`로 표시되어 있고, `protected_login_ids('gmarket')`을 쓰는 대부분의 삭제/판매중지 로직이 자동으로 이 계정을 제외한다.

**2026-09-07 예외**: 사용자가 "dlwodb777 계정도 적용해서 다음부터 해줘"라고 신규광고센터(adcenter.esmplus.com) ON/OFF에 한해 명시적으로 재요청 → `crawlers/gmarket_new_adcenter_control.py`의 `run_control`에서만 `protected_login_ids('gmarket') - {'dlwodb777'}`로 이 계정을 예외 처리해 광고 on/off 대상에 포함시킴. **다른 모든 자동화(삭제/판매중지 등)는 여전히 차단 대상** — is_test_account 플래그 자체는 그대로 True로 유지.

**Why:** 사용자가 계정을 초기화하고 새로 큐레이션한 상품 목록이라, 자동화(예: [[project_11st_loss_delete]] 류의 적자삭제, [[project_smartstore_clean_violation_system]] 류의 판매중지 자동화)가 무단으로 개입하면 사용자의 수동 작업과 충돌·훼손될 수 있음. 광고 on/off는 상품 자체를 건드리지 않아 사용자가 별도로 허용함.

**How to apply:** 지마켓 관련 상품삭제/판매중지 등 계정 단위 자동화 작업을 실행하거나 제안할 때 dlwodb777 계정은 여전히 대상에서 제외할 것. 신규광고센터 on/off만 예외적으로 포함됨(코드에 이미 반영됨, `is_test_account` 플래그는 안 건드림). 다른 조치까지 확대하려면 사용자의 추가 명시적 요청 필요.

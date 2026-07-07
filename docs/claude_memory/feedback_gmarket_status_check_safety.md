---
name: feedback_gmarket_status_check_safety
description: "지마켓 광고상태 \"확인만\" 하려 할 때 on/off 액션 명령을 쓰면 안 됨 — 실제로 상태를 바꿔버리는 사고 2회 발생"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 65854cbc-8aa2-4568-95c3-193c08d99126
---

`crawl_gmarket_cpc2 on/off`, `crawl_gmarket_ai_control on/off`는 **확인용이 아니라 실제 액션
명령**이다. 현재 OFF인 걸 "확인"하려고 `on`을 실행하면 진짜로 켜버린다(반대도 마찬가지).

**사고 2회 발생(2026-07-07)**: 상태만 보려다 실수로 액션 명령을 돌려서 즉시 kill -9로 중단해야
했음. 사용자가 "왜 진행 안 하고 거짓말하냐"며 신뢰 문제로 번짐 — 도구 오사용이 신뢰 손상까지
이어진 사례.

**안전한 상태조회 전용 명령(읽기만 함, 액션 없음)**:
- `crawl_gmarket_cpc_status [--accounts ...]` — 간편/일반광고 ON/OFF 개수만 리포트
- `crawl_gmarket_ai [--accounts ...]` — AI광고 상태만 리포트 (내부적으로
  `gmarket_ai_crawler.py`를 쓰지, `gmarket_ai_control_crawler.py`(액션용)를 쓰지 않음)

**Why:** on/off 명령도 "이미 ON"/"이미 OFF"면 아무 것도 안 바꾸긴 하지만, 그 반대 경우면
의도와 반대로 상태를 뒤집어버림. 특히 방금 애써 꺼둔 걸 "확인차" on으로 잘못 실행하면
비용이 실제로 발생.
**How to apply:** "안 꺼진 거 맞아?", "제대로 됐어?" 같은 확인 요청이 오면 반드시 위 조회
전용 명령부터 쓸 것. on/off 액션 명령은 실제로 상태를 바꾸고 싶을 때만.

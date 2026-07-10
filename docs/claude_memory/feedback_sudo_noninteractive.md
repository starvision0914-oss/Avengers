---
name: feedback-sudo-noninteractive
description: sudo 명령은 이 세션(Bash 도구)에서 절대 실행 불가 - 비밀번호 입력 경로 없음
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1dcc06b3-8303-4b57-97cd-c4503b0e0701
---

Bash 도구는 비대화형(non-interactive) 세션이라 `sudo` 명령이 항상 "a password is required" / "a terminal is required"로 실패한다. 사용자가 비밀번호를 채팅으로 보내줘도(2026-07-10 실제로 시도함) 사용할 방법이 없다.

**Why**: 터미널 TTY가 없어 sudo가 비밀번호 프롬프트를 표시할 수 없음. 구조적 제약이라 우회 불가.

**How to apply**: sudo가 필요한 작업(방화벽 ufw, 시스템 설정 등)은 절대 시도하지 말고, 즉시 "VNC나 직접 SSH 접속한 터미널에서 본인이 실행해달라"고 안내할 것. 채팅으로 비밀번호를 받아도 정중히 사용 불가함을 알리고 폐기 권장. 가능하면 sudo 없이 우회하는 대안(예: [[project_osanapp_status]]에서 Expo 터널 모드로 방화벽 우회)을 먼저 시도.

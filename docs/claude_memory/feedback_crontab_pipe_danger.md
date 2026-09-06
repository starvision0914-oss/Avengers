---
name: feedback_crontab_pipe_danger
description: "crontab -l | sed 's#...#...#' 실패시 빈 출력이 그대로 crontab -에 먹혀 전체 크론 삭제됨 — 실제로 62개 잡 전삭제 사고 발생(즉시 백업으로 복구)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5819c9b5-4ebb-4c4b-bfb1-e856ab5bec3c
  modified: 2026-09-06T12:08:04.509Z
---

`crontab -l | sed "s#패턴#치환#" | crontab -` 패턴에서 경로에 `/`가 들어간 문자열을 sed 구분자로 잘못 고르면 sed가 파싱에러로 죽고, sed의 빈 stdout이 그대로 `crontab -`에 파이프되어 **크론탭 전체가 삭제**된다. 2026-09-06 이 사고로 62개 크론잡이 순간 전삭제됐다가, 작업 직전에 떠둔 백업 파일로 즉시 복구함.

**Why:** 파이프 체인에서 중간 명령이 실패해도 쉘은 계속 진행하고, `crontab -`은 표준입력이 비어있으면 정말로 크론탭을 빈 것으로 덮어쓴다. set -o pipefail이 없는 한 이 실패는 조용히 통과된다.

**How to apply:**
- 크론탭을 수정하기 전 반드시 `crontab -l > 백업파일` 먼저 뜬다(이미 습관이지만, 파이프 명령 자체의 실패를 막지는 못함).
- sed로 크론탭을 직접 고치지 말고, Python으로 `crontab -l` 결과를 문자열로 받아 **정확히 원하는 줄이 1번만 매치되는지 assert** 하고, **치환 후 줄 수가 그대로인지 assert**한 다음에만 `crontab -`에 넣는다(이번에 사용한 방식).
- 혹은 `crontab -l | sed ... ` 실행 후 `crontab -l`로 결과 줄 수를 즉시 검증하고, 이상하면 곧바로 백업으로 원복한다.
- sed 구분자는 경로(`/`)가 포함된 문자열을 다룰 때 `#`처럼 텍스트에 안 나올 문자를 고르되, 치환 문자열 안에도 그 구분자가 없는지 확인한다.

관련: [[project_toss_integration]]

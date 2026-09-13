---
name: project_11st_full_delete_false_success_2026-09-13
description: "11번가 임시 대량삭제 스크립트가 클릭 성공=삭제완료로 오판, 잔여검증 누락으로 거짓 성공 로그/DB기록"
metadata: 
  node_type: memory
  type: project
  originSessionId: 75734676-9be3-4dc6-8142-3bcecf154617
  modified: 2026-09-13T02:50:02.144Z
---

2026-09-13 tmxkzhfldk7(외 tmxkqlwus13/tmxkzhfldk6/tmxkzhfldk8) 11번가 상품 전량삭제 시도 중, 로그(`/tmp/full_delete_5accounts.log`)는 tmxkzhfldk7 "삭제시도 5056/5056 목표달성"으로 기록했으나 직후 재크롤 결과 **4695개가 실제로 남아있었음**(완전 삭제 아님).

**근본원인**: 이전 세션에서 작성한 1회성 스크립트(파일 미보존, `.claude/file-history`에서 발굴)의 `delete_chunk_500()`이 정식 모듈 `crawlers/eleven_loss_delete.py`의 헬퍼(`_select_all`,`_click`,`_clear_popups`,`_mark_deleted`)만 재사용하고, **핵심 안전장치인 "잔여 0 검증"을 빼먹음**. `선택상품삭제` 클릭 + 확인 alert 수락만 되면 바로 `return 'deleted'` → 즉시 `_mark_deleted()`로 `St11LossDeleted`에 "삭제완료" 기록. 실제 그리드 재검색으로 잔여개수 확인하는 절차가 전혀 없었음.

정식 모듈(`_process_group`)에는 이미 이 문제로 인한 안전장치가 있었음: `res['deleted'] = (remaining == 0)`(클릭여부가 아닌 잔여0 검증으로 성공판정, [[project_11st_loss_delete_selectall_bug]] 사고 이후 추가됨). 임시 스크립트가 이 검증을 누락하면서 **동일 유형의 사고가 재발**.

**교훈**: 11번가 삭제/판매중지처럼 파괴적이고 되돌릴 수 없는 작업의 1회성 스크립트를 새로 짤 때, 기존 정식 모듈의 헬퍼 함수만 가져다 쓰지 말고 **검증 로직(잔여 재확인)까지 반드시 함께 가져오거나 재구현**해야 함. 클릭 성공/alert 수락은 절대 "실제 반영"의 증거가 아님(참고: [[project_11st_suspend_processing_delay]] 성공해도 반영까지 지연되는 패턴도 있어 클릭 직후 판정은 이중으로 위험).

**현재 상태(2026-09-13, 미해결)**: tmxkzhfldk7 등 4개 계정 삭제가 부분적으로만 반영된 상태로 중단. 사용자가 수동으로 나머지 삭제 진행 중. `St11LossDeleted`의 오늘자 기록(tmxkzhfldk7 5056건 등)은 신뢰 불가 — 실제 반영 여부와 무관하게 클릭 시점에 무조건 기록됨.

관련: [[project_11st_loss_delete]], [[project_11st_loss_delete_selectall_bug]], [[feedback_verify_before_reporting_stopped]]

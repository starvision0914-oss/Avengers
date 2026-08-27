---
name: project_lcode_progress_pct_bug
description: L코드 도매마트 조회 진행상황 텔레그램의 퍼센트가 항상 100%로 오표시되던 버그와 수정 내용
metadata: 
  node_type: memory
  type: project
  originSessionId: 2bb86c91-ac05-4c15-bc80-5a88bc63e555
  modified: 2026-08-27T03:18:05.625Z
---

`notify_lcode_progress.py`(1시간마다 텔레그램)가 보여주는 진행률이 "이번 재점검에서 몇 % 처리했나"가 아니라
"LCodeStatus에 기록이 한 번이라도 있는 코드 비율"을 세고 있어서, 대부분 코드가 예전에 이미 한 번씩
조회된 적이 있는 상황에서는 실제 재점검 진행과 무관하게 거의 항상 "100.0%"로 찍혔음.

2026-08-27: 사용자가 정각(12:00) 문자를 보고 "완료됐다"고 오인(실제 문구는 "실행 중 · 103,718/103,718건
(100.0%)"— 상태 자체는 실행중이라 적혀있었지만 퍼센트가 100%라 착각). 실제 진행률은 크롤러 자체 로그
(/tmp/check_domemart_lcodes.log) 기준 61,125/105,197건(58%)이었음.

**수정**: `_real_run_progress()`를 추가해 `/tmp/check_domemart_lcodes.log`의 마지막
"N/M 진행 중..." 또는 "완료: N/M 처리" 줄을 직접 파싱해 진짜 진행률을 표시하도록 변경(2026-08-27).
로그 파싱 실패 시(최초 실행 등)에만 예전 방식(LCodeStatus 존재여부 비율)으로 폴백.

**Why**: 사용자가 텔레그램 알림을 신뢰하고 완료 여부를 판단하는데, 구조적으로 항상 100%가 뜨는 지표는
신뢰할 수 없는 정보 — 크롤 진행상황처럼 사용자에게 직접 노출되는 자동 보고는 "그럴듯해 보이는 숫자"가
아니라 실제 근거(로그/DB)와 일치하는지 반드시 검증해야 함. [[feedback_crawl_problem_check_thoroughness]]
[[feedback_verify_before_reporting_stopped]]와 같은 맥락 — 자동보고 자체의 정확성도 항상 의심할 것.

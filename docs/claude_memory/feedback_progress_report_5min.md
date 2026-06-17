---
name: feedback_progress_report_5min
description: 장시간/크롤 작업 중 사용자는 5분마다 진행상황 보고를 요구함
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4b81a2de-3c94-48d2-a767-9d7a7a3fd4ae
---

사용자는 크롤링 등 장시간 작업 진행 시 **5분마다 진행상황을 보고**하라고 요구함(2026-06-12). "무조건" 강조.

**Why:** 크롤러가 캡차/로그인 실패로 멈춰도 사용자가 모르고 방치되는 일이 있었음. 침묵하면 문제를 늦게 안다.

**How to apply:** 장시간 크롤·복구 작업을 돌릴 때 ScheduleWakeup(~5분) 또는 /loop로 주기 보고. 단발 질문엔 불필요. 문제 발견 시 "정상"에서 멈추지 말고 근본원인까지 파고들어 먼저 보고. [[feedback_crawling_rule]] [[project_gmarket_captcha_login]]

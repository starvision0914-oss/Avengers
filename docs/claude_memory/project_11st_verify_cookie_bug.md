---
name: project_11st_verify_cookie_bug
description: "11번가 \"OTP완료인데 인증안됨\" 정체 — verify가 쿠키 미저장(수정) + 도구는 OTP24h로 인증판정"
metadata: 
  node_type: memory
  type: project
  originSessionId: e76d08ca-b676-492c-8ef3-735797020404
---

11번가 계정이 "OTP완료라고 나오는데 인증 안됨"으로 보이는 2가지 원인 (2026-06-21 규명·수정):

1. **verify_11st_logins 쿠키 미저장 버그(수정완료)**: OTP 로그인 성공 시 eleven_crawler._do_login이 last_otp_at만 갱신하고, verify 커맨드가 성공 후 _save_cookies를 호출 안 해 인증 세션이 버려졌음. → last_otp_at(="OTP완료")만 갱신되고 cookie_saved_at은 옛날 그대로 → 세션 헛돎. 수정: verify_11st_logins.py 성공 분기에 _save_cookies(driver, acct) 추가 + import. (일반 크롤 eleven_crawler line 1221은 원래 저장함 — verify만 버그)

2. **사용자 "03.11번가" 도구는 OTP 24h 기준으로 인증판정**: 11번가 OTP는 24시간 유효라, OTP가 24h 지나면 도구가 "인증 안됨" 표시. 하지만 **실제 크롤은 쿠키(72h)로 동작**하므로 OTP 만료여도 크롤 정상. 예: dlrmsgh014는 쿠키 32분전·크롤 32분전 성공인데 OTP가 24h25m 지나 "인증안됨" 표시됨(실제 정상). 근본해결은 도구가 쿠키(72h) 기준 판정하거나, OTP는 24h마다 만료(treadmill)임을 인지. 전계정 강제재검증은 24h뒤 또 만료 + OTP도배라 비효율(앞서 'OTP 줄이기' 목표와 상충).

관련 [[project_11st_otp_notification]] [[project_11st_tmxkzhfldk8_crash]] [[feedback_progress_report_5min]]

---
name: project_lotteon_gmarket_shared_loginid
description: tmxkql111/tmxkql222는 지마켓+롯데온 공용 로그인ID — 플랫폼 헷갈려 오류 오보고한 사례
metadata: 
  node_type: memory
  type: project
  originSessionId: c1ae2553-bee6-4466-aefb-6a0a06251f25
  modified: 2026-08-23T13:32:55.700Z
---

`tmxkql111`, `tmxkql222` 로그인ID는 지마켓(CrawlerAccount)과 롯데온(LotteonAccount) 양쪽에 동일하게 등록되어 있음(계정 자체는 별개 row, id만 공유 아님 — 로그인 아이디 문자열이 겹침).

**있었던 혼동(2026-08-23)**: 이 로그인ID에서 "로그인 오류"를 지마켓 문제로 보고했으나, 실제로는 [[project_lotteon_integration_attempt]]에서 이미 알려진 **롯데온 2FA 토큰 확보 실패**(`/tmp/manual_lotteon_products_now.log`, 08:44 `[lotteon:tmxkql111] 2FA 요구 — 자동화 불가, 스킵`)였음. 같은 시간대 지마켓 로그(`cron_gmarket_cost.log` 등)에서는 두 계정 모두 정상 로그인·수집 확인됨.

**Why:** 로그인ID 문자열만 보고 플랫폼을 착각하기 쉬움. 특히 tmxkql111/222는 롯데온이 2FA로 계속 실패 중인 계정이라 착시가 잘 남.
**How to apply:** 이 두 로그인ID 관련 오류 보고 전에는 반드시 로그/DB에서 platform(gmarket vs lotteon)을 먼저 명시적으로 확인할 것. 로그 파일명이나 `[platform:login_id]` 형태 prefix로 구분.

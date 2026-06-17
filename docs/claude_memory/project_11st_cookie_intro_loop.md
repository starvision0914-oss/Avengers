---
name: project_11st_cookie_intro_loop
description: 11번가 광고비 대량 다운로드실패 근본원인 — 쿠키 무효 오판(/view/intro) + implicit_wait hang
metadata: 
  node_type: memory
  type: project
  originSessionId: 354070d6-c8cd-4591-8ad8-ac8c18636875
---

2026-06-11 진단·수정. 11번가 광고비(crawl_11st_cost) 대량 "다운로드 실패"의 근본원인 두 가지:

1. **쿠키 무효 오판 무한루프** (핵심): `_try_cookie_login`이 URL에 `soffice.11st.co.kr`만 있으면 성공으로 판정했다. 쿠키가 만료되면 `/view/main`이 **`/view/intro`(로그아웃 상태 셀러오피스 랜딩, '로그인하기'·'가입하기' 링크 페이지)**로 리다이렉트되는데 도메인은 그대로라 오판 → 풀로그인/OTP가 영영 안 돎 → 오피스 0/0/0, cost 페이지(view/8201)도 intro로 가서 iframe 없음 → 다운로드 실패. 게다가 로그아웃 상태 쿠키를 재저장해 cookie_saved_at만 갱신 → 한번 만료되면 영영 복구 안 되는 doom loop. **수정**: `/view/intro`면 False, `soContent` 엘리먼트 존재할 때만 성공 인정.

2. **implicit_wait hang**: browser.py `create_driver`가 `implicitly_wait(10)`을 거는데, 이 크롤러는 명시적 WebDriverWait/짧은폴링(_get_text)에 의존. 섞이면 미발견 요소마다 find_elements가 10초씩 헛대기 → 오피스 수집 계정당 수 분 hang. **수정**: eleven_crawler `_new_driver`에서 `implicitly_wait(0)` (eleven_loss_delete와 동일 처방).

검증: jinag7461 엔드투엔드 OK — 쿠키만료감지→풀로그인→OTP(폰알림 5초 자동)→/view/main→647건 저장. OTP는 [[project_11st_otp_notification]] 대로 정상.

후속: 다수 계정이 같은 무효쿠키 상태라 첫 복구 회차에 계정마다 OTP 1회 필요(이후 72h 재사용). [[project_11st_ip_block_prevention]] 동시크롤 금지·페이싱 유지. 미커밋 상태(4/8 이후 전부 uncommitted).

---
name: project_gmarket_captcha_login
description: 지마켓 ESM 로그인 이미지캡차(자동입력방지문자) 대응 — 사람이 1회 풀어 쿠키재발급 후 크롤러가 쿠키재사용
metadata: 
  node_type: memory
  type: project
  originSessionId: 4b81a2de-3c94-48d2-a767-9d7a7a3fd4ae
---

지마켓/ESM 로그인이 **이미지 캡차(자동입력방지문자)** 로 막힐 때(IP변경·봇탐지 트리거, 2026-06-12 발생). 캡차는 로그인 버튼 1회 클릭해야 등장(초기 화면엔 id/pw/체크박스만).

**원인:** 크롤러는 쿠키재사용 우선(`gmarket_cost_crawler._try_cookie_login`, TTL 72h) → 쿠키 무효화되면 풀로그인(`_esm_login`) 폴백 → 캡차 만나 전계정 실패.

**해법(정식·안전, 우회 아님):** 사람이 캡차 1회 직접 풀어 로그인 → `_save_cookies`로 DB저장 → 크롤러는 쿠키로 동작(캡차 안만남). **캡차 자동풀이(OCR/외부서비스) 금지 — 계정정지 위험.**

**도구:** `backend/manual_login_relay.py [login_id]` — Xvfb:99 크롬으로 id/pw입력+로그인클릭→캡차 스크린샷을 프론트 public(`/captcha.png`, Vite 5173 서빙)+텔레그램으로 전송→`/tmp/captcha_pending` ON. 사용자가 텔레그램 답장(또는 `/tmp/captcha_answer.txt`)으로 캡차문자 주면 입력·제출·쿠키저장·검증(`_try_cookie_login`). 텔레그램훅은 `telegram_command_bot.py`에 pending시 답장을 캡차로 인식하도록 추가됨.

**주의:** 동시크롤 금지(락 `/tmp/avengers_crawl_chrome_gmarket.lock`). Xvfb 강제종료시 `/tmp/.X99-lock`·`/tmp/.X11-unix/X99` 잔존→재기동 실패하니 삭제. 정리 pkill 패턴에 'manual_login_relay' 넣으면 쉘 자기자신 kill됨 주의. [[feedback_crawling_rule]] [[project_11st_ip_block_prevention]] [[feedback_progress_report_5min]]

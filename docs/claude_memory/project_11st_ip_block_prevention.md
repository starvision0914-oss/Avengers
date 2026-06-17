---
name: project_11st_ip_block_prevention
description: "11번가 IP 차단 방지 — 동시 크롤 절대 금지(전역 락), 사전 접속점검"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8cfc5d0f-21a9-45a7-8307-c0179c4ca099
---

2026-06-09 11번가가 우리 서버 공인IP(115.23.154.209)를 **방화벽 차단**(ping 100% 손실, 전 도메인 타임아웃, 타 사이트는 정상). 원인: **나의상품 동기화(OpenAPI 수백페이지) + 상품ROAS 백필(셀레늄)을 동시 실행** → 요청 폭주. 약 30~40분 후 자동 해제(일시적, 영구정지 아님). 동적IP인데 재부팅해도 같은 IP 나옴.

**Why:** 동시 크롤이 IP 차단의 직접 원인. IP 차단은 우리 자체 쿨다운(`/tmp/avengers_11st_blocked_until`, is_blocked)과 무관하게 11번가가 거는 것 — 실제 확인은 live_reachable()(www.11st.co.kr HTTP) 또는 ping이 아니라 HTTP로(11번가는 ICMP 차단).

**How to apply:** 강화 완료 — `eleven_block_guard.preflight(name)`: ①is_blocked ②live_reachable HTTP ③`acquire_global_lock`(전역 단일 크롤, /tmp/avengers_11st_global_crawl.lock, 죽은PID 자동회수). 모든 11번가 크롤 진입점이 호출하고 끝에 `release_global_lock()`: eleven_crawler.run_all_accounts(광고비), eleven_product_daily.run_all_accounts(상품ROAS), eleven_my_product_service.sync_focused_accounts(동기화). 페이싱: OpenAPI PAGE_SLEEP 8~12초, 상품ROAS 계정당 3회 재시도+차단시 자동대기. **절대 두 크롤 동시 실행 금지.** [[feedback_crawling_rule]] [[project_11st_transient_fails]]

매시간 차단 체크: scripts/check_11st_block_telegram.sh (cron 0 * * * *) → 실제 HTTP 접속 테스트 후 텔레그램. 텔레그램 명령봇: PM2 avengers-telegram-bot (/차단 /매출 /커버리지 /크롤중지 /광고비크롤 /상품크롤).

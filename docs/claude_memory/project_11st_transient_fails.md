---
name: project_11st_transient_fails
description: "11번가 수집 실패의 ~94%는 일시적(다음 회차 자동회복), 알림은 연속2회+1일1회로 게이팅"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8cfc5d0f-21a9-45a7-8307-c0179c4ca099
---

11번가 광고비(`crawl_11st_cost`)·상품(`eleven_product_crawler`) 수집 실패의 대부분은 **일시적**이다. 실측(2026-06-08): 3일간 성공389/실패35(~8%), 실패 계정-카테고리의 **94%(134/143)가 다음 회차에 자동 성공으로 회복**. 빈 계정/크롤러 고장 아님 — 11번가 soffice 서버의 일시적 지연·거부 + 빡빡한 타임아웃 + 옛 파일 캐시가 원인.

대표 실패 문구와 진짜 원인:
- `다운로드 실패`(cost): 광고 iframe(8201/8301) 타임아웃 → 15초→**30초**로 완화
- `대량엑셀 조회불가`: soffice 세션만료/일시거부 (self-heal 재로그인 있음)
- `파일이 오늘자 아님`: 11번가가 옛 생성본 반환 → **생성요청 강제 재트리거 최대 2회**
- `생성완료 타임아웃`: 상품 9천개대 대형계정 엑셀 생성 지연 → 폴링 4분→**6분**(GEN_POLL_ROUNDS 24)
- 셀러포인트 0바이트 = 해당기간 데이터 없음(정상), ERROR 아님

**알림 게이팅**: `guard.notify_failure(acct,category,msg,name)` / `guard.notify_success(acct,category)` (apps/cpc/eleven_block_guard.py). 연속 `ALERT_AFTER_CONSEC=2`회 실패(=회복못함) + 직전알림 후 24h 경과일 때만 텔레그램 발송. 상태파일 `/tmp/avengers_11st_alert_state.json`. → 1회 일시실패는 무음, 진짜 지속실패만 알림.

관련: [[feedback_crawling_rule]] (사람처럼 페이싱+3회실패 중지), [[project_sales_revenue_def]]

---
name: feedback_crawl_problem_check_thoroughness
description: 크롤링 문제있냐고 물으면 상태필드만 보지 말고 최근 3일 로그 전체를 뒤져서 문제사항을 다 보고할 것 — 모든 세션/창에서 항상 적용
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c1ae2553-bee6-4466-aefb-6a0a06251f25
  modified: 2026-08-23T15:35:42.341Z
---

사용자가 "(지마켓/11번가/롯데온/스마트스토어) 크롤링 문제있어?" 라고 물으면, `CrawlerAccount.crawling_status` 같은 DB 상태필드 하나만 보고 "문제없다"고 답하면 안 된다. **반드시 해당 플랫폼의 최근 3일치 크롤 로그 전체를 뒤져서(grep) 발생했던 문제사항을 빠짐없이 정리해서 보고할 것.**

**Why:** 2026-08-24 확인 결과 `crawling_status` 필드는 지마켓 상품수집 크롤러(`gmarket_product_crawler.py`)의 로그인실패/iframe진입실패/API페이징중단 등 실패 케이스에서 전혀 갱신되지 않음(기본값 '정상'에서 안 바뀜) — 이 필드만 보고 반복적으로 "문제없다"고 오답한 전례가 있음([[project_gmarket_ad_report_status_fixes]] 계열의 "상태표시 오판" 패턴과 동일 유형). 즉 상태필드는 실제 크롤 건강도를 반영하지 못하는 경우가 있으므로, 로그를 직접 확인하지 않으면 거짓 안심을 줄 수 있음.

**How to apply:**
- 확인 대상 로그(플랫폼별): 지마켓 `/tmp/cron_gmkt_products.log`(상품수집), `/tmp/cron_gmarket_cost.log`류(광고비), `/tmp/delete_loss_gmarket.log`(적자삭제) 등. 11번가는 `/tmp/cron_11st_night.log`, `/tmp/delete_loss.log` 등. 롯데온·스마트스토어도 대응 로그 확인.
- 최근 3일 범위로 필터링(로그가 날짜 로테이션 없이 누적되므로 [[project_cron_log_no_rotation]] 참고 — 타임스탬프 직접 파싱해서 최근 3일만 추출).
- "로그인 실패", "iframe 진입 실패", "API 오류", "JSON 파싱 실패", "오류:", "KeyboardInterrupt", "타임아웃" 등 에러 패턴 grep.
- 단순 "문제없음" 한마디로 끝내지 말고, 발견된 문제를 항목별로(어떤 계정/몇 번/언제) 나열해서 보고.
- **이 규칙은 세션이 바뀌거나 새 대화창에서 물어봐도 항상 적용**되어야 함 — 사용자가 명시적으로 요청한 영구 규칙.
- **"확인해드릴까요?" 같은 재확인 질문 하지 말고 바로 로그 뒤져서 답할 것.** "문제있어?"라는 질문 자체가 곧 실행 트리거임(2026-08-24 사용자가 재확인 질문을 거부하며 명시).

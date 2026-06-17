---
name: project_gmarket_adcost_keyword_combined
description: 지마켓 상품별광고비+키워드 통합 크롤(매일 08:00) — 로그인 1회로 둘 다 수집
metadata: 
  node_type: memory
  type: project
  originSessionId: 4b81a2de-3c94-48d2-a767-9d7a7a3fd4ae
---

지마켓 **상품별 광고비(ad_report)와 ROAS≥200 키워드 수집을 한 세션에 통합**(2026-06-13). 같은 ad.esmplus.com cpc/report/groupReport 페이지라 **계정 로그인 1회로 둘 다** 수집 → IP/캡차 위험·로그인 절반.

**구현:** `gmarket_ad_report_crawler.run(..., with_keywords=True)` — 계정 광고비 저장 후, 같은 driver로 그 계정 당월 ROAS≥200(conv>0 & conv*100/cost≥200) 상품번호에 `crawl_account_keywords(driver, ...)` 호출(키워드 크롤러 재사용 함수). 키워드 실패는 광고비 저장에 영향 없게 에러 격리. 명령 옵션 `crawl_gmarket_ad_report --with-keywords`.

**스케줄:** cron `cron_gmarket_ad_report_kw.sh` 매일 **08:00**(09:00 잔액크롤 전 종료 목표, 14계정 ~28분). 단독 키워드 cron(03:30)은 제거함(중복). 검증: rejoice999 1계정 — 광고비(CPC1021/AI103)+키워드6 한 로그인 OK.

**주의:** 수동 락 금지(guard.preflight가 전역락 자동관리, 수동락 만들면 self-스킵 — [[project_gmarket_keyword_lock_gotcha]]). [[project_gmarket_ad_product_report]] [[project_gmarket_keyword_report]] [[feedback_crawling_rule]]

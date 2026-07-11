---
name: project-osan-kospi-news-series
description: "오산 홈페이지 코스피 종목별 \"최신 뉴스 3가지\" 블로그 시리즈 진행상황 및 재개 방법"
metadata: 
  node_type: memory
  type: project
  originSessionId: 22f4c8ff-2f78-4400-9e88-27bf11b821dd
---

오산시 소개 홈페이지(/home/rejoice888/homepage, WP-CLI `/home/rejoice888/bin/wp`)에 "경제뉴스" 카테고리(term_id 24)로 코스피 상장기업별 "최신 뉴스 3가지" 요약글을 발행 중. 2026-07-11 기준 **138/200개** 발행 후 사용자 요청으로 **중단**.

**Why:** 사용자가 "그만물어보고 200개 되면 물어봐" → 이후 토큰 비용 우려로 [[feedback_ask_before_token_heavy_work]] 확인 후에도 "104개 이어서 계속"이라 승인했으나, 138개 시점에 "여기까지 중단하고 메모리 저장해줘"로 명시 중단 지시.

**진행 방식(재개 시 그대로 따를 것):**
- 재사용 헬퍼: `/home/rejoice888/.claude/jobs/22f4c8ff/tmp/kospi_helper.php` (이 job 임시폴더는 세션 종료 시 삭제될 수 있으니, 재개 전 존재 여부 확인 필요 — 없으면 이전 발행된 post의 wp_insert_post 구조를 참고해 재작성)
- 회사별 스크립트: `post_<slug>.php`가 helper를 require하고 `publish_kospi_post([...])` 호출 (title/keyword/slug/meta_desc/intro/sections/table_rows/faq/summary/refs/related_link/img_colors)
- 실행: `wp eval-file post_<slug>.php --path=/home/rejoice888/homepage`
- 검증: 출력된 글자수(1500자 이상)·키워드 등장횟수(1회 이상) 확인
- 총계 확인: `wp post list --category_name=경제뉴스 --post_type=post --format=count --path=/home/rejoice888/homepage`

**마지막 발행:** 매일유업 (ID 1074, 138번째). **다음 후보로 리서치까지 마쳤으나 미발행:** 남양유업 (2026년 1분기 영업이익 5억원, 전년比 572% 증가, 5년 적자 탈출 — WebSearch 완료, post 파일 미작성).

**How to apply:** 사용자가 재개를 요청하면("이어서 해줘" 등) 138개 지점부터 남양유업으로 이어서 발행. 목표 200개까지는 [[feedback_ask_before_token_heavy_work]] 원칙상 재개 자체도 먼저 확인받는 것이 안전(이전엔 200개 목표까지 승인받았으나, 이번 중단 지시가 최신 지시이므로 재개는 다시 확인).

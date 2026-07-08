---
name: project-11st-office-point-zero-bug
description: "11번가 셀러오피스 메인페이지 개편으로 오피스현황(셀러포인트/캐시/상품수) 절대경로 XPath 전부 깨짐 → 0원으로 조용히 저장되던 버그, 라벨기반 탐색으로 수정"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6b826e73-696d-468f-b925-82fa47cfc353
---

2026-07경 11번가 셀러오피스(soffice.11st.co.kr/view/main) 페이지 레이아웃이 개편되며 `_OFFICE_XPATHS`(crawlers/eleven_crawler.py)의 절대경로 XPath가 전부 어긋남. `_get_text`가 미검출 시 빈 문자열을 반환하고 `_parse_int_safe`가 이를 0으로 바꿔 예외 없이 `cash=0, point=0, products=0`을 저장 → 크롤러 로그엔 "오피스OK"로 찍혀 있어 정상처럼 보였음.

실제로는 계정이 정상이고 셀러포인트/캐시 잔액도 있었음(예: tmxkql21 실잔액 156,883원, ElevenCostHistory 거래 balance와 일치). 확인된 영향 계정: tmxkql21, tmxkql27, tmxkzhfldk6, tmxkzhfldk7 (2026-07-08 기준, 최근 6시간 데이터로 전수조사).

**원인**: 페이지의 두 위젯이 마크업 패턴이 다름 — 정산(셀러캐시/셀러포인트) 위젯은 `div.title`와 `div.count`가 li의 형제(sibling), 상품(판매중/판매금지/판매중한도) 위젯은 `span.count`가 `div.title` 내부 자식(child)으로 중첩. 절대 인덱스 XPath는 둘 다 신뢰 불가.

**수정**: `_office_val(driver, label)` 헬퍼 추가 — 라벨 span 텍스트가 속한 `li`를 앵커로 잡고 그 안에서 첫 `class contains 'count'` 요소의 `<a>` 텍스트를 가져옴(두 마크업 패턴 모두 커버). 핵심 3항목(셀러캐시/셀러포인트/판매중)이 전부 미검출이면 조용히 0 저장하지 않고 RuntimeError를 던져 "오피스 수집 실패" 로그로 남기도록 안전장치 추가. ad_balance/overdue/undelivered/fulfillment/shipping/inquiry는 신 레이아웃 위치 미확인 상태로 기존 절대경로 유지(이미 깨져있던 항목이라 회귀 아님).

**Why**: 대시보드의 11번가 "셀러포인트" 잔액(`apps/cpc/views.py:999` `e_bal = et.get('point')`)이 실제 정상 계정을 0원으로 표시해 사용자가 오판할 뻔함. 페이지 개편은 예고 없이 일어나므로 절대경로 XPath는 이런 식으로 계속 깨질 수 있음 — 향후 유사 증상(특정 계정만 오피스 수치 0, 로그는 성공) 발생 시 우선 라벨 기반 셀렉터로 전환하고, 핵심 항목 전부 미검출 시 예외 처리로 알림이 뜨게 하는 패턴을 재사용할 것.

**How to apply**: "OO계정 광고비/포인트/상품수가 0으로 나온다" 류 문의가 오면 (1) ElevenCostHistory의 실제 balance/거래 내역으로 진짜 잔액부터 대조, (2) ElevenMyProduct 등록상품 수와 오피스 스탯 products를 비교해 스크래핑 결함인지 실제 0인지 구분, (3) 절대경로 XPath가 원인이면 라이브 쿠키로 실제 DOM을 떠서 재확인 후 라벨기반으로 교체.

관련: [[project_11st_myproduct_status_source]], [[project_11st_cookie_intro_loop]], [[project_crawl_lock_parser_bug]]

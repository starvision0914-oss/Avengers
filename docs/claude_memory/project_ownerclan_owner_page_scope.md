---
name: project_ownerclan_owner_page_scope
description: "/ownerclan(예비상품)과 /owner(오너클랜크롤러) 페이지 구분, /owner의 상품자동수집은 보류 상태"
metadata: 
  node_type: memory
  type: project
  originSessionId: a2d588dd-a8ef-4b9d-9ed0-0fd113039ab2
---

**두 페이지를 혼동하지 말 것**:
- `/ownerclan` = 예비상품(OwnerclanProductsPage, workspace="reserve") — 상품 매칭용 스테이징 공간. [[project_ownerclan_reserve_pipeline]] 참조, 기존에 정상 운영 중.
- `/owner` = 오너클랜크롤러(OwnerclanCrawlerPage) — 오너클랜 정식 GraphQL API 연동 페이지. [[project_ownerclan_api_discovery]] 참조.

**`/owner` 페이지의 현재 상태(2026-07-14 사용자 확정)**:
- **계정정보 크롤링("계정정보 새로고침" 버튼, account-info-crawl)만 지시된 상태** — 정상 동작 중.
- **상품 자동수집("새 상품 가져오기" 버튼, api-crawl → crawl_ownerclan_api 커맨드)은 아직 실행 지시한 적 없음. 보류 상태.** 실행/테스트 금지 — 사용자가 명시적으로 다시 지시할 때까지 건드리지 않을 것.
- DB 확인 결과 task_type='api_crawl' 레코드가 한 번도 생성된 적 없음(2026-07-14 시점) — 이건 버그가 아니라 애초에 지시한 적이 없어서였음. 예비상품 계정정보의 last_synced_at(7/11)은 개발 중 터미널에서 직접 테스트했던 흔적.

**코드 개선 사항(적용은 했으나 미실행)**: `crawlers/ownerclan_api_crawler.py`의 `crawl_new_items`가 매번 전체 카탈로그(15만+건, 페이지당 200개=750+페이지)를 처음부터 재스캔하는 구조라 매우 느림(추정 20~30분+). dateDesc 정렬 특성을 이용해 "신규 0건 페이지 2회 연속 시 조기종료"하는 로직을 추가해뒀음 — 나중에 이 기능을 켤 때 참고. 상품자동수집 보류 지시가 있었으므로 이 개선사항도 실행/검증 보류.

관련: [[project_ownerclan_reserve_pipeline]], [[project_ownerclan_api_discovery]]

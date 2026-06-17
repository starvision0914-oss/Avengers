---
name: project_11st_loss_delete
description: "11번가 적자상품 자동삭제(셀러오피스) 구현·운영 함정 — iframe, 백그라운드 실행, 동시크롤 금지"
metadata: 
  node_type: memory
  type: project
  originSessionId: 01fbf4ca-8075-41d1-994d-3cdbad6cd8fe
---

11번가 적자상품 판매중지·삭제 자동화 (`crawlers/eleven_loss_delete.py`, `delete_loss_products` 커맨드).

- 상품관리 UI는 `/view/8006` 안의 **iframe `Content_ifrm_8006`** 에 있음 → 셀렉터 조작 전 반드시 iframe 진입.
- 셀렉터: 사용자제공 `jqxWidget*`/`ext-gen*` 는 세션마다 바뀌는 자동ID라 신뢰불가 → **텍스트 기반 폴백**(`//a[.='판매중지']`, `//a[contains(.,'선택상품')and contains(.,'삭제')]`) 사용. prdNo=textarea, btnSearch=button.
- 플로우: 1단계 판매금지=검색→전체선택→삭제 / 2단계 판매중·판매중지·품절=검색→전체선택→판매중지→삭제. 상품번호는 **숫자만**(비숫자 섞이면 안 됨). 삭제분은 `St11LossDeleted`로 비고'삭제완료' 기록.
- mode='validate'(기본, 파괴적 클릭 없음) / 'real'(실삭제). 실삭제는 되돌릴 수 없음.

**현재 상태(2026-06-10 미완·보류):** 로그인·iframe·검색·셀렉터·타이밍(420초 해결)·판매중분리 OK. select_all은 **누르면 안 됨**(검색결과가 이미 전체체크 상태라 누르면 해제됨→"선택된 항목 없음"). 비고기록은 '잔여0 검증'으로 게이팅(클릭만으로 기록 금지). **남은 블로커: "신규셀러 패키지 프로모션" ExtJS 모달(x-panel x-layer)이 그리드를 마스크 → 판매중지/삭제 클릭 무효.** 이 프로모를 페이지 진입 직후 닫아야(x-tool-close, stale 재시도) 동작. rejoice345 실제 삭제는 아직 안 됨(데이터 안전).

**운영 함정(중요):**
1. 로그인 1회 ~66초 → real 1계정이 도구 타임아웃(수백초) 초과. **반드시 백그라운드(detach)+로그파일로 실행**하고 폴링. 포그라운드 timeout으로 죽이면 finally 미실행 → 고아 크롬+죽은 락 잔존.
2. `crawl_11st_cost` 등 다른 11st 크롤러는 **전역락(preflight)을 안 잡음** → 적자삭제 preflight가 동시실행을 못 막는 갭 존재. 삭제 실행 전 `pgrep crawl_11st_cost` 등으로 직접 확인 후, 끝난 뒤 실행. [[project_11st_ip_block_prevention]]

관련: 영구정지 계정 제외 [[project_11st_perma_banned]], 매출/적자 판단 [[project_11st_sales_match_global]]

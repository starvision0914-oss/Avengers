---
name: project_11st_jqxgrid_realtime_verify
description: "11번가 나의상품(/view/8006) 실시간 상태를 정확히 검증하는 방법 — jqxGrid('getrows') JS API 직접호출"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2b25ce04-399d-4dcc-bcb0-8937fe2c40ef
  modified: 2026-08-26T04:10:03.639Z
---

11번가 셀러오피스 상품관리(/view/8006, iframe Content_ifrm_8006) 그리드는 jqWidgets(jqxGrid) 기반. 실시간 상태(판매중/판매중지 등) 검증 시도 중 두 가지 함정을 확인(2026-08-26):

1. **getSellProductListJSON 직접 POST는 안 됨**: `SellProductAjaxAction.tmall?method=getSellProductListJSON&prdNo=...`를 GET/POST로 직접 호출하면 필요한 파라미터(페이지크기/검색조건 등)가 빠져 `{"TOTAL_COUNT":0,"DATA_LIST":[]}`만 반환됨. [[project_11st_excel_export_stale_status]]에 기록된 이 엔드포인트명은 맞지만 단독 재현은 실패.
2. **DOM 텍스트 파싱도 위험함**: `_paste_and_search`로 검색 후 `div[role='row']`의 `.text`를 파싱하면 "그리드 20행"이라고 나오는데, 이는 실제 검색결과 건수가 아니라 **가상스크롤(virtualization) 뷰포트 고정 행수**(항상 20으로 표시됨) — 실제 데이터가 아닌 빈 자리도 포함될 수 있고, 컬럼도 스크롤 안 된 상태면 상태/가격 컬럼 자체가 DOM에 없어서(`selStatCdVal`, `selPrc` 등이 렌더링 안 됨) 파싱 결과가 계정마다 들쭉날쭉함.

**정답(검증됨)**: 검색 실행 후(`_paste_and_search`) `driver.execute_script("return jQuery('#dvdataGrid').jqxGrid('getrows');")`로 그리드 내부 데이터모델을 직접 가져오면, DOM 렌더링/가상스크롤과 무관하게 검색된 정확한 건수만큼 전체 필드(161개)를 다 받을 수 있음. 핵심 필드:
- `prdNo`: 상품번호(문자열)
- `selStatCd`: 판매상태 코드(예: '105')
- `selStatCdVal`: `<a onclick=...><span>판매중지</span></a>` 형태 HTML — `<span>([^<]*)</span>` 정규식으로 사람이 읽는 라벨 추출
- `selPrc`: 판매가(정수)
- `selQty`: 재고수량(정수)

배치 크기는 30건까지 문제없이 한 번에 조회 가능(가상스크롤 제약과 무관).

**How to apply:** 앞으로 11번가 나의상품 실시간 상태 검증이 필요하면 이 방법을 우선 사용. `crawlers/eleven_loss_delete.py`의 `_paste_and_search`/`PRODUCT_PAGE`로 검색만 하고, 결과는 DOM이 아니라 `jqxGrid('getrows')`로 읽을 것.

---
name: project_11st_excel_export_stale_status
description: 11번가 나의상품 엑셀다운로드는 생성에 시간이 걸리는 배치 리포트라 방금 바뀐 상태변경을 못 따라감 — 상태검증은 엑셀재수집 대신 실시간 AJAX 조회 사용
metadata: 
  node_type: memory
  type: project
  originSessionId: c1ae2553-bee6-4466-aefb-6a0a06251f25
  modified: 2026-08-24T06:11:48.713Z
---

11번가 "나의상품"을 갱신할 때 쓰는 **엑셀 다운로드(파일생성요청 방식, crawl_11st_products)는 생성 자체에 시간이 걸리는 배치 리포트**라, 방금 일어난 상태변경(판매중지 등)을 바로 못 따라감을 2026-08-24에 발견. 캐시라기보다 "요청 시점 기준 리포트 생성"에 가까워서, 상태변경 직후 곧바로 받아봐도 그 변경 전 스냅샷이 나올 수 있음.

**Why:** L코드/미매칭 판매중지(총 6,795건) 실행 직후 "성공" 로그가 나왔지만, 확인차 crawl_11st_products로 재수집한 엑셀에서는 전부 여전히 "판매중"으로 나와서 "판매중지가 전혀 반영 안 됐다"고 오판(→ 나의상품 DB를 잘못 되돌리고, 정상이던 코드를 불필요하게 수정하는 등 큰 혼란). 그런데 실제 로그인 세션으로 사이트가 쓰는 실시간 AJAX(`POST soffice.11st.co.kr/product/SellProductAjaxAction.tmall?method=getSellProductListJSON&prdNo=...`, 응답의 `selStatCdVal` HTML 안 `<span>판매중지</span>` 텍스트)로 **직접 들어가서 조회**하니 전부 정상적으로 "판매중지"였음. 즉 판매중지 액션 자체는 처음부터 문제없었고, **검증에 쓴 엑셀 재수집 쪽이 시간이 걸려 못 따라간 것**이었음(사용자 확인: "엑셀 검증은 오래걸린다").

관련 발견: 판매중지 실행 시 실제 사이트가 쓰는 진짜 API 엔드포인트는 `POST soffice.11st.co.kr/product/SellProductAction.tmall?method=updateProductSelStat&prdStatCd=SELL_STOP` (body: `chkPrdNoCount=N&trgtPrdNos=콤마구분상품번호&content=`) — 향후 UI클릭 대신 이 엔드포인트를 직접 호출하는 방식(지마켓처럼)으로 전환 가능.

**How to apply(사용자 지시, 2026-08-24):** 11번가 판매중지/상태변경을 검증할 때는 시간이 오래 걸리는 엑셀 재수집(crawl_11st_products) 쓰지 말고, **반드시 로그인 세션으로 직접 들어가서 실시간 AJAX 조회**(`SellProductAjaxAction.tmall?method=getSellProductListJSON&prdNo=...`)로 확인할 것. 엑셀 기반 판단은 "아직 반영 안 됨"이라는 거짓 신호를 줄 수 있음. [[feedback_recrawl_before_nomatch_suspend]]의 "재수집 먼저"는 여전히 유효하지만(작업 대상 뽑을 때), 작업 직후 "성공했는지" 검증에는 엑셀이 아닌 실시간 조회를 쓸 것.

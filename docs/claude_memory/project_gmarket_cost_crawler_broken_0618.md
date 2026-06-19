---
name: project_gmarket_cost_crawler_broken_0618
description: 지마켓 거래내역(GmarketCostHistory) 크롤 06-18부터 응답이상으로 깨짐 — 근본원인+검증된 수정안
metadata: 
  node_type: memory
  type: project
  originSessionId: e76d08ca-b676-492c-8ef3-735797020404
---

**✅ 2026-06-19 수리 완료.** crawlers/gmarket_cost_crawler.py 재작성: _SEARCH_JS에 `X-Requested-With:XMLHttpRequest` 헤더 추가+엔드포인트 인자화, 지마켓(GmktSellBalanceUseListSearch)·옥션(IacSellBalanceUseListSearch) 2페이지 분리수집, searchAccount=평문 login_id, _norm_gmkt/_norm_iac 스키마매퍼, _save에 market 인자+market별 삭제+traded_at, _classify 소문자 cpc. 검증: rejoice794 06-18 23건 복구. 빈(존재안함) cron_gmarket_adcost_month.sh 생성(35일 재수집, 22시 대기형). OverviewView도 거래내역 기반 GmarketDashboardView로 교체(기간합산 정확)+기간프리셋.

(이력) 지마켓 판매예치금 거래내역(GmarketCostHistory) 크롤이 2026-06-18부터 전계정 0건. 06-17이 마지막 성공일.

**근본원인(라이브 확정):** ESM이 06-18경 거래내역 API에 `X-Requested-With: XMLHttpRequest` 헤더 없는 요청엔 JSON 대신 HTML 전체페이지를 반환하도록 변경 → crawlers/gmarket_cost_crawler.py의 `_SEARCH_JS` fetch에 이 헤더가 없어 "응답이상". 추가로 현행 파일은 **분실/되돌려진 깨진 버전**(IAC 토큰 단일 엔드포인트)이라 06-17을 만든 진짜 크롤러와 다름.

**검증된 정확한 호출법(rejoice794로 실측):**
- 지마켓: 페이지 `Member/Settle/GmktSellBalanceManagement?menuCode=TDM131`, 엔드포인트 `GmktSellBalanceUseListSearch`. 응답스키마: TransDate(일시)/SdMoney·TransMoney(금액)/SaveTypeNm(차감)/SdCodeNm(분류근거 "cpc광고구매")/RefNo/GoodsNo
- 옥션: 페이지 `IacSellBalanceManagement?menuCode=TDM134`, 엔드포인트 `IacSellBalanceUseListSearch`. 응답스키마: UseDate/UseAmnt/UseType/Comment/OrderNo
- **searchAccount=평문 login_id**($("#sellerId").val() 옵션값), data-token 아님(토큰은 죽음, 모든 인코딩 HTML).
- 파라미터: `page=N&limit=500&searchAccount=<평문>&searchType=&searchSDT=&searchEDT=&searchKey=0&searchKeyword=&SortFeild=TransDate&SortType=Desc&start=0`
- 헤더 필수: `X-Requested-With: XMLHttpRequest`, `Accept: application/json, text/javascript, */*; q=0.01`, `Content-Type: application/x-www-form-urlencoded`
- 실측: rejoice794 06-17 지마켓 61건(DB와 일치), 06-18 지마켓 23건(복구 데이터). 옥션은 별도 8건.

**남은 수정작업:** _SEARCH_JS에 헤더+엔드포인트인자화, _save에 market 인자+market별 삭제, gmkt/iac 스키마 매퍼 분리(TransDate→traded_at/use_date, SdCodeNm→comment, SdMoney→amount), _classify 소문자 'cpc' 처리, 본루프에서 지마켓+옥션 둘 다 수집. cron_gmarket_adcost_month.sh는 빈 파일이라 22시 cron 무동작 — 채워야 함.

**임시 대응:** 대시보드(GmarketDashboardView)는 거래내역 최종일 이후를 GmarketDepositSnapshot으로 자동보충 → 06-18 광고비 약 365K 이미 표시됨(스냅샷 추정치, 거래내역 대비 ±20%). 진단 스크립트 /tmp/diag_*.py 참조. 관련 [[project_gmarket_subaccount_token]] [[project_gmarket_adcost_source]]

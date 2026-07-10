---
name: lotteon-vat-crawler
description: "롯데온 부가세 크롤러 구축(2026-07-10) — 화면단위 세션토큰 스코프, /tax 페이지 버튼 통합"
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

롯데온 정산관리 > 부가세신고자료조회의 내부 API(`soapi.lotteon.com/settle/v1/so/vatPayment/selectVatPaymentList`)를 이용해 `crawlers/lotteon_vat_crawler.py` + `crawl_lotteon_vat` 명령으로 구축. `TaxVatMonthly(platform='lotteon')` 저장.

**핵심 함정**: 롯데온 세션 Bearer 토큰은 화면(메뉴) 단위로 스코프됨 — [[lotteon_product_crawler]]의 `_login_and_get_token`(상품관리 화면에서 딴 토큰)으로 부가세 API를 호출하면 401. 반드시 부가세 화면(정산관리>부가세신고자료조회)에 직접 진입해 그 화면의 조회버튼 클릭으로 발생하는 XHR에서 토큰을 새로 따야 함(`_login_and_get_vat_token`).

응답 필드: `pyYm`(YYYYMM), `salesTypCd`(매출유형, 실측 "A"=중개만 확인), `salesAmt`/`csrcAmt`(현금영수증)/`ccrdAmt`(신용카드)/`mphnAmt`(휴대폰)/`etcAmt`(기타). 11번가/지마켓과 달리 과세/면세/영세 구분 없음 — salesAmt 합계를 taxable_sales에 저장.

**Why**: 사용자가 롯데온 부가세도 다른 플랫폼처럼 세무 페이지에서 관리하길 원함.
**How to apply**: `/tax` 페이지 "크롤링" 버튼(`_TAX_VAT_PLATFORMS`)에 lotteon 이미 등록됨. 새 플랫폼 VAT 크롤러 추가 시 이 화면단위 토큰 스코프 패턴을 먼저 의심할 것. cron 미등록 — 월 1회 수동 버튼 사용 중.

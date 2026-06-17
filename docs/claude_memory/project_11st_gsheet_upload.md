---
name: project_11st_gsheet_upload
description: 11번가 기간별보고서(일자별27컬럼)→계정별 구글시트 업로드. eleven_period_report
metadata: 
  node_type: memory
  type: project
  originSessionId: 2652a85c-f4de-41b6-8478-ea5e69ec25ed
---

11번가 adoffice **기간별 보고서(일자별 27컬럼)** 를 계정별 구글시트(시트명=login_id)에 올리는 기능(2026-06-14 완성·검증).

**정답 형식(반드시 이것)**: 27컬럼 = 날짜·노출수·클릭수·클릭률·평균노출순위·평균클릭비용·총비용·(총/직접/간접/장바구니 각각: 전환수·전환당비용·전환금액·전환율·광고수익률). 행 = **합계 + 그 달 날짜별 1줄씩**(빈날짜는 '-'). 작음(~30행). ⚠️ 상품별/키워드별 아님 — 그거 올리면 오염+셀한도(1천만) 초과(과거 실수). 원본 형식 확인법: 안 건드린 워크시트(rejoice777 등) 헤더 보기.

**출처**: 페이지 `adoffice.11st.co.kr/sellers/{sn}/cpc/focus/report/period`(사용자가 알려줌). 실제 다운로드 API = `apis.adoffice.11st.co.kr/advertiser/account/sellers/v1/reports/daily/download?startDate&endDate&dateIntervalType=daily&selectedMetrics=...`. ※ 기존 상품ROAS의 bulkdownload(reportScope=PRODUCT_KEYWORD)와 **다른 엔드포인트**. reportScope 20개 다 400이라 그쪽으론 못 받음.

**구현**: `crawlers/eleven_period_report.py` — 검증된 UI방식(period 페이지 직접이동→당월/전월 드롭다운→조회→다운로드→UTF-16·탭 CSV 읽기) + 누락날짜 빈행삽입(fill_missing_dates) + gsheet_upload.upload_rows. 명령 `crawl_11st_period_gsheet [--accounts ...] [--no-gsheet]`. **기간: 매월 1일=전월 / 그외=당월(1일~어제)** (_period_for). 폼 XPath: 드롭다운/조회/다운로드는 파일 상단 상수.

**구글시트**: credentials = `backend/credentials.json`(서비스계정 google-sheet-ai-cpc@my-project-20032-453413), 스프레드시트 key 기본 1Yo9jG...7_-A("11번가 광고비 실적시트", 계정별 73시트). gspread 6.2.1. [[project_11st_gsheet_upload]] gsheet_upload.upload_rows(rows,title,ss).

**검증**: 1·2·3등급(jinag7460/starvis7942/rejoice666) 15행(합계+13일) 정상 업로드(2026-06-14). 상품ROAS(eleven_product_roas)의 옛 상품별 시트업로드 코드는 제거함(형식 안 맞아서).

**크론 등록 완료(2026-06-14)**: `scripts/cron_11st_product_daily.sh`(crontab 30 8 = 매일 08:30) 끝에 `crawl_11st_period_gsheet` 추가 → 매일 8시반 [상품 일별크롤 + 구글시트 업로드] 자동 수행. 즉 8:30 크론이 둘 다 함(순차, ~1시간). 로그 /tmp/cron_11st_gsheet.log.

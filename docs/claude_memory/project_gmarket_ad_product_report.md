---
name: project_gmarket_ad_product_report
description: 지마켓 CPC/AI매출업 상품별 광고비 리포트 크롤 메커니즘(calendar 기간설정+엑셀다운). 검증완료 2026-06-12
metadata: 
  node_type: memory
  type: project
  originSessionId: e6d44da8-ed92-4870-82a7-b8f14310a58c
---

지마켓 **상품별 광고비**(CPC + AI매출업) = ad.esmplus.com 광고센터 리포트 크롤. 로그인은 gmarket_crawler `_try_cookie_login/_full_login`(ad.esmplus.com) 재사용.

**CPC 상품별**: `https://ad.esmplus.com/cpc/report/groupReport`
- 탭: `SelTab.SetReportListTab('I')` (또는 a[onclick*=SetReportListTab('I')])
- 조회: `ReportList.GetTotalSearch()` / 다운로드: `ReportList.ExcelDown('Good')`
- 컬럼: 사이트·광고상품번호·연관상품번호·노출수·클릭수·클릭률·영역명·평균노출순위·평균클릭비용·**총비용(광고비)**·구매수·구매금액·전환율·광고수익률. (판매자ID 컬럼 없음 — 계정=리포트 1개)

**AI매출업 상품별**: `https://ad.esmplus.com/Remarketing/Report/GroupReport`
- 탭: `#reportsTab2` 클릭
- 조회: `RemarketingReport.Display.SearchMain()` / 다운로드: `RemarketingReport.ExcelDown.ExcelDown('goods')`
- 다운로드는 GET: `/Remarketing/Report/ReportExcel?SchStartDate=&SchEndDate=&SiteId=&SellerId=(#hdnSearchSellerId)&SiteGoodsNo=&GroupNo=&pageNo=1&pageSize=1000&page=goods`
- 컬럼: 판매자ID·그룹명·상품번호·클릭수·평균클릭비용·**총비용(광고비)**·광고상품기준(주문/구매/구매금액)·판매자기준(주문/구매/구매금액/전환율/광고수익률). 최대 1개월(31일) 조회.

**기간 설정(공통, 핵심)**: 날짜는 `#searchSDT`/`#searchEDT` 요소가 보유(조회/다운로드가 여기서 읽음). 설정법:
1. calendar 아이콘 클릭 `#dvSearchControl i.icon_calendar`
2. 프리셋 클릭 `a[data-type='TM']`(=이번달). 기타: 1D어제/7D/TW이번주/LW지난주/30D/LM지난달/90D/M직접입력/PM과거직접입력
3. 적용 `CalendarLayer.ApplyCalendarDate()`
→ '이번달'이면 당월1일~오늘 자동 설정됨(미래일 disabled).

**성능(rejoice666=공유ESM rejoice7942, 2026-06 검증)**: 로그인4s(쿠키)+CPC25s+AI26s=**계정당 ~56s**. CPC 822상품/93,390원, AI 121상품/114,213원.

주의: 공유ESM은 로그인≠리포트셀러(rejoice666 로그인→rejoice7942 리포트). CPC는 판매자ID 컬럼 없음(계정선택 필요시 MasterIdInfo/hdnSearchSellerId). 진단스크립트: crawlers/diag_ai_period.py, diag_rejoice666_june.py. [[project_gmarket_adcost_source]] [[feedback_crawling_rule]] 동시크롤금지.

**과거월 직접입력(검증 2026-06-12)**: 현재월=TM프리셋, 과거월=직접입력. 캘린더 '최근 내역 조회' a[data-type='M'](직접입력)/'과거 내역 조회' a[data-type='PM'](6개월초과용). **기간 직접연결 데이터 = `#displayDate`(readonly input, value='YYYY-MM-DD ~ YYYY-MM-DD')** → `CalendarLayer.ApplyCalendarDate()`가 ~로 잘라 `#searchSDT`/`#searchEDT`(span)에 기록 → 조회는 searchSDT/EDT를 읽음. `_set_period_month`가 displayDate.value 직접주입+ApplyCalendarDate+searchSDT/EDT 강제기록(datepicker 날짜클릭 불필요). 제약 maxDate=-1D(종료일 어제클램프), minDate=-182D(PP셀러)/-732D. crawl_account(year,month)분기, run(periods=[(y,m)..])로 한 로그인 다월순회. 커맨드 `--months '1-6'`. 진단: diag_calendar_manual.py, diag_calendar_setrange.py.
**rejoice666 2026 1~6월 백필완료(2026-06-12)**: 총10,544행(1월CPC682,616 2월570,636 3월1,568,699 4월932,833 5월212,058 6월93,390).
**전계정 2025~2026 대량백필 완료(2026-06-12)**: 대표 25계정(공유ESM 서브 223/224/235/236/starvisi 제외) × 2025-01~2026-06(18개월) 전부, **총 2,097,446행, 전계정 18/18 누락0**. ~6.5시간(03:21~), IP차단0. run()이 login_ids 없을때 서브계정 자동제외(gmarket_origin_id가 다른계정 가리키면 서브). 커맨드 `--ym-from 2025-01 --ym-to 2026-06`(해 넘는 범위). 일시적 브라우저오류(렌더러 타임아웃/AI탭 reportsTab2 못찾음)로 dlwoddbs55 3개월 빠졌다가 재크롤로 복구(멱등이라 안전). 옥션은 site컬럼(A)로 동일크롤 포함. ROAS페이지 집계상한 12→24개월로 확장(_gmkt_roas_period, 프론트 clampYear -23, 라벨 '최대 2년').

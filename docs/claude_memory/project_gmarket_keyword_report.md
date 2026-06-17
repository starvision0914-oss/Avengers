---
name: project_gmarket_keyword_report
description: 지마켓 CPC 키워드별 실적 수집(상품번호 검색)·컬럼매핑·웹통합. ROAS페이지 키워드 기능
metadata: 
  node_type: memory
  type: project
  originSessionId: 27de0a9f-0150-4513-bcfb-18f7653ffd2a
---

지마켓 **CPC 광고 키워드별 실적** = ad.esmplus.com `cpc/report/groupReport`의 **'키워드' 탭**(`li[data-type='K'] a`)에서 상품번호를 `#searchText`에 검색→Enter→결과표 `#spanKeywordSearchData table tbody tr` 파싱. 상품당 ~5초.

**크롤러** `crawlers/gmarket_keyword_crawler.py`: 로그인은 gmarket_crawler `_try_cookie_login/_full_login` 재사용, 기간설정은 gmarket_ad_report_crawler `_set_period_thismonth/_set_period_month` 재사용. 순서: REPORT_URL→키워드탭→기간→`ReportList.GetTotalSearch()`→판매자'지마켓'(a.select_text[data-select='slt-0']→radio data-type='2'→btn_apply)→상품별 검색. preflight(platform='gmarket') 동시크롤 금지. `run({login_id:[product_no,...]}, year, month)`.

**★컬럼 매핑(라이브 검증 2026-06-13, 실측 12칸)**: `[0]키워드 [1]노출 [2]클릭 [3]클릭율 [4]영역명("그 외 영역") [5]평균노출순위 [6]평균클릭비용 [7]총비용 [8]구매수 [9]구매금액 [10]전환율 [11]광고수익률`. 붙여받은 PyQt 코드(11칸 가정)는 '영역명'이 끼어 한칸씩 밀림 → **끝(오른쪽)에서 매핑**으로 해결: avg_rank=tds[-7], avg_click_cost=tds[-6], cost=tds[-5], orders=tds[-4], conv_amount=tds[-3], conv_rate=tds[-2], roas=tds[-1] (왼쪽 0~3은 앞에서). 영역명 유무에 견고.

**모델** `GmarketKeywordReport`(gmarket_keyword_report): (login_id, product_no, keyword, year, month) 유니크, 월단위 멱등(범위삭제후삽입). 필드 impressions/clicks/click_rate/avg_rank/avg_click_cost/cost/orders/conv_amount/conv_rate/roas.

**★키워드 효율 필터(2026-06-13, 사용자 요구)**: 대상상품은 ROAS≥200%인데 그 상품의 **키워드는 0%까지 전부 저장**돼 91%(5,970중 5,412)가 conv_amount=0이었음. → 수집 저장 직전 `gmarket_keyword_crawler.py`에서 **키워드 단위 ROAS≥100%(conv_amount≥cost·cost>0)만 저장**하도록 필터 추가. 기존 <100행 일괄삭제(553만 보존). GmarketProductRoasView 모달 칩도 kw_roas_min 기본 100 적용. 즉 키워드는 수집·표시 모두 ROAS≥100만.

**관리명령** `crawl_gmarket_keywords --ym-from --ym-to --roas-min(기본200) --eid --product-nos`. 대상=기간 CPC ROAS≥roas_min & 구매금액>0 상품 자동산정, 또는 --product-nos 직접지정(login_id는 GmarketProductAdCost로 매핑).

**API**: `/cpc/gmarket/keyword-crawl/`(POST 트리거, body product_nos/ym/roas_min), `/cpc/gmarket/keyword-upload/`(엑셀 첫열=상품번호 업로드→수집), `/cpc/gmarket/keyword-status/`(진행상태). 트리거는 subprocess로 관리명령 실행(크롤러 preflight가 동시실행 차단).

**프론트**(GmarketRoasPage 상품모달, `_gmkt_product_rows`가 행에 keywords·avg_click_cost 부착): 평균단가(광고비 왼쪽, **프론트에서 cost/clicks 직접계산** — 백엔드 필드 undefined시 에러나서), 키워드 칩(광고비 오른쪽, ROAS%표기·광고비순6개), 🔑키워드수집 버튼(보이는/선택 상품 대상), 📤엑셀업로드. 대상 상품번호 = 'ROAS200%↑ 키워드(CPC)' 모달에 뜬 상품(CPC roas≥200).

검증: rejoice666 2상품 라이브 추출 성공(공사장안전띠=노출23·클릭1·광고비1045·구매금액165740·ROAS15860%). 동시크롤 금지로 사용자 ad_report 백필 중엔 자동 연기됨.

**연도-버킷 모드(2026-06-13 추가)**: 월별이 아니라 **연 단위 누적**으로 수집(상품당 1회 범위조회 → 12배 빠름). `_set_period_range(driver,start,end)`로 캘린더에 'YYYY-01-01~YYYY-12-31'(현재연도는 오늘까지) 설정, 결과를 **year=YYYY, month=0**(버킷키)으로 저장. ★함정: run()의 `month = month or today.month`는 month=0이 falsy라 6월로 새는 버그 → `month if month is not None else ...`로 수정. 명령 `--year 2025`(대상=그해 CPC ROAS≥200% 중복제거), API `keyword-crawl {years:[2025,2026]}`(연도별 순차 &&), loss-products 키워드부착은 `year__in=기간연도`(month무관)로 버킷 매칭. 프론트 3버튼(2025키워드/2026키워드/전체키워드)=openKwYear가 기간 연도로 맞추고 키워드모달 오픈+연도기록, 🔑수집은 years 전송. 모달 전 컬럼 정렬(키워드열=kw_count). 대상 실측: 2025=5,505 / 2026=2,047상품(중복제거, 25계정). 시간≈상품수×6초(2025 ~10시간, 2026 ~4시간). rejoice666 파일럿(2025=293·2026=158=451, ~45분) 라이브 검증: 테팔커피포트1490%·JBL633% 등 정상부착. [[project_gmarket_ad_report_product]] [[project_gmarket_roas_page]] [[feedback_crawling_rule]]

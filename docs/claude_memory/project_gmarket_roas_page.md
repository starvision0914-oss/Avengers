---
name: project_gmarket_roas_page
description: 지마켓 상품 ROAS 페이지(/gmarket-roas) 데이터출처·실매출매칭·기간·적자기준
metadata: 
  node_type: memory
  type: project
  originSessionId: ecfd8451-6046-498a-a6e4-32b9cd436ffc
---

지마켓 **상품 ROAS 페이지**(`/gmarket-roas`, GmarketRoasPage.tsx) = [[project_gmarket_ad_product_report]] 크롤(GmarketProductAdCost)을 계정별 집계.
백엔드: `GmarketRoasAccountsView`(계정요약 `/cpc/gmarket/roas-accounts/`), `GmarketProductRoasView`(상세+CSV `/cpc/gmarket/product-roas/`), 공통헬퍼 `_gmkt_roas_period`/`_gmkt_month_q`/`_gmarket_realsales`/`_gmkt_realsales_window`.

**ROAS 2종(확정 2026-06-12)**:
- **광고전환 ROAS** = 광고리포트 전환매출(conv_amount)/광고비. CPC단독·AI단독·합계 각각. %표기.
- **실매출 ROAS** = 매출자료 전역매칭/광고비. 다리: GmarketProductAdCost.product_no → GmarketMyProduct.seller_product_code(=판매자/자체코드) ↔ SalesRecord.product_code. 매출=total_price 전역합(지마켓+옥션, 판매자ID 무관). 직접 product_no↔product_code는 0건(체계 다름)이라 반드시 다리 필요. 검증 rejoice666: 광고비207,603 광고전환485,030(233.6%) 실매출1,044,294(503%).
- **상품별 광고비(총비용)는 참고용**(사용자 명시). 신뢰값은 광고센터 스냅샷(GmarketDepositSnapshot) — [[project_gmarket_adcost_source]].

**기간**: 이번달/지난달/년간/기간별, **월단위·최대 1년**(GmarketProductAdCost는 year+month 월단위 누적, 일별 없음). 11번가는 adoffice 일별이라 일별 ROAS 가능하지만 지마켓은 불가. 프론트 ym_from/ym_to('YYYY-MM') 전달, 백엔드 1년 초과시 최근12개월 클램프. **실매출 매칭기간은 광고데이터 실제존재 월로 한정**(_gmkt_realsales_window) — 안그러면 년간선택시 광고비(6월만) vs 매출(전체) 불일치로 ROAS 부풀려짐.
**일별수집 권장 안함**: 리포트가 일별 미제공→매일 '어제' 직접입력 크롤 필요(IP차단 위험, 총비용 참고용이라 가치 낮음). 과거월은 직접입력 1회 백필. 월단위 관리 권장.

**적자상품 모달(11번가 St11RoasPage식, 2026-06-12)**: '전체 적자상품 📋' 클릭→모달(다운로드 아님). 기준 **광고비≥2,000 & 클릭≥10 & ROAS(광고전환 conv/cost)≤100** (상품번호 단위 기간집계). 백엔드 `GmarketLossProductsView`(/cpc/gmarket/loss-products/, JSON), `_gmkt_loss_rows`. 모달: 헤더클릭정렬·행체크박스(전체선택, 미선택시 전체대상)·📋판매자코드복사·📋상품번호코드복사(숫자만)·⬇엑셀(클라이언트CSV)·✓삭제완료처리. 삭제완료=`GmarketLossDeleted`(login_id+product_no uniq, mig 0031) 기록→비고 '삭제완료'(파랑). status우선순위: 삭제완료>삭제(카탈로그없음)>상품상태. 엔드포인트 `GmarketLossMarkDeletedView`(/cpc/gmarket/loss-products/mark-deleted/, body items[{login_id,product_no,seller_code}]). 검증 rejoice666 2026누계 적자161개.
(별도 CSV버튼 dlLoss는 제거됨. '전체 ROAS200%↑ 상품'=dlHighRoas(roas_min=200 export), '키워드'버튼은 준비중 alert-키워드리포트 미수집.)

**모달 3모드 통일(2026-06-12)**: 4개 툴바버튼 전부 모달(다운로드 아님). 백엔드 `_gmkt_product_rows`(필터 옵션화: cost_min/clicks_min/roas_min/roas_max, CAP 5000) + `GmarketLossProductsView`(/cpc/gmarket/loss-products/) 공통. 프론트 LMODES={loss:cost2000/roas≤100/clk10+삭제완료버튼, high:roas≥200(CPC+AI), keyword:roas≥200+ad_type=cpc(키워드광고=CPC만), all:무필터}. 삭제완료버튼은 loss모드만. '키워드'버튼='CPC ROAS200%↑ 상품리스트'(키워드리포트 아님—CPC=키워드광고로 간주). 백엔드 _gmkt_product_rows에 ad_type(cpc/ai) 필터. 검증 rejoice666누계 키워드(cpc)158 상품(cpc+ai)180. **구매건수(real_orders)** = 매출자료 상품코드매칭 실주문건수(_gmarket_realsales가 Count('id')도 집계, 이제 4-tuple: code/real/status/realorders 반환 — 콜러 3곳 갱신). 모달/상세/CSV에 구매건수 컬럼. **상품번호 클릭→지마켓링크**(site='A'→itempage3.auction.co.kr/DetailView.aspx?itemno=, 그외→item.gmarket.co.kr/Item?goodscode=, 숫자만). 검증 rejoice666 누계: 적자161 high180 전체3706. 카탈로그크롤(GmarketMyProduct)엔 구매건수 없음(상태/재고/가격만)—구매건수는 광고리포트 orders 또는 매출매칭으로만.

**모달 데이터 기준(사용자확정 2026-06-12)**: 주(主)=**광고센터 기준**(광고비·구매수 ad_orders=Sum(orders)·구매금액 conv_amount·ROAS 광고전환). 필터·정렬도 광고센터 roas. **매출자료 기준(실구매건수 real_orders·실매출 real_sales)은 '참고'(회색 text-[#aaa]+"(참고)"라벨)**. 헤더안내 "구매수·구매금액·ROAS=광고센터 / 실구매·실매출=매출자료(참고)". 엑셀도 동일구분. (구매건수 출처 질문→매출자료매칭 A 유지 확정.)

**상세모달**: 컬럼헤더 클릭정렬(기본 광고비 내림차순), 판매자코드 컬럼, 여러달 선택시 product_no 단위 집계(roas=conv/cost 재계산). 계정표 우측끝 '상세' 버튼. **맨오른쪽 비고(상품상태) 컬럼**: GmarketMyProduct.status_type 매핑(`_gmkt_status_label`/`_GMKT_STATUS`). **'11'/'21'→판매중**(실측 '11'은 100% 재고>0, ESM 원본 sellStatus코드 미매핑분), 22→판매중지, 25→판매불가, 23→품절, 24→판매종료, **MyProduct에 없는 광고상품→'삭제'**. _gmarket_realsales가 (code_by_pno, real_by_pno, status_by_pno) 3-tuple 반환. CSV에도 비고 컬럼.

**고친 버그(2026-06-12)**: ①계정표 헤더8칸 vs 본문7칸 밀림(cpc_roas/ai_roas 셀 누락)→정렬복구 ②실행중 백엔드가 옛 코드라 cpc_roas/ai_roas/real_* None 반환→pm2 restart 필요(views.py는 untracked 신규라 미reload시 구버전 서빙). 대시보드 `/gmarket`에 '상품 ROAS' 진입버튼 추가. 프론트는 vite dev(HMR).

---
name: project_gmarket_adcost_source
description: "지마켓 광고비 3소스(today=스냅샷/month·일자별=거래원장/ROAS=상품별), 옥션 site=A, seller_id 'G'정규화로 공유ESM 서브분리"
metadata: 
  node_type: memory
  type: project
  originSessionId: ba50ac2f-1f75-48ec-bf63-633d335f8b3e
---

지마켓 광고비 출처가 2가지이고 값이 다름.

⚠️ **정정(2026-06-11)**: 스냅샷은 "오늘 실시간 사용액/잔액" 표시엔 신뢰값이지만 **월별 집계엔 부적합**. total_usage는 당일 누적(자정 리셋)인데 크롤이 8~19시에만 찍히고 저녁(20~23시)·누락일은 0 → 그날 마지막 스냅샷이 하루치를 다 못 담음. 실측 5월: 스냅샷합산 34,287 vs 거래내역 268,323 = **스냅샷이 8배 과소**. views.py:159-172(april_snaps)가 이 스냅샷합산으로 월광고비를 내서 "집계 엉망". → **월/과거 광고비는 GmarketCostHistory(use_date 기준 CPC+AI매출업 amount합)로 집계해야 정확.** 단 거래내역은 셀러캐시 결제분 누락 갭 있음(아래) → '기타'유형·셀러캐시분 감사 필요. 매출 자체는 광고비의 1%↓라 수익성 이슈 아님(진짜는 매출 -66% 트래픽붕괴, 3월66.9M→5월22.5M).

✅ **확정·정정(2026-06-17)**: 광고비 데이터 **3소스** 역할 명확.
- **스냅샷**(GmarketDepositSnapshot, crawl_gmarket_cost=gmarket_crawler): 당일 누적 광고비(0시~현재, 자정리셋)·잔액. 대시보드 ProfitDashboardView **today_***. 09~19시+07:40 매시 수집(7분, 화면 숫자만 read). cost_hourly 다른크롤 겹치면 **스킵→대기후수집**으로 변경(최대50분).
- **거래원장**(GmarketCostHistory, use_date별=일자별 광고비): 대시보드 **month_*** = "이번달 광고비"(당월 use_date 합). **일자별 광고비 정리의 근본**(=/gmarket ad-daily 화면, GmarketAdDailyView). 채우는 건 **gmkt_today**(orch_gmkt_today.sh, 오늘만 빠르게 멱등), **20시 cron(cron_gmarket_adcost_17check.sh)이 호출**+마감체크. crawl_gmarket_adcost는 --from/--to로 전체(기본 올해1월~오늘) 멱등.
- **상품별**(GmarketProductAdCost, crawl_gmarket_ad_report 08시): ROAS·상품별. period=당월전체 멱등(일자별 스킵돼도 1회 크롤로 메워짐).
- **정합성**: 광고센터(상품별) vs ESM(거래원장) 6/1~16 = **0.1%차**(거래원장 최신시). 스냅샷 당일누적 vs 거래원장 당일 ≈1.5%(시점차).
- **옥션**: 상품별/거래원장 모두 집계됨. CPC리포트 **site='A'**(지마켓=G), **AI는 site=''(옥션·지마켓 통합)**. 거래원장은 market='auction'. 옥션 월 5천~1.5만(전체 0.1~0.25%, 거의 안함). ⚠️**일자별 구글시트(gmarket_daily_gsheet)는 dailyReport 기본=지마켓만→옥션 미포함**(합산하려면 수정 필요).
- **공유ESM 서브 광고비**: 대표 로그인 1회로 리포트에 판매자ID로 같이 나옴(별도로그인 불필요). AI리포트 seller_id에 **'G '접두사**('G starvisi')라 조회0이던 것 → **접두제거 정규화 완료**(starvisi/223/224 분리표시). 일자별 시트는 대표탭에 대표+서브 **합산**(starvisi 별도탭 없음). 235/236은 6월 광고 미집행(실제0).

✅ **대시보드 실시간 보충(2026-06-19)**: GmarketCostHistory(거래원장)는 use_date 기준 **1~2일 지연 기록**(2026-06-19 시점 최신=06-17)이라 GmarketDashboardView 기간 광고비가 "오늘/어제치 0"으로 보였음. → **하이브리드로 수정**(views.py GmarketDashboardView): 거래내역 최신 반영일(_cut_g/_cut_a=market별 Max(use_date))**까지는 거래내역**, 그 이후 미반영일(오늘 포함)은 **GmarketDepositSnapshot 당일소진액(계정별 그날 마지막값) 실시간 보충**(중복 방지). 검증: 오늘만 조회 0→121,121원(CPC+AI). 갱신 주기=스냅샷 시간별 크롤(09~23시). 옥션은 _cut_a/auction_cpc로 대칭 처리.

--- 이하 종전 기록(실시간 스냅샷 맥락) ---

- **GmarketDepositSnapshot** (crawl_gmarket_cost → gmarket_crawler.py): ad.esmplus.com 광고센터에서 CPC(`gmarket_cpc`)·AI매출업(`ai_usage`) 실시간 소진액 직접 read. 예) dlrmsgh012 CPC=6501/AI=1067. **이게 맞는 값.**
- **GmarketCostHistory** (crawl_gmarket_adcost → gmarket_cost_crawler.py): 판매예치금 거래내역 텍스트 분류(transaction_type=CPC/AI매출업/서버비용). dlrmsgh012는 CPC=7029/AI=0 → 광고센터와 불일치(셀러캐시 결제분은 거래내역에 안 뜸).

대시보드 `/api/cpc/gmarket/dashboard/` (GmarketDashboardView, apps/cpc/views.py)는 CPC/AI를 **스냅샷 최신값**에서 가져오도록 수정함(서버비용만 거래내역). 잔액과 동일한 "계정별 최신 스냅샷" 재사용.

계정 정렬: CrawlerAccount.display_order = config.ini의 User번호(dlrmsgh012=5 … starvisi=28). 대시보드 기본 정렬은 번호 오름차순, 프론트 GmarketDashboard.tsx 전 컬럼 정렬 가능.

주의: 거래내역 응답이상=수집실패(0건 아님). 일부 계정(starvisi/rejoice235/236 등) 거래내역 응답이상으로 0건. dlwodb777은 거래내역 정상0건이나 광고센터엔 비용존재(셀러캐시 의심, 복수아이디 아님 확인됨). 타임존상 collected_at __date 조회 금지([[feedback_timezone_pitfalls]]).

상품(광고그룹)별 광고비 효율: GmarketAdGroupPerf 모델 + crawl_gmarket_adgroup 명령 + /cpc/gmarket/adgroup/ API + 화면 /gmarket-adgroup. 소스=ESM 광고센터 CPC 입찰관리 그리드(#tbGroupAdStateList 일반/#tbSmartGroupAdStateList 간편): 광고그룹별 노출/클릭/클릭율/평균클릭비/총비용(광고비)/상품수. 로하스 LCP 계정은 광고그룹=상품 1:1이라 사실상 상품별. ROAS(매출대비)는 ESM에 없음→매출결합 필요(미구현).

★로그인실패 데이터오염 함정: 드라이버 재사용+쿠키재사용 상태에서 로그인 실패(잘못된 자격증명)하면 직전 계정의 세션/페이지를 그대로 읽어 동일 데이터가 복제됨. rejoice235/rejoice236(직전 rejoice234 복제), starvisi(직전 dlwodb000 복제)가 대표 사례 — 이 3계정은 로그인 자체가 안 됨(자격증명/접근 보류 중). 수집 후 동일 수치 중복 발견 시 해당 계정 제외할 것. 11번가 cost 크롤도 USE_COOKIE_LOGIN=True로 전환됨(IP안전+속도), gmarket_cost_crawler도 쿠키재사용 추가됨.

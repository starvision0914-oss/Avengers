---
name: project_gmarket_adcost_source
description: "지마켓 광고비는 광고센터 스냅샷이 신뢰값(거래내역과 다름), 대시보드 CPC/AI 출처와 계정 정렬 기준"
metadata: 
  node_type: memory
  type: project
  originSessionId: ba50ac2f-1f75-48ec-bf63-633d335f8b3e
---

지마켓 광고비 출처가 2가지이고 값이 다름.

⚠️ **정정(2026-06-11)**: 스냅샷은 "오늘 실시간 사용액/잔액" 표시엔 신뢰값이지만 **월별 집계엔 부적합**. total_usage는 당일 누적(자정 리셋)인데 크롤이 8~19시에만 찍히고 저녁(20~23시)·누락일은 0 → 그날 마지막 스냅샷이 하루치를 다 못 담음. 실측 5월: 스냅샷합산 34,287 vs 거래내역 268,323 = **스냅샷이 8배 과소**. views.py:159-172(april_snaps)가 이 스냅샷합산으로 월광고비를 내서 "집계 엉망". → **월/과거 광고비는 GmarketCostHistory(use_date 기준 CPC+AI매출업 amount합)로 집계해야 정확.** 단 거래내역은 셀러캐시 결제분 누락 갭 있음(아래) → '기타'유형·셀러캐시분 감사 필요. 매출 자체는 광고비의 1%↓라 수익성 이슈 아님(진짜는 매출 -66% 트래픽붕괴, 3월66.9M→5월22.5M).

--- 이하 종전 기록(실시간 스냅샷 맥락) ---

- **GmarketDepositSnapshot** (crawl_gmarket_cost → gmarket_crawler.py): ad.esmplus.com 광고센터에서 CPC(`gmarket_cpc`)·AI매출업(`ai_usage`) 실시간 소진액 직접 read. 예) dlrmsgh012 CPC=6501/AI=1067. **이게 맞는 값.**
- **GmarketCostHistory** (crawl_gmarket_adcost → gmarket_cost_crawler.py): 판매예치금 거래내역 텍스트 분류(transaction_type=CPC/AI매출업/서버비용). dlrmsgh012는 CPC=7029/AI=0 → 광고센터와 불일치(셀러캐시 결제분은 거래내역에 안 뜸).

대시보드 `/api/cpc/gmarket/dashboard/` (GmarketDashboardView, apps/cpc/views.py)는 CPC/AI를 **스냅샷 최신값**에서 가져오도록 수정함(서버비용만 거래내역). 잔액과 동일한 "계정별 최신 스냅샷" 재사용.

계정 정렬: CrawlerAccount.display_order = config.ini의 User번호(dlrmsgh012=5 … starvisi=28). 대시보드 기본 정렬은 번호 오름차순, 프론트 GmarketDashboard.tsx 전 컬럼 정렬 가능.

주의: 거래내역 응답이상=수집실패(0건 아님). 일부 계정(starvisi/rejoice235/236 등) 거래내역 응답이상으로 0건. dlwodb777은 거래내역 정상0건이나 광고센터엔 비용존재(셀러캐시 의심, 복수아이디 아님 확인됨). 타임존상 collected_at __date 조회 금지([[feedback_timezone_pitfalls]]).

상품(광고그룹)별 광고비 효율: GmarketAdGroupPerf 모델 + crawl_gmarket_adgroup 명령 + /cpc/gmarket/adgroup/ API + 화면 /gmarket-adgroup. 소스=ESM 광고센터 CPC 입찰관리 그리드(#tbGroupAdStateList 일반/#tbSmartGroupAdStateList 간편): 광고그룹별 노출/클릭/클릭율/평균클릭비/총비용(광고비)/상품수. 로하스 LCP 계정은 광고그룹=상품 1:1이라 사실상 상품별. ROAS(매출대비)는 ESM에 없음→매출결합 필요(미구현).

★로그인실패 데이터오염 함정: 드라이버 재사용+쿠키재사용 상태에서 로그인 실패(잘못된 자격증명)하면 직전 계정의 세션/페이지를 그대로 읽어 동일 데이터가 복제됨. rejoice235/rejoice236(직전 rejoice234 복제), starvisi(직전 dlwodb000 복제)가 대표 사례 — 이 3계정은 로그인 자체가 안 됨(자격증명/접근 보류 중). 수집 후 동일 수치 중복 발견 시 해당 계정 제외할 것. 11번가 cost 크롤도 USE_COOKIE_LOGIN=True로 전환됨(IP안전+속도), gmarket_cost_crawler도 쿠키재사용 추가됨.

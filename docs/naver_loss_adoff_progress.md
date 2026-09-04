# 네이버(스마트스토어) 적자상품 자동 광고OFF — 진행 현황

## 1. 자동화 로직 — 완료
- [x] `/naver-roas` 화면: 상품별 광고센터ROAS + 실매출ROAS(정산 기준) 함께 표시
- [x] 판정 기준: **(광고센터ROAS≤100% AND 실매출ROAS≤100%) OR 실매출 0원** — 실매출 0원은 광고센터ROAS가 아무리
      높아도(전환 허수 의심) 적자로 간주 (2026-09-04 "달콤한 밀양 사과" 사례로 발견)
- [x] 조건: 광고비≥2,000원 · 클릭≥10 · 실매출 매칭 근거(seller_management_code) 필요 (없으면 적자로 단정 안 함)
- [x] **광고 OFF는 판매중(SALE) 상품만 대상** — 판매중지/품절 상품은 목록엔 보이되 OFF 액션에서는 제외
- [x] 자동화 명령: `manage.py auto_naver_loss_adoff` (매일 21:30 크론, `cron_naver_loss_adoff.sh`)
- [x] 화면 수동 버튼(`선택 광고 OFF`)도 서버가 동일 기준으로 재검증 후 실행 (`_verify_loss_products`,
      `NaverRoasBulkAdOffView`) — 프론트 선택값을 그대로 믿지 않음
- [x] 적자상품 목록: 상태 필터 드롭다운 + 판매중 상품 항상 최상단 정렬

## 2. 2026-09-04 오탐 사고 — 원인 규명·수정 완료
발단: "말랑이 고릴라 스트레스 볼"(실ROAS 616.6%, 흑자)이 잘못 광고OFF됨.

**원인 ①** — 화면 버튼(`/naver-product-roas/ad-off/`)이 서버 재검증 없이 프론트가 보낸 목록을 그대로 실행.
프론트 새로고침 중 뜬 stale 데이터가 그대로 전송되어 무관 상품 155건이 잘못 OFF됨.
→ 서버 측 AND조건 재검증 로직 추가로 해결.

**원인 ②(더 심각)** — `crawl_naver_product_adcost` 저장 버그. 매일 크론이 `since=월초~until=오늘`(월누적) 범위로
조회 후 `(계정,since_date,until_date,ad_type,상품)`을 유니크 키로 저장했는데, `until_date`(오늘)가 매일 바뀌어
**하루치 스냅샷이 매일 새 행으로 계속 쌓임**. SUM() 집계 시 이 스냅샷들이 중복 합산되어 광고비/전환매출이
최대 20~30배(날짜 수만큼) 부풀려짐. ("대용량 레모나 산 스틱" 사례: 실제 90일 매출 90,330원인데 DB 집계는
2,619,570원으로 표시됨)
→ 저장 로직을 `(계정,since_date,ad_type,상품)` 기준으로 매번 덮어쓰도록 수정, `NaverAdProductReport` 모델
`unique_together`도 동일하게 변경(마이그레이션 0021), 기존 중복행 365,913건 삭제(→65,677행 남음).

**사후 재검증**: 정리된 데이터로 계정 7(아이리스)·13(스타쇼핑몰) 전체 소재 재검증
→ 애초에 꺼질 이유 없었던 **1,581건 복구(ON)**, 정확한 기준으로도 적자인 **81건 신규 OFF**. 실패 0건.

## 알아둘 점
- `NaverAdProductReport.product_no`는 mallProductId(=`SmartStoreProduct.channel_product_no`)와 매칭됨.
  내부표시번호(`product_no`)로 조회하면 매칭 거의 안 됨(과거 버그, 이미 수정됨).
- 실매출은 `SalesRecord`(platform='smartstore')를 `seller_management_code`(및 `_bare_seller_code` 정규화)로
  글로벌 매칭, 정산 시차 대비 45일 버퍼 사용.
- 소재별 90일 개별 재확인(광고센터 내부 API, 쿠키 필요)은 검토했으나 **오히려 착시를 줄 수 있어(짧은 창에서
  간접전환 1건이 실매출 0원인데도 고ROAS로 보임) 도입하지 않기로 결정** — 연간 누적 + 실매출 AND(또는
  실매출0) 기준을 계속 사용.
- 광고센터 내부 통계 API용 쿠키는 `crawlers/naver_ads_cookies.json`에 `naver_ad_login_id` 별로 저장됨
  (계정 7=rejoice999 등, 실제 로그인ID와 다름 — `SmartStoreAccount.naver_ad_login_id` 필드 확인 필요).

## 다음에 이어서 할 일 (없으면 비워둠)
- (현재 없음 — 2026-09-04 기준 스마트스토어 네이버 광고 자동화 전 항목 정상 완료)

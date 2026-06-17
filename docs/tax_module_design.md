# Avengers 세무(부가세/VAT) 모듈 설계안

> 작성 2026-06-07. ai100(betona1/ai100) 세무 모듈을 참고해 Avengers에 맞게 재설계.
> 원칙: **11번가 먼저 완성 → 지마켓/스마트스토어/쿠팡 순 확장**. 기존 11번가 로그인/크롤 인프라(eleven_crawler) 재사용.

## 1. 목표 & 핵심 개념
부가세 신고에 필요한 **마켓별 "부가세신고내역"(공식 과세매출)** 을 자동 수집해 **사업자별·월별로 합산**하고, **매출세액 − 매입세액(광고비 등)** 기준 부가세를 산출한다.

- **매출자료**: 마켓 셀러센터의 *부가세신고내역* 페이지(주문자료 SalesRecord와 별개 — 정산 기준 공식 과세매출).
- **매입자료**: 광고비 세금계산서(ElevenCostHistory의 CPC) + 마켓수수료 등.
- **산출**: 부가세 예정/확정 신고용 종합자료 (사업자별, 월/분기별).

```
마켓 부가세신고내역 크롤 → 마켓별 월 매출 테이블
   + 광고비/수수료(매입) → 사업자별·월별 합산 → 매출세액-매입세액 → 신고 종합자료/엑셀
```

## 2. 데이터 모델 (신규 테이블, Avengers 스키마)
ai100은 tax 전용 DB를 썼으나, Avengers는 **단일 Avengers 스키마**에 `tax_` 프리픽스 테이블로 둔다.

| 모델 | 주요 필드 | 설명 |
|---|---|---|
| **TaxBusiness** | code, name_short, name_official, biz_reg_no, biz_type(법인/개인), report_cycle(월/분기), vat_number | 사업자 |
| **TaxAccountMap** | business(FK), platform, login_id, account_name, memo, is_active | 마켓 로그인계정 ↔ 사업자 매핑 (CrawlerAccount.login_id 기준) |
| **TaxVatMonthly** | business(FK), platform, login_id, year, month, taxable_sales(과세매출), tax_free_sales(면세), credit_card, cash_receipt, expense_proof, mobile, etc_amount, collected_at | 마켓·계정·월별 **매출** (부가세신고내역 파싱 결과) |
| **TaxPurchase** | business(FK), platform, login_id, year, month, ad_supply(광고공급가), ad_vat(광고부가세), fee_supply(수수료공급가), fee_vat, source | **매입**(광고비/수수료 세금계산서). 광고비는 ElevenCostHistory에서 파생 |

unique_together: TaxVatMonthly = (login_id, year, month), TaxPurchase = (login_id, year, month, source).
저장: delete-insert(idempotent), (login_id, year-month) 기준 — 매출 업로드와 동일 원칙.

## 3. 수집 — 마켓별 VAT 크롤러
공통 패턴(ai100과 동일): 로그인 → 부가세신고내역 페이지 → 기간(YYYYMM) 선택 → 표 파싱 → 사업자 매핑 → 저장.

### 11번가 (1순위, 구현 대상)
- **재사용**: eleven_crawler의 `create_driver`, `_try_cookie_login`(쿠키 4h 재사용 → OTP 회피), `_do_login`, `_dismiss_dom_modals`.
- **페이지**: `https://soffice.11st.co.kr/view/30476` (부가세신고내역), iframe 내부.
- **기간 선택**: `#searchStartYear/#searchStartMonth/#searchEndYear/#searchEndMonth` (select) → `#btnSearch`.
- **표 파싱**: table[1], 행=월. 컬럼: 기간 / 과세매출 / 신용카드 / 현금영수증 / 지출증빙 / 휴대폰 / 기타 / 부가수수료 / 면세 / 영세. '합계' 행 스킵.
- 신규 파일: `crawlers/eleven_vat_crawler.py`, 명령 `crawl_11st_vat`.

### 이후 확장 (지마켓 ESM, 스마트스토어, 쿠팡 …)
ai100의 `gmarket_vat.py` 등 참조해 동일 구조로 추가. 지마켓은 **매입자료(수수료/광고비 세금계산서)** 도 제공.

## 4. 집계 서비스 (tax_service.py)
- `get_businesses()` / `get_vat_summary(year, business_id)`: 마켓별 TaxVatMonthly를 **사업자별·월별 합산** + 마켓 breakdown.
- **부가세 계산**: 과세매출 합계 × 1/11 = 매출세액. 매입세액 = (광고/수수료 공급가 × 10%). 납부세액 = 매출세액 − 매입세액.
- 신고주기: 개인=월, 법인=분기(1~4Q) 소계.

## 5. API (apps/tax 또는 cpc 확장)
- `GET /api/tax/businesses/` 사업자 목록
- `GET /api/tax/vat-summary/?year=&business_id=` 종합자료(summary+breakdown)
- `GET /api/tax/vat-monthly/?platform=&year=` 마켓 raw
- `GET/POST /api/tax/accounts/` 계정↔사업자 매핑 CRUD
- `POST /api/tax/crawl/` 수동 크롤(스트리밍)

## 6. 프론트엔드 (/tax 페이지)
- 사업자 선택 + 연도 필터
- 종합 탭: 사업자별 월별 합산표(과세매출/매출세액/매입세액/납부세액) + 마켓 분해
- 마켓 탭: 11번가 등 raw 월별표
- 엑셀 다운로드(분기/상반기 소계, 법인 먼저)
- 계정관리 모달(사업자↔로그인 매핑)

## 7. 단계별 구현 절차
- **Phase 0 (테스트)**: 11번가 1계정 부가세신고내역 크롤 → 콘솔 출력 검증 ✅ ← 지금 단계
- **Phase 1**: TaxBusiness/TaxAccountMap/TaxVatMonthly 모델 + 마이그레이션, `crawl_11st_vat`로 전 11번가 계정 수집·저장
- **Phase 2**: tax_service 집계 + API + 간단 화면(11번가 종합)
- **Phase 3**: 매입(광고비/수수료) 연동 → 납부세액 산출
- **Phase 4**: 지마켓·스마트스토어·쿠팡 크롤러 추가, 사업자 통합 종합자료 + 엑셀

## 8. 1계정 테스트 계획
- 대상: 11번가 1계정(예: rejoice321), 기간 2026-01 ~ 2026-05.
- 방식: 쿠키 재사용 로그인 → view/30476 → 기간선택·검색 → 표 파싱 → **월별 과세매출/결제수단 콘솔 출력**(DB 저장 없음).
- 주의: cost 크롤(Chrome 락)과 동시 실행 불가 → cost 크롤 종료 후 실행.

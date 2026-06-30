---
name: project_naver_ad_product_roas
description: 네이버 스마트스토어 상품별 광고비 수집 시스템 구축 현황 (2026-06-29)
metadata: 
  node_type: memory
  type: project
  originSessionId: e4cd61c6-5723-4df5-93b9-ee4dc506dac6
---

## 구축 완료 내용

### 핵심 발견: 네이버 광고 API 2개
- 공개 NCC API(`api.naver.com`): 쇼핑 캠페인 비용 **0 반환** (막혀있음)
- 내부 Web API(`ads.naver.com/apis/sa/api/stats` POST): **실제 비용 반환**
- 인증: 쿠키 + `X-AD-customer-id` 헤더 필수
- `salesAmtMicros` 필드 = 마이크로원 (÷1,000,000 = 원)

### 수집 구조
- 공개 NCC API: 캠페인→광고그룹→소재→`referenceData.mallProductId`로 상품번호 추출
- 내부 API: 소재ID 배치 POST → 비용/클릭/전환 수집
- 저장: `NaverAdProductReport` 모델 (DB: `naver_ad_product_report`)

### 쿠키 관리
- `NAVER_ADS_AVAILABLE_USER` 쿠키 ~4시간마다 만료
- `NID_AUT` 유효한 한 QR 없이 자동 갱신 가능
- 갱신 스크립트: `/home/rejoice888/Avengers/backend/naver_ads_cookie_refresh.py`
- 대상 계정: rejoice666(스타쇼핑v), rejoice888(스타쇼핑v AI), rejoice999(아이리스.)
- 쿠키 파일: `crawlers/naver_ads_cookies.json`

### 크론
- `30 */3 * * *` → 쿠키 자동 갱신
- `30 8 * * *` → 상품별 광고비 수집 (당월 누적)

### 소급 수집 결과 (2026-06-29 완료)
- 아이리스.(rejoice999): 1~6월 합계 26,221개
- 스타쇼핑(v)(rejoice666): 1~6월 합계 14,295개
- 2025년: 0개 (현재 소재ID로 과거 조회 불가 — 네이버 정책)

### 프론트엔드
- URL: `/naver-roas` (`NaverRoasPage.tsx`)
- 기능: 기간/계정/광고유형 필터, 전체/적자/우수 모드, 정렬, 복사, CSV 엑셀
- 적자 기준: 광고비≥2,000 · 클릭≥10 · ROAS≤100%
- 우수 기준: ROAS≥200%
- 스마트스토어 페이지에 "상품별 ROAS" 파란 버튼으로 접근

### 관련 파일
- 서비스: `apps/smartstore/services/naver_search_ad.py` (`fetch_product_stats`)
- 커맨드: `apps/smartstore/management/commands/crawl_naver_product_adcost.py`
- 뷰: `apps/smartstore/views.py` (`NaverProductRoasView`)
- URL: `apps/smartstore/urls.py` → `/api/smartstore/naver-product-roas/`

**Why:** 지마켓처럼 상품별 ROAS 분석으로 적자상품 탐지·흑자상품 패턴 파악
**How to apply:** 다음 세션에서 네이버 광고 관련 작업 시 이 구조 그대로 활용

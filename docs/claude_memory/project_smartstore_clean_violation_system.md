---
name: smartstore-clean-violation-system
description: 스마트스토어 클린위반 크롤링·UI 시스템 구축 및 위반 상품 API 수정 내역
metadata: 
  node_type: memory
  type: project
  originSessionId: 123695e8-4adb-41fb-9174-4d05b712db02
---

## 클린위반 시스템 (2026-06-29~30 구축)

### 크롤러
- 명령: `python3 manage.py crawl_clean_violations`
- 파일: `apps/smartstore/management/commands/crawl_clean_violations.py`
- 대상: 전 16개 계정, login_id 기준 중복 제거로 실로그인
- 복수스토어: `starvis7783@gmail.com` → radio value `101489530`으로 아이리스.(id=7) 전환
- DB: `SmartStoreCleanViolation` (db_table='smartstore_clean_violation')
- 현황: 총 96건 (스타쇼핑몰 52건, 나머지 0건), 신규 위반 없음

### API 엔드포인트
- `GET /smartstore/clean-violations/` → 계정별 요약 (CleanViolationListView)
- `GET /smartstore/clean-violations/<account_id>/` → 상세 내역 (CleanViolationDetailView)

### UI (/smartstore 페이지)
- 계정 테이블: `#` 번호열 + 클린위반 빨간 배지 (클릭 시 모달)
- 모달: 위반유형별 문제점/대책 카드 + 상품 목록 (네이버 링크)

### 위반 상품 API 수정 (네이버 커머스 API)
- PUT 엔드포인트: `PUT /external/v2/products/channel-products/{channelProductNo}` (channel_product_no 사용)
- statusType 반드시 'SALE'로 변경 (UNADMISSION로 PUT 하면 400)
- 원산지 국내산: `originAreaCode='00'` (경남 밀양/제주도도 '00', content에 텍스트 입력)
- 농산물 단위가격: `unitCapacity: {unitPriceYn: false}` 추가 필수 (없으면 400)

### 수정 완료 상품 (스타쇼핑몰 starvision0914@gmail.com)
| 상품 | origin_no | 수정 내용 | 결과 |
|------|-----------|-----------|------|
| 매트리스패드 | 12908045543 | 상품명: "매트리스 패드 침대 패드 통기성 침구 SS Q 사이즈 110x205 155x205" | ✓ 재심사 |
| 요가의자 | 12907892823 | 상품명: "접이식 요가 보조 의자 필라테스 홈트 스트레칭 강철프레임 발커버 포함" | ✓ 재심사 |
| 밀양사과 | 12934700532 | 원산지 기타→국내산(00)+상품명 수식어 제거 | ✓ 재심사 |
| 제주감귤 | 12926815436 | 원산지 기타→국내산(00)+상품명 수식어 제거 | ✓ 재심사 |
| 경화제 | 12949802078 | 생활화학제품 안전확인신고 번호 없음 | 보류 |

**Why:** 클린위반 누적 시 페널티 → 상품 노출 감소·계정 제재 위험
**How to apply:** 위반 상품 수정 시 channel-products PUT 사용, statusType='SALE' 필수

---
name: starvision-product-name-optimization
description: "스타비젼(dlrmsgh01234@gmail.com) 상품명 AI 최적화 프로젝트 — Anthropic API 키 필요, 대기 중"
metadata: 
  node_type: memory
  type: project
  originSessionId: 123695e8-4adb-41fb-9174-4d05b712db02
---

## 스타비젼 상품명 최적화 프로젝트 (2026-06-30 시작, 대기 중)

### 현황
- 대상: SmartStoreAccount id=2 (스타비젼, dlrmsgh01234@gmail.com)
- 상품 수: SALE 997개, PROHIBITION 4개, OUTOFSTOCK 3개
- Commerce API 키: 있음
- 목표: 997개 전체 상품명 최적화 + 속성 추가

### 대기 이유
- Anthropic API 키 미등록 → 사용자가 `console.anthropic.com`에서 발급 예정
- SDK는 서버에 설치됨 (anthropic==0.112.0)
- 비용 예상: claude-haiku-4-5로 약 $1.44 (~2,100원)

### 작업 흐름 (준비됨)
1. `python3 manage.py collect_product_data` → `/tmp/starvision_products.json` 수집 (스크립트 완성)
2. Anthropic API로 상품명+속성 배치 생성 (haiku-4-5 권장)
3. 엑셀 파일로 검토
4. `PUT /external/v2/products/channel-products/{channelProductNo}` 일괄 적용

### API 핵심 사항
- GET/PUT 모두 `channel_product_no` (DB 필드명) 사용
- `PUT channel-products/{cno}` body: `{originProduct, smartstoreChannelProduct}`
- 응답에 `originProductNo` 포함됨
- rate limit: 초당 ~4건, DELAY=0.28초 설정

### 상품명 최적화 원칙
- 핵심 키워드 앞 배치 (소비자 검색어)
- 소재/규격/용도/대상 포함
- 수식어 제거 (프리미엄·달콤한·고품질·베스트·최고 등)
- 중복 키워드 제거
- 50자 이내, 특수문자 최소화

### 수집 스크립트
- `apps/smartstore/management/commands/collect_product_data.py`
- 출력: `/tmp/starvision_products.json`
- `new_name` 필드: AI가 채울 빈 필드

**Why:** 네이버 클린위반 예방 + 검색 상위 노출 = 매출 증가
**How to apply:** Anthropic API 키 등록 후 즉시 실행 가능

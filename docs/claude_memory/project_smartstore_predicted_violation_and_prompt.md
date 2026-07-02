---
name: project_smartstore_predicted_violation_and_prompt
description: 스마트스토어 예상 클린위반 스캔 기능 + 상품명/키워드/속성 AI 프롬프트 버튼 구축 (2026-07-02)
metadata: 
  node_type: memory
  type: project
  originSessionId: 9a2d9cae-85f4-4a32-8f5b-806fab248ce3
---

## 예상 클린위반 스캔 (2026-07-02 구축)
- 실제 클린위반 이력 102건 분석 결과: 중복상품 85%(87건), 원산지위반 5, KC인증위반 4, 상품명표기위반 2, 생활화학미인증 2, 가품/불법판매 각 1
- 이 패턴 기반으로 상품명 키워드 휴리스틱 스캔 구현 — DB(`SmartStoreProduct`)만 조회, 크롤링 아님
- 백엔드: `apps/smartstore/views.py`의 `PredictedViolationListView`/`PredictedViolationDetailView`, URL `/smartstore/predicted-violations/`(전계정 카테고리별 건수, 5~6초 소요)와 `/<category>/`(상세, 개별 카테고리 0.5~1초)
- 카테고리 5종: duplicate(계정내 정확 중복, 신뢰도 높음) / danger(삼단봉·쌍절곤·정글도·서바이벌칼 등 위험물품, 높음) / origin(원산지 과장, 중간) / kc(유아완구 키워드, 낮음-오탐多) / chem(생활화학 키워드, 낮음-오탐多)
- 프론트: `SmartStorePage.tsx`에 "예상 클린위반" 버튼(주황-빨강 그라데이션) → `PredictedViolationModal`
- 브랜드 키워드(나이키/디올 등) 매칭은 "디 올 뉴"(차량트림)/필라테스 등과 충돌해 오탐뿐 → 폐기
- **Why:** 사용자가 전계정 클린위반 예상품목을 지속적으로 확인하고 싶어함(엑셀 요청 후 대시보드 상시 노출 요청)
- **How to apply:** 새로 크롤된 계정이 늘어도 자동으로 전체 SALE 상품 대상 스캔되므로 추가 유지보수 불필요. 키워드 사전은 `views.py`의 `_TACTICAL_KW`/`_KC_KW`/`_CHEM_KW`/`_ORIGIN_KW` 등 상수로 관리

## 상품명·키워드·속성 최적화 AI 프롬프트 (2026-07-02)
- 프롬프트 파일: `/home/rejoice888/PUBLIC/스마트스토어_상품명키워드속성_프롬프트.txt` — 11번가 프롬프트와 동일 스타일, 클린위반 실측 패턴 반영(중복상품·원산지·KC인증·생활화학·위험물품·브랜드도용)
- 출력 JSON: status(ok/위험/확인필요/중복의심), product_name, search_tags(최대10), attributes, checklist
- 프론트: `SmartStorePage.tsx` 우측에 "AI 프롬프트" 버튼 → `SmartStorePromptModal.tsx`(복사 전용, 11번가/지마켓/옥션 프롬프트 모달과 동일 패턴 — ChatGPT/Claude에 수동 붙여넣기용)
- **Why:** 사용자가 상품명 최적화를 요청했으나 기존 규칙기반 `apply_ss_products.py`(CATEGORY_KEYWORDS)는 주노그노(문구류) 카테고리 전용이라 다른 계정엔 커버리지 5% 미만 → AI 기반이 필요
- **How to apply:** [[project_smartstore_ai_optimize_pipeline]] (자동화 파이프라인 구축 시 참조 — Claude API로 상품명+검색태그(seoInfo.sellerTags, {"text":..} 형식)+속성을 자동 PUT하는 명령 작성 중)

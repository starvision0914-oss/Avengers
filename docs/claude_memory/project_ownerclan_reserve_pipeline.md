---
name: project_ownerclan_reserve_pipeline
description: "예비상품(/ownerclan)=오너클랜 등록대기 스테이징, 나의상품과 UI 동일 기준"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2652a85c-f4de-41b6-8478-ea5e69ec25ed
---

Avengers 프론트: `/ownerclan` 사이드바 라벨 **예비상품**(OwnerclanProductsPage)은 오너클랜 등록대기 상품 대기열. 거기서 선택→복사하면 **나의 상품**(`/myproduct-wholesale` MyProductPage)으로 넘어감. 라우트 주의: `/myproduct`는 ElevenMyProductsPage, 도매 나의상품은 `/myproduct-wholesale`.

**UI 통일 기준 = 예비상품**(2026-06-14 사용자 확정). 나의상품을 예비상품에 맞춤: 헤더 검색창 제거(새로고침·다크모드만), 액션바 그룹핑·스타일 동일+그리드뷰토글·중복삭제 추가(CSV/품절/동기화/복사는 오너클랜 원본 전용이라 제외), 번호식 페이지네이션. 백엔드 `my/products/dedupe/`(services.dedupe_my_by_product_name) 신규.

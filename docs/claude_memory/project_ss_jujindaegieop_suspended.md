---
name: ss-jujindaegieop-suspended
description: 스마트스토어 유진대기업(계정17) 네이버 이용정지로 크롤링/대시보드에서 제외
metadata: 
  node_type: memory
  type: project
  originSessionId: 7bfbc7f2-6086-4ea9-9f13-e82f74ef6633
  modified: 2026-08-22T22:38:37.118Z
---

## 유진대기업(SmartStoreAccount id=17) 이용정지 처리 (2026-08-23)

- 사용자 확인: 현재 네이버에서 이용정지 상태 (상품 0개, 판매 0건과는 별개로 계정 자체가 정지됨)
- 이전에 겪던 Commerce API `403 Forbidden` 토큰발급 실패([[project_smartstore_commerce_api_status]] 참고 — 유진스타일 403은 별개 계정)는 상품 미등록이 원인으로 추정했으나, 실제로는 이용정지가 근본 원인이었을 가능성 높음
- 조치: `is_active=False`로 변경 → `crawl_smartstore`, `crawl_smartstore_adcost`, `crawl_naver_product_adcost`, 대시보드(`apps/smartstore/views.py`) 전부 `is_active=True` 필터라 자동 제외됨
- 로그인ID/PW/Commerce API키/시크릿은 DB에 그대로 보존 (삭제 안 함), memo 필드에 상태 기록해둠

**Why:** 이용정지 계정을 계속 크롤링 시도하면 의미없는 실패 로그/알림만 쌓임. 정지 해제 여부는 사용자만 확인 가능.
**How to apply:** 사용자가 "유진대기업 이용정지 풀렸다"고 알려주면 `SmartStoreAccount.objects.filter(id=17).update(is_active=True)`로 즉시 복구. 그 전까지는 대시보드/크롤 대상 목록에 안 보이는 게 정상이니 "왜 빠졌지" 헷갈리지 말 것.

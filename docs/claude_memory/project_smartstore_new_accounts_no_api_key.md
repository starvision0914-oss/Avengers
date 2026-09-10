---
name: project_smartstore_new_accounts_no_api_key
description: 2026-09-06 신규 등록 스마트스토어 계정 10개 수집 0건 — 원인은 이용정지, API키 등록 보류(사용자 확인 2026-09-10)
metadata: 
  node_type: memory
  type: project
  originSessionId: 4c6cd55d-0535-40f3-8d75-3377621bd2b2
  modified: 2026-09-10T02:18:43.891Z
---

2026-09-10 크롤 점검(01:00 `cron_smartstore.sh` 로그)에서 발견: 전체 27개 활성 스마트스토어 계정 중 아래 10개가 `commerce_api_key`가 비어있고 `merchant_no`도 한 번도 채워진 적 없음(created_at=2026-09-06). Selenium으로 merchantNo 추출을 매일 시도하지만 실패 → 판매통계/광고비는 즉시 스킵되고, 상품 API도 응답 없음이라 Commerce API 폴백 조건(`not ok and account.commerce_api_key`)이 `commerce_api_key` 부재로 발동하지 않음 → 상품 0건 유지(기존 데이터 삭제는 안 함), 판매/광고비 0건이 매일 조용히 반복됨(텔레그램 알림 없음).

영향 계정(login_id): ijaeyun044@gmail.com(스타피씨에스), ij9602847@gmail.com(스타드림딜), i92372664@gmail.com(스타고급상점), jinag7460@gmail.com(스타블루오션), starvis0914@gmail.com(스타웨이브), starvis7942@gmail.com(스타프랜즈), sjsiahw@gmail.com(스타그노), rejoice7942@gmail.com(스타전문점), dlrmsgh01231@gmail.com(스타코리아), rejoice08217@gmail.com(유진오피스).

**Why:** [[project_smartstore_commerce_api_status]] (2026-07-01자, "전체계정 등록완료")는 그 시점 17개 계정 기준이었고, 그 이후 신규 추가된 10개 계정은 온보딩(Commerce API 키 발급·등록)이 누락된 채 방치됨. 코드 로직 자체는 정상(폴백 설계 의도대로 동작) — 데이터/설정 누락이 원인.
**How to apply:** 스마트스토어 관련 작업 시 이 10개 계정은 매출/광고비 데이터가 없다는 전제로 판단할 것. 사용자가 나머지 계정처럼 API 키를 등록하길 원하면 네이버 커머스API센터에서 발급 후 `SmartStoreAccount.commerce_api_key/commerce_secret_key`에 저장 — 코드 수정 불필요. [[project_smartstore_commerce_api_status]] 갱신 필요(구 메모는 2026-07-01 시점 스냅샷일 뿐).

**2026-09-10 사용자 확인**: 이 10개 계정은 현재 스마트스토어 자체가 이용정지 상태(원인은 API 키 미등록이 아니라 정지)라 API 키 등록은 의미 없음 — 정지 해제 전까지 보류, 다음에 처리. 크롤 실패는 계속 정상 동작(정지 상태이니 당연한 결과)이므로 추가 조사/알림 불필요.

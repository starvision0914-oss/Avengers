---
name: sales-upload-dedup-fix
description: 매출 엑셀 업로드 중복 레이스컨디션 발견·수정(2026-07-10) — 같은 파일 재제출 3분내 자동 차단
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

`SalesUploadView`(`/api/sales/upload/`)는 이미 "최신 파일이 이긴다" 교체로직을 갖고 있었음 — 업로드 시 파일에 있는 (플랫폼,셀러)별로 그 기간[min~max] 기존 SalesRecord를 삭제 후 재삽입(정상 순차 업로드라면 자동으로 최신 데이터로 갱신됨, 별도 조치 불필요).

**발견한 버그**: 같은 파일(예: `통합주문관리-[아이리스]위탁장부-검색결과....xls`)이 8초 간격으로 두 번 업로드되면(더블클릭/네트워크 재시도), 두 요청의 delete→insert가 겹쳐 실행되며 일부 행이 레이스컨디션으로 중복 저장됨(실측: 2031행 파일, 90행 진짜중복·594,308원 매출 과대계상 — order_number가 자주 빈값이라 order_datetime+금액+수량까지 봐야 진짜 중복인지 판별 가능, order_date만으로 판별하면 오탐 많음[[project_sales_upload_dedup_fix]] 자체 교훈).

**수정**: `SalesUploadView.post()` 최상단에 idempotency 가드 추가 — 같은 `file_name`이 최근 3분 내 이미 성공 처리됐으면 재처리 없이 이전 `SalesUploadLog` 결과를 그대로 반환.

**Why**: 사용자가 "7월은 마지막 엑셀자료가 들어가야해 중복계산 안되는 방법 있을까" 요청.
**How to apply**: SalesRecord 매출 숫자가 이상하다는 신고가 오면, 먼저 `SalesUploadLog`에서 같은 파일명이 짧은 간격(분단위)으로 중복 업로드된 적 있는지 확인. 진짜 중복 판별은 (seller_id, product_code, order_datetime, total_price, quantity) 전부 일치해야 함 — order_date만 쓰면 같은날 다른 주문을 오탐함.

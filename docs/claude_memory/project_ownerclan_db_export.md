---
name: ownerclan-db-export
description: 예비상품(/ownerclan) 전체 DB CSV 다운로드 기능 구축완료(2026-07-11)
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

`/ownerclan` 페이지에 "DB 전체 다운로드" 버튼 추가 — 필터 없이 전 15만2천여건을 CSV로. 기존 "엑셀 받기"(필터 적용, 18개 컬럼 요약)와는 별개 기능.

`OwnerClanProductDbExportView`(apps/ownerclan/views.py) — `StreamingHttpResponse`로 메모리효율 스트리밍(150k행 × 필드 다수라 openpyxl 대신 csv 사용). **orig_*(원본대조용 내부컬럼)와 detail_html/notice_html/header_text 등 거대 텍스트필드는 제외**— 포함시키면 파일이 엑셀에서 열기 힘들 정도로 커짐. 워크스페이스(예비상품/상품가공) 전환은 기존 `services._t()`가 반환하는 실제 테이블명으로 판별(`ProcessingProduct`는 `_build_processing_product()`로 동적생성된 모델 — `MyProduct`(나의상품, 별개 테이블)와 혼동 주의).

프론트는 [[feedback_window_open_bearer_auth]] 패턴대로 axios `responseType:'blob'` 사용(window.open 금지).

**Why**: 사용자가 "오너클랜에 디비다운로드" 요청.
**How to apply**: 오너클랜 관련 신규 모델(ProcessingProduct 등) 참조 시 `^class` grep만으로는 동적생성 모델을 놓칠 수 있음 — `_build_processing_product()`처럼 `type()`으로 만드는 패턴이 있는지 확인할 것.

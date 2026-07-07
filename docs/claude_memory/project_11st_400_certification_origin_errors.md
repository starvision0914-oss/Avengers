---
name: project_11st_400_certification_origin_errors
description: 11번가 Hulk API 상품수정 시 홍보문구 추가하면 발생하는 3가지 400에러(RAW_MATERIAL/ORIGIN/CERTIFICATION) 원인·대응
metadata: 
  node_type: memory
  type: project
  originSessionId: c8272f73-4610-4a02-b107-7e70ef950e0e
---

상품명 최적화(scripts/_apply_11st_decisions.py) 중 발견. 상품명만 바꿀 땐 통과하다가 **홍보문구(advertisementPhrase)를 같이 넣으면** 그 상품과 무관해 보이는 기존 데이터 결함 때문에 저장이 막히는 사례 3종:

1. **RAW_MATERIAL**: `rawMaterial.code=='05'`("상품별 원산지는 상세설명 참조")인데 `origin.code`가 남아있으면 충돌 → `origin.code`를 정상값(예: '03')에서 함부로 지우면 오히려 **ORIGIN 에러를 새로 만들어냄**(2026-07-04 최초수정 때 이 실수를 함 — rawMaterial=05라고 무조건 origin.code를 지우면 안 됨, 실제 RAW_MATERIAL 에러가 난 경우에만 반응형으로 지울 것).
2. **ORIGIN**("원산지 정보는 필수"): 원산지 코드 자체가 비어있는 상품. 실제 원산지를 모르므로 허위 입력 불가.
3. **CERTIFICATION**("인증정보를 반드시 입력"): 카테고리가 KC 인증 필수인데 인증정보가 비어있는 상품(장난감/퍼즐 등). 이름만 바꿔도(홍보문구 없이도) 막히는 경우도 있음 — 진짜 KC인증번호 없이는 자동화로 해결 불가.

**Why**: 허위 원산지/인증정보 입력은 법적 문제라 자동으로 채우면 안 됨. 하지만 상품명 최적화 자체는 막을 이유가 없음.

**How to apply**: `_apply_11st_decisions.py`에 반응형 재시도 로직 구현됨 — RAW_MATERIAL 에러 시에만 origin.code 정리 후 재시도, ORIGIN/CERTIFICATION 에러 시엔 홍보문구를 원본 그대로 되돌리고 상품명만 재시도. 재시도(홍보문구 제외)도 실패하면(주로 CERTIFICATION 카테고리) 그 상품은 skip하고 사용자에게 "진짜 인증정보 필요, 자동화 불가"로 보고. 향후 다른 계정 처리 시에도 이 스크립트 그대로 재사용 가능.

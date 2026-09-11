---
name: project_11st_seller_code_edit_origin_trap
description: "11번가 hulk API로 판매자관리코드(sellerManagementCode) 수정 가능하나, 원재료유형=05+원산지코드 populated 조합이면 저장 자체가 거부됨"
metadata:
  type: project
  originSessionId: 3a442b17-84db-4700-800a-337d103e410d
  modified: 2026-09-11T12:03:16.041Z
---

**배경**: 도매마트(L코드) 원가 매칭 오류로 역마진 오탐이 뜨는 상품들 — `ElevenMyProduct.seller_product_code`(=11번가 실제 "판매자관리코드")가 `LCE_SX_...` 형태라 `l_code_status`와 자동 매칭되는데, 이 매칭 자체가 틀려서(엉뚱한 도매가 연결) 역마진으로 잘못 잡힘. 해결책 = 해당 상품들의 판매자관리코드를 LCE_ 패턴이 아닌 값(상품명 기반)으로 바꿔서 자동매칭 대상에서 빼는 것. 사용자가 starvis7942 계정 일부 상품엔 이미 수동으로 이렇게 해뒀던 걸 실측 확인(2026-09-11).

**판매자관리코드 실제 변경 방법**: `apps/cpc/management/commands/optimize_11st_product_names.py`에 이미 구현된 hulk API 패턴 재사용.
- 세션: `_get_session(acct)` — 셀러오피스(soffice.11st.co.kr) 쿠키 로그인 후 requests 세션.
- 조회: `_get_hulk_detail(sess, prd_no)` → `GET https://apis.11st.co.kr/product/hulk/v2/product/{prd_no}/detail` — 상품 전체 상세 dict 반환. 필드명 `sellerManagementCode`.
- 수정: 받은 dict를 그대로 mutate(`detail['sellerManagementCode'] = new_code`) 후 `_put_hulk_update(sess, prd_no, detail)` → `PUT .../update?createCd=1201&siteCode=` (전체 dict 그대로 재전송 — 부분수정 아님).

**⚠️ 함정(2026-09-11 실측, 5개 상품 전부 재현)**: GET으로 받은 detail을 그대로 PUT하면 무관한 필드 때문에 400 에러가 날 수 있다 — `rawMaterial.code=='05'`("원재료 유형: 상품별 원산지는 상세설명 참조")인데 `origin.code`에 값(예:'01')이 들어있으면 `"원재료 유형이 \"상품별 원산지는 상세설명 참조\"일 경우 원산지 코드는 입력 불가합니다"` 400 에러. **GET은 이 조합을 문제없이 반환하지만 PUT은 거부** — 즉 예전에 저장될 땐 검증이 느슨했는데 지금은 재저장 시 막힘. 확인한 5개 상품 전부(도매마트 L코드 계열) 이 조합이었음 — 같은 방식으로 일괄등록된 상품군은 전부 이 함정에 걸릴 가능성 높음.

**Why**: 사용자가 판매자코드만 바꾸려 했는데 무관한 원산지 필드 검증에 막힘 — 원산지 표시는 규제 관련 필드라 임의로 비우기 전에 사용자 확인 필요하다고 판단해 진행 중지함(2026-09-11, "이번에는 중지"로 답변받음 — 아직 미해결).

**How to apply**: 다음에 이 계열(도매마트 L코드) 상품의 hulk API 필드를 수정할 일이 생기면, PUT 전에 `rawMaterial.code=='05'`인지 먼저 확인하고 그렇다면 `origin.code`를 비워야 저장된다는 걸 미리 알고 접근할 것(사용자에게 원산지코드를 비워도 되는지 재확인 후 진행). [[project_gmarket_biocide_regulation]]처럼 규제 관련 필드는 항상 사용자 확인 거칠 것.

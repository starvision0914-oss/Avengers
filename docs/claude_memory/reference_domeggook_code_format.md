---
name: reference-domeggook-code-format
description: "스마트스토어 판매자관리코드(seller_management_code)가 순수 숫자 7자리면 \"도매매코드\"로 명칭"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 72798bef-7b95-4ff6-9ea6-b86c367edb55
  modified: 2026-09-03T23:16:25.876Z
---

스마트스토어 상품의 판매자관리코드(seller_management_code)가 W로 시작하지 않는 "기타" 코드 중,
**순수 숫자 7자리**로만 이루어진 코드는 "도매매코드"라고 부른다(사용자 지정, 2026-09-04).

**Why:** 오너클랜 소싱 상품은 W+영숫자(대부분 16진수, 일부는 W+7자리 비16진수 영숫자도 있음 —
[[project_smartstore_wcode_regex_gap]] 참고) 코드를 쓰는 것과 대비해, 도매매(스피드고 프로젝트가
연동 대상으로 삼은 도매 사이트, [[project_gmarket_biocide_regulation]]과 무관) 소싱 상품은 7자리
순수 숫자 판매자코드를 쓴다는 게 사용자 확인 사항. 앱 `apps/speedgo`(SpeedgoItem.domemea_no)가
도매매 연동 파이프라인이지만 2026-09 기준 실제 데이터가 거의 없어(테스트용 1건) DB로는
교차검증 불가 — 사용자의 직접 확인에 근거한 명칭.

**How to apply:** 스마트스토어 상품 분석/보고 시 seller_management_code가 W로 시작하지 않고
정규식 `^[0-9]{7}$`에 맞으면 "도매매코드"로 지칭. 8자리 숫자코드 등 다른 길이는 도매매코드가
아니라 그냥 "기타코드"로 유지(사용자가 7자리만 지정함). 예: 스타컴퍼니(starvisi7942)에 169건 존재.

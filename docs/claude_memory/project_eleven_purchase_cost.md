---
name: project_eleven_purchase_cost
description: "11번가 나의상품 구매원가=오너클랜 공급가(ownerclan_price), 마켓가 아님 + 확인필요(역마진) 필터"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4b81a2de-3c94-48d2-a767-9d7a7a3fd4ae
---

11번가 나의상품(/myproduct) 구매원가(`ElevenMyProduct.purchase_cost`) = 예비상품 오너클랜의 **`ownerclan_price`(도매 공급가)**. 이전엔 `market_price`(마켓 권장판매가, 마진 포함)를 써서 cost_diff(=판매가−원가)가 거대 음수 → 가짜 역마진 15,169건이었음(market_price>ownerclan_price인 행이 286,707 전부). ownerclan_price로 교체 후 역마진 125건(집중관리 기준 94건)으로 정상화(2026-06-15).

**Why:** market_price는 "이 가격에 파세요" 권장가라 항상 공급가보다 큼 → 원가로 쓰면 안 됨. **How to apply:** 수정 위치 `apps/cpc/eleven_my_product_service.py`의 `_attach_purchase_cost()`(API 주입)·`refresh_purchase_costs()`(set-based UPDATE, 전체/증분 3곳). 코드 변경 후 `refresh_purchase_costs()` 전체 실행 + `pm2 restart avengers-backend` 필수.

**확인필요(역마진) 기능:** get_my_products(needs_check=True)→cost_diff<0만, 가장 심한 순(맨 위). 응답 needs_check_total. 프론트 ElevenMyProductsPage `⚠ 확인필요(N)` 토글+역마진 행 빨강배경(11st만).

**잔여(미해결):** ②단위 불일치(11번가 "x5개" vs 오너클랜 "x500개" 등 같은 셀러코드, 수량보정 필요) ③오염 데이터 ~7건(산업용기어유 WD0977F: ownerclan_price 967만, 자릿수 오류). 둘이 잔여 역마진 대부분. 관련 [[project_ownerclan_reserve_pipeline]] [[project_eleven_my_query_perf]].

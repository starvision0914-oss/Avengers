---
name: project-gmarket-daily-vs-monthly-design
description: 지마켓 상품별광고비를 11번가처럼 일별저장으로 바꾸면 정합성이 높아지는지 검토(보류)
metadata: 
  node_type: memory
  type: project
  originSessionId: 88045d6c-b9b8-4d0c-a791-3652c19433ed
---

2026-07-12, 사용자가 "지마켓도 11번가처럼 일별 크롤+중복제외 방식으로 바꾸면 정합성이 더 높아지지 않나?"라고 질문 → 검토 후 **일단 구조만 참고, 실제 변경은 보류**하기로 함.

**검토 결론:**
- 현재 지마켓(`GmarketProductAdCost`)은 `(계정,광고유형,상품,연,월)` 유니크 → 매일 크롤 시 그 달 전체를 delete+reinsert(당월 1일~오늘 누적 조회, "이번달(TM)" 프리셋). 크롤 중간 실패 시 최악의 경우 정상 데이터가 부실한 값으로 덮일 위험 있음.
- 11번가(`St11ProductDaily`)는 `(계정,상품,날짜)` 유니크로 하루치만 갱신 → 특정 날짜 크롤 실패해도 다른 날짜 기존 데이터는 안전. 정합성 측면에서 더 견고한 설계.
- 기술적으로는 지마켓 리포트도 캘린더 `SetDate`로 임의 기간(하루만) 지정이 가능해 보여 일별 방식 전환은 가능해 보임(크롤러 코드 `crawlers/gmarket_ad_report_crawler.py` 확인).
- 전환 시 비용: 크롤러가 "이번달 누적" 대신 "어제 하루" 범위로 조회하도록 로직 변경 필요 + 과거 이미 쌓인 월단위 스냅샷은 일별로 소급 불가(백필 어려움).

**How to apply:** 다음에 지마켓 상품별광고비 데이터 정합성 문제(부분 크롤실패로 월 데이터 오염 등)가 실제로 발생하면 이 메모를 근거로 일별 전환을 다시 검토할 것. 관련: [[project_gmarket_adcost_collected_at_gotcha]] (현재 월단위 구조의 함정), [[project_11st_cost_partial_loss]] (비슷한 range-delete 위험이 있었던 11번가 사례, 이미 수정됨).

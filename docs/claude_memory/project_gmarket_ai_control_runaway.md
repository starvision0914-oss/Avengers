---
name: project_gmarket_ai_control_runaway
description: 지마켓 AI광고 제어 _get_group_info 중복파싱 폭주버그(복수아이디)·강제중지·예약 동작
metadata: 
  node_type: memory
  type: project
  originSessionId: e76d08ca-b676-492c-8ef3-735797020404
---

지마켓 AI 광고 ON/OFF 제어(/ad-settings AI탭, gmarket_ai_control_crawler) 관련(2026-06-18):

- **폭주 버그(해결)**: `_get_group_info`가 `div.remarketing_table table` 중첩 셀렉터로 **같은 그룹행을 수십번 중복** 파싱 → 복수아이디 마스터(starvisi=서브 dlwodb000 등)에서 그룹 3개가 **300개+로 뻥튀기** → set_ai_onoff 300회+ 호출, 11분 런어웨이, 이력 300건+. **해결: group_no `seen` set으로 중복제거** (starvisi 실측 3개 확인). 안전장치: run_ai_schedule._run_on_with_date에 그룹>100이면 스킵 + page_load_timeout 40초.
- AI 진행사항 표는 seller_id(서브) 표시 — gmarket_id(마스터)만 쓰면 서브 구분 안 돼 똑같이 보임. seller_id에 서브(rejoice223/dlwodb000 등) 정확히 들어있음.
- **강제중지**: guard.request_control_stop/is_control_stop/clear_control_stop('gmarket') 플래그. run_control(cpc2/ai/combined)·_run_on_with_date 루프가 계정/그룹 사이에서 확인→중단(현재건 ≤40초 마무리). API: POST /cpc/gmarket-control/stop/. 크롬 안 죽여서 동시 11번가 무해.
- **계정선택 의미**: 수동=미선택이면 전체25계정 / **예약=미선택(0개)이면 크론 동작 안함(계정선택 필수)**. saveCpc2/saveAi가 selected_accounts 저장(이전 누락버그 수정).
- 간편 예약 OFF는 [[project_gmarket_11st_hourly_adcost]] 아님 — crawl_gmarket_cpc2가 --source schedule시 Cpc2Schedule.selected_accounts만 대상(전체 도는 버그 수정). 간편+일반 통합: include_cpc1(Cpc2Schedule 필드), cron_ad_combined(시각·요일 같을때만 통합 1로그인). [[project_11st_ad_strategy_schedule]]

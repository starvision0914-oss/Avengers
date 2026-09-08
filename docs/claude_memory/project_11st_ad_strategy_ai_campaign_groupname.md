---
name: project_11st_ad_strategy_ai_campaign_groupname
description: "11번가 전략설정 — AI추천/AI검색 캠페인은 광고그룹명이 '전체-' 관례를 안 따라 그룹 0개로 미적용되던 버그, 폴백 매칭으로 수정"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0f0cb927-fa1b-4978-9384-d14a26fab9db
  modified: 2026-09-07T17:08:23.799Z
---

[11번가 광고그룹 전략설정](project_11st_ad_strategy_schedule.md) 에서 tmxk26 계정의 AI추천_캠페인_1/2, AI검색_캠페인_1/2가 "캠페인 매칭"까지는 성공하는데 매번 "그룹 0개"로 끝나 아무것도 적용 안 되던 문제(2026-09-08 사용자 신고 "전략설정 해달라고 지시했는데 왜 안된거지").

**원인**: `crawlers/eleven_ad_strategy.py`의 `get_group_links()`가 광고그룹 이름이 `전체-`로 시작하는 것만 인식하도록 하드코딩돼 있었음. 이건 사용자가 수동으로 만든 캠페인(예: '자동_캠페인 0630')의 그룹 명명 관례('전체-1'…'전체-9')일 뿐이고, **11번가가 자동 생성하는 AI추천/AI검색 캠페인은 그룹명이 상품 카테고리명(건강식품_1, 고양이용품_1, 헤어케어_1 등)**이라 필터에 안 걸림 → 그룹 0개 → 조용히 아무 일도 안 일어남(에러 없음, 티 안 남).

**수정**(2026-09-08): `get_all_group_links()` 신설 — find_campaign_links와 동일한 MUI 테이블 행 구조(`//*[@id='root']//table/tbody/tr/td[2]/div/div/a`)로 그룹명 무관 전체 수집. `get_group_links()`는 기존 `전체-` 매칭을 먼저 시도하고 0개면 이 폴백을 사용 — 기존 '전체-' 관례 계정은 동작 그대로, AI 캠페인만 새로 커버됨.

**검증+실적용 완료**: tmxk26 AI추천_캠페인_1(100개 그룹), AI추천_캠페인_2(73개 그룹) 전부 평일 8~16시 스케줄 실제 적용·저장 완료(오류 0건, "잔여 불일치 0칸" 검증됨).

**남은 것**: `St11AdStrategySchedule`(id=2, enabled=True)에 tmxk26 외 jinag7461·tmxkdnpdlqm8·tmxkrmsh55 3개 계정도 같은 AI추천/AI검색 캠페인이 등록돼 있으나 아직 미적용 상태(2026-09-08 기준). 그리고 **더 근본적으로, 이 스케줄을 매일 자동 재적용할 크론 자체가 crontab에 등록돼 있지 않음** — `apps/cpc/management/commands/apply_st11_ad_strategy.py`가 존재하고 코드/문서상 "cron이 enabled면 매일 재적용"이라 돼 있지만 실제 crontab에는 `apply_st11_ad_strategy` 관련 라인이 전혀 없음. 지금까지의 실행은 전부 사용자가 UI에서 수동으로 누른 것(run_id가 10~20분 간격으로 계속 쌓인 이유). 사용자가 원하면 (1) 나머지 3계정 적용 (2) 매일 자동 재적용 크론 등록을 진행할 것.

[[project_11st_ad_strategy_campaign_race]]

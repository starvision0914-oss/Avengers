---
name: project_11st_ad_spike_schedule_guard
description: 11번가 CPC 증가감지시 8~16시 전략설정 자동적용 가드 신설(2026-09-07) — guard_11st_ad_schedule_on_spike
metadata: 
  node_type: memory
  type: project
  originSessionId: 5819c9b5-4ebb-4c4b-bfb1-e856ab5bec3c
  modified: 2026-09-07T11:48:08.848Z
---

11번가는 지마켓과 달리 "광고비 증가 감지시 자동 조치"가 전혀 없었다(텔레그램 알림만 있고 OFF 로직 없음). 조사해보니 `St11AdStrategySchedule`(전략설정=8~16시 노출 스케줄) 자체가 tmxkdnpdlqm8 1계정만, 그것도 enabled=False로 사실상 아무도 적용 안 되고 있었음 — 그래서 밤늦게까지 광고비가 계속 나가는 계정이 있었다(2026-09-07 tmxk26 18~20시 사이 3,674원, tmxkrmsh55 187원 소진 확인, `eleven_seller_office_stat.point` 잔액 diff로 발견).

**구축한 것(2026-09-07):**
- 신규 커맨드 `apps/cpc/management/commands/guard_11st_ad_schedule_on_spike.py`:
  1. `ElevenCostHistory`(CPC)에서 직전 70분 증가 계정 탐지(notify_11st_adcost_hourly와 동일 판정)
  2. 계정별로 `crawlers.eleven_ad_strategy.list_campaigns()`로 실제 캠페인명 라이브 조회
  3. `run_strategy()`로 그 계정 전체 캠페인에 8~16시·평일 스케줄 실제 적용(execute=True)
  4. `St11AdStrategySchedule`(단일 레코드)에 계정/캠페인 누적 병합 + enabled=True로 저장
  5. 텔레그램 통지
- `scripts/cron_11st_cost_hourly.sh`에 `notify_11st_adcost_hourly` 바로 뒤 단계로 추가 — 매시간(11,15,17~22시, 평일) 자동 실행.

**Why:** 지마켓의 `cron_gmarket_hourly_ad_guard.sh`(증가시 완전 OFF)와 같은 취지지만, 11번가는 완전 차단이 아니라 "8~16시만 노출"로 시간 제한만 거는 방식을 사용자가 선택함([[project_gmarket_hourly_ad_guard]] 참고, 유사 패턴).

**How to apply:** 11번가 광고비 관련 문의 시 이 가드가 매시간 자동으로 도는 중임을 전제. 계정 하나당 캠페인 그룹 수가 많으면(예: tmxkrmsh55 27개+ 그룹) 적용에 10분 이상 걸릴 수 있음 — 정상. `St11AdStrategySchedule`은 단일 레코드라 이 가드가 계속 계정/캠페인을 누적시킴(한 번 걸린 계정은 계속 스케줄 유지 대상).

관련: [[project_11st_ad_strategy_schedule]] [[project_11st_ad_strategy_campaign_race]]

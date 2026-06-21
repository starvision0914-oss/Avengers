---
name: project_gmarket_adcontrol_busy_guard
description: 지마켓 광고제어(AI/CPC2/통합) 누적·진행상태 오표시 결함과 adcontrol busy 마커 해결
metadata: 
  node_type: memory
  type: project
  originSessionId: 3ffd271f-9d85-433f-ba63-5fc9965d018e
---

지마켓 광고 ON/OFF 제어(AI·간편CPC2·통합)는 **단일 브라우저 순차**(계정 1개씩, `for acct in qs`)이고 동시실행은 `guard.preflight(wait=True)` 전역락으로 막혀 있음. 하지만 2가지 결함 있었음(2026-06-21 수정):

**① 진행상태 오표시**: `GmarketControlStatusView`가 `ps`로 프로세스(`run_ai_schedule` 등)를 찾아 실행판정 → **대시보드 버튼은 백엔드 스레드**(`AiControlView`/`Cpc2ControlView`가 `th.Thread`로 `run_control` 직접호출)라 ps에 안 잡혀 "실행중인데 아님"으로 표시(크론 프로세스만 잡힘).

**② 누적**: 제어 뷰가 POST마다 가드없이 새 스레드 → 각자 preflight(wait=True 최대30분)로 줄섬 → 동시는 아니나 클릭 여러번/크론겹침이 **차례로 다 실행(누적)**.

**해결 = adcontrol busy 마커**(`eleven_block_guard.py`): `/tmp/avengers_gmarket_adcontrol.busy`(pid|name|ISO시각). `try_acquire_adcontrol`(O_EXCL 원자획득, 죽은pid·45분초과면 스테일 자동해제), `clear_adcontrol_busy`, `adcontrol_busy_info`.
- 실행 함수 4곳(`gmarket_ai_control_crawler.run_control`, `gmarket_cpc2_control_crawler.run_control`, `gmarket_ad_combined_control.run_combined`, `run_ai_schedule` 명령) 시작에 `try_acquire`→실패시 **즉시 스킵**(줄세우기X), finally에 `clear`. 대시보드 스레드·크론 둘 다 같은 마커로 커버.
- 제어 뷰(Cpc2/Ai)는 사전 `adcontrol_busy_info` 체크 → 실행중이면 **409 "이미 실행 중"** 즉시 거절.
- 상태 뷰는 마커를 우선 신호로 읽어 스레드 실행도 정확히 "실행중" 표시.

참고: AI ON 경로가 둘로 갈림 — **크론=`run_ai_schedule`**(자체 preflight, AI 시작일=다음영업일 `_next_business_day`), **대시보드=`gmarket_ai_control_crawler.run_control`**. 강제중지(🛑)는 `/gmarket-control/stop/`(대시보드 버튼) 단일 트리거만 set(`request_control_stop`), 각 실행 시작시 `clear_control_stop`로 묵은플래그 제거(스테일 아님). [[project_11st_adoffice_ad_control]]

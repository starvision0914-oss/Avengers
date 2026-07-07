---
name: project_gmarket_11st_hourly_adcost
description: 지마켓·11번가 시간별 광고비 텔레그램(증가분) 크론 + 광고비 스케줄 통합 정리
metadata: 
  node_type: memory
  type: project
  originSessionId: 2652a85c-f4de-41b6-8478-ea5e69ec25ed
---

2026-06-15 구축. 계정별 시간별 광고비 증가분을 텔레그램 발송.

**지마켓**: `crawl_gmarket_cost`(스냅샷 GmarketDepositSnapshot: CPC=gmarket_cpc+auction_cpc, AI=ai_usage) → `notify_gmarket_adcost_hourly`(직전 스냅샷 대비 증가분). 형식 `rejoice666  CPC 15,000(+6,200) / AI 8,000(+1,000)`. cron `cron_gmarket_cost_hourly.sh` 매시간 09-19.

**11번가**: CPC만(AI매출업은 지마켓 전용). `notify_11st_adcost_hourly`가 ElevenCostHistory(transaction_type='CPC') 오늘누적+직전1시간(window-min 70) 집계. cron `cron_11st_cost_hourly.sh` 매시간 17-23.

**스케줄 통합(중복 제거)**: 지마켓 cost(9,14)·today_refresh(13,16)·17check(18) → 시간별 9-19로 흡수, 17check는 22시 마감만. 11번가 cost(11,15,18,20,22)→주간 11,15만 + 저녁 17-23 시간별, evening_cpc(18-23)·adcost_17check(17) 제거(시간별이 대체).

**충돌가드**: 시간별 스크립트가 파일락+pgrep(gmkt_/ad_report/keywords/crawl_11st_cost) 확인 후 겹치면 스킵. crontab 수정 시 `crontab -l > 백업` 먼저(2026-06-15 sed `#`구분자 사고로 2줄만 남겨 복원함 — Python으로 재작성 권장).

08:00 지마켓 상품별크롤이 06-14~15 스킵된 원인=일회성 키워드백필(06-13밤~06-15 08:18)이 락점유. 백필 끝나 정상화.

## 2026-07-06 발견·수정: 11번가 알림 통째 스킵 버그
`cron_11st_cost_hourly.sh`가 다른 11st 크롤 실행 중이면 pgrep 가드로 "수집"뿐 아니라 **알림(notify_11st_adcost_hourly)까지 통째로 건너뜀** — 실제로 17시 알림이 이 버그로 누락된 걸 로그에서 확인. 알림은 ElevenCostHistory만 읽는 작업이라 크롤 충돌과 무관하게 항상 실행되도록 스크립트 분리(크롤만 조건부 스킵, 알림은 무조건 실행). 사용자 요청으로 스케줄도 대시보드 수집시간과 동일하게 확장: `0 17-20 * * 1-5` → `5 11,15,17,18,20,22 * * 1-5`(정시+5분, crontab 백업 후 변경). 수정 직후 테스트런으로 실제 텔레그램 발송 확인 완료.

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

---
name: project_toss_integration
description: "토스쇼핑 파트너스 광고비 연동 — 계정1개, 크론 01:00(전일확정), 로그인은 토스계정 그대로"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5819c9b5-4ebb-4c4b-bfb1-e856ab5bec3c
  modified: 2026-09-06T12:07:52.340Z
---

토스쇼핑 파트너스(shopping-seller.toss.im) 광고비 수집 — 2026-09-02 최초 구축 완료.

**구조:**
- 계정: TossAccount 1개(starvis7942@gmail.com), 광고센터 별도 로그인 없음, 2FA 없음
- 크롤러: `crawlers/toss_crawler.py` — `/ads` 페이지 기간프리셋(오늘/어제) 버튼 클릭 후 캠페인 표 스크래핑
- DB: TossAccount, TossAdCost(계정합계), TossCampaignAdCost(캠페인별)
- 전역락 platform='toss' 별도 신설(다른 플랫폼과 동시 실행 가능)
- 대시보드: `/smartstore` 페이지 PLATFORM_TABS '토스' 탭, `TossDashboard.tsx`

**크론: 매일 01:00** (전일 확정치, `cron_toss_adcost.sh` → `crawl_toss_adcost --when=yesterday`)
- 2026-09-06: 08:00에서 01:00으로 변경(사용자 요청 "다른 쇼핑몰과 동일하게" — 스마트스토어/롯데온 등 "전일확정" 계열 크론과 시간대 통일)

**Why 01:00로 바꿨나:** 08:00엔 11번가/지마켓 등 주간 크롤이 몰리는 시간대라 자원경합 가능성. 진단 당시 08:00 크론은 시스템로그상 매일 실행은 됐으나 DB엔 그날 밤 23:01경에야 반영되는 이상현상이 있었음(정확한 원인은 마침 겹친 서버재부팅으로 /tmp 로그가 날아가 재구성 불가). 01:00은 스마트스토어·롯데온이 쓰는 조용한 시간대.

**How to apply:** 토스 관련 문의 시 이 구조를 기준으로 답변. 크론 로그는 `/tmp/cron_toss_adcost.log`에만 남으므로 재부팅되면 사라짐 — 재발 원인 추적하려면 재부팅 전에 확인 필요.

관련: [[feedback_crontab_pipe_danger]] [[project_cron_log_no_rotation]] [[project_platform_lock_split]]

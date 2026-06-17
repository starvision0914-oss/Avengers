---
name: project_gmarket_hourly_false_skip
description: 지마켓 시간별 광고비 미수집 원인 — pgrep이 모니터/디버그 셸을 오탐해 매시간 스킵
metadata: 
  node_type: memory
  type: project
  originSessionId: 2652a85c-f4de-41b6-8478-ea5e69ec25ed
---

지마켓 시간별 광고비(cron_gmarket_cost_hourly.sh, 09-19시)가 06-16·06-14 등 0건 수집된 근본원인:

**pgrep 오탐.** 충돌방지 로직 `pgrep -f 'crawl_gmarket_ad_report'`가, 다른 세션이 띄운 `bash -c while pgrep -f "crawl_gmarket_ad_report --eid …"` **디버그/모니터 셸의 명령줄 문자열까지 매칭** → 실제 python 크롤이 없는데도 "다른 지마켓 크롤 실행중 — 스킵"을 매시간 반복. 결과: 광고비는 나갔지만 GmarketDepositSnapshot 0건.

**수정(2026-06-17):** pgrep 패턴을 `manage.py crawl_gmarket_ad_report`(실제 python 실행형)으로 변경 → `while pgrep …` 셸은 `manage.py shell -c`라 매칭 안 됨. keywords/grade도 동일 적용.

**How to apply:** 지마켓 시간별 수집이 비면 (1) `pgrep -af crawl_gmarket` 로 모니터/디버그 셸 잔재 확인·정리, (2) 실제 python 크롤(`ps -eo cmd|grep '[p]ython.*crawl_gmarket'`) 유무 확인. 디버그용 `while pgrep` 루프 만들 때 크롤명 문자열이 cron 감지에 걸리지 않게 주의. GmarketDepositSnapshot은 __date(USE_TZ) 조회 0건 함정 → 범위조회. [[project_gmarket_adcost_source]] [[project_crawl_lock_parser_bug]] [[timezone_pitfalls]]

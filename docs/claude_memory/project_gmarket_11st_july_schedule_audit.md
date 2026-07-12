---
name: project-gmarket-11st-july-schedule-audit
description: 2026-07 지마켓/11번가 전체 크론 스케쥴링 크롤링 문제여부 진단 결과(시점 스냅샷)
metadata: 
  node_type: memory
  type: project
  originSessionId: 88045d6c-b9b8-4d0c-a791-3652c19433ed
---

2026-07-12 사용자 요청으로 7월 1일~12일 지마켓/11번가 전체 크롤 스케쥴을 크론로그+DB 교차검증으로 진단. **전체적으로 정상, systemic 장애 없음.**

**확인 내용:**
- 지마켓 상품별광고비+키워드(cron_gmarket_ad_report_kw.sh 08:20): 12일 전부 시작/종료 로그 정상, 오늘 기준 28개 계정 전부 최신 갱신 확인 (최초엔 DB 9일 결측으로 오판할 뻔함 → [[project_gmarket_adcost_collected_at_gotcha]] 참고)
- 11번가 광고비(ElevenCostHistory): transaction_datetime 기준 평일 연속 수집 확인, 주말(7/4-5, 7/11-12) 무데이터는 [[project_11st_weekend_ad_off]] 의도된 정상. 7/10에 대량 created_at 리로드 이벤트 있었으나 실거래 데이터 자체는 끊김 없음
- 11번가 IP 글로벌프리즈: 7/3 저녁 2회(18:30/19:17/20:30, 각 30분) 발생 — [[project_11st_ip_block_prevention]] 설계대로 자동복구, 이후 재발 없음
- 개별 계정 단위: dlrmsgh013(11번가) 3회접속실패→스킵, rejoice119 Chrome 크래시 1회, rejoice987/911/dlwodbs333/666(지마켓) 로그인실패 1~2회 — 전부 [[project_crawling_rule]] 3진아웃 룰대로 다음계정 진행, 재발 없이 단발성
- 계정별 synced_at 신선도: 11번가 71개 활성계정, 지마켓 31개 활성계정 전부 7/8 이후 갱신 확인 — [[project_smartstore_product_sync_outage]] 같은 장기방치 없음
- 부수 발견(무관): cron_gmkt_cost_hourly.sh 실행 시 `apps.club.views.pitching_staff_view` AttributeError 2회 — club 앱 URL설정 문제로 지마켓 크롤과 무관, 크롤 자체는 성공(25-26/26)했으므로 급하지 않으나 미해결
- 부수 발견(경미): 진단 시점 고아 Xvfb/chrome 프로세스 2개 잔존 — [[project_crawler_zombie_pc]] 리퍼가 있으나 완전 박멸은 아님

**How to apply:** 이 결과는 2026-07-12 15시경 스냅샷. 이후 재진단 시엔 이 메모를 그대로 믿지 말고 로그/DB 재확인할 것(특히 club 앱 에러가 방치돼 있는지, 좀비프로세스가 누적되는지는 추적 가치 있음).

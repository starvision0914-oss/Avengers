---
name: project-11st-ad-strategy-campaign-race
description: 11번가 전략설정(/ad-settings) 캠페인 불러오기가 0개로 실패했던 원인 — 캠페인 생성 직후 조회 시 반영지연
metadata: 
  node_type: memory
  type: project
  originSessionId: 8a1a0899-544e-4def-815c-d319d327b2bb
  modified: 2026-08-11T21:35:22.729Z
---

[11번가 광고그룹 전략설정](project_11st_ad_strategy_schedule.md) 페이지에서 "캠페인 불러오기"·"강제 갱신" 둘 다 "캠페인을 못 찾았습니다"로 실패한 사례(2026-08-12, 계정 tmxkdnpdlqm8) 조사.

**원인**: St11AdStrategyLog 조회 결과 실제 크롤은 정상 실행됐고 페이지 접속·로그인도 성공했으나 `find_campaign_links`가 0건 반환. 해당 캠페인('자동_캠페인 0812')은 생성시각이 06:27:12였고, 조회 시도는 06:27:37(25초 후)·06:29:08(2분 후) 둘 다 실패. 같은 계정으로 몇 분 뒤 수동 진단 크롤을 돌리니 정상적으로 1건 잡힘 — 즉 코드/셀렉터 버그가 아니라, **캠페인을 막 생성한 직후엔 11번가 서버 쪽 목록 반영이 지연**되어 조회해도 0건으로 나오는 레이스 컨디션.

**조치**: `crawlers/eleven_ad_strategy.py`의 `list_campaigns()`에 재시도 로직 추가 — 0개면 8초 대기 후 페이지 재진입해 최대 2회 재조회(2026-08-12). `pm2 restart avengers-backend`로 반영 완료.

**How to apply**: 캠페인을 막 새로 만든 직후에는 "불러오기"가 바로 안 잡힐 수 있음을 안내하고, 잠시 후(또는 자동 재시도로) 다시 시도하면 됨. 새로운 "캠페인 0개" 신고가 오면 먼저 St11AdStrategyLog(run_id)로 실제 실패 유형(로그인 실패/DOM 못찾음/타이밍)부터 구분할 것.

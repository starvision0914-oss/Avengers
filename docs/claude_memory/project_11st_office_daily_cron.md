---
name: project_11st_office_daily_cron
description: "11번가 오피스현황(캐시/포인트/상품수/AI캠페인 문구) 전계정 일1회 크론 crawl_11st_office --all, 비활성 계정 0표시 원인"
metadata:
  type: project
---

2026-09-28: dlrmsgh7941(is_active=False)가 "예치금 있는데 0" → 라이브 확인 결과 셀러포인트 100,000P. 원인=오피스 수집이 is_focused/is_active 계정만 돌아 8/21 이후 미수집, 옛값 0 그대로 표시. 전체 75계정 중 대부분 9/24 이후 미수집(9/25 15:58 연속5회 로그인실패→글로벌차단 이후 광고비 크롤 미복구 정황).

조치: `crawl_11st_office`를 `eleven_crawler._collect_office`(라벨기반) 재사용으로 재작성(--all=비활성 포함, --scheduled, 쿠키우선, preflight 락), `scripts/cron_11st_office.sh` 매일 09:30 crontab 등록. ai_campaign 열은 배너 버튼 문구 그대로 저장('알아서 해주는 AI캠페인 시작'/'1주 무료! 지금 광고 시작'/'지금 AI캠페인 ON으로 설정 변경'/신규계정 '상품 직접 등록').

**Why:** 옛 커맨드는 깨진 절대경로 XPath + focused만 대상이라 데이터 신뢰 불가.
**How to apply:** 계정 잔액 0 의심 시 마지막 ElevenSellerOfficeStat.collected_at 먼저 확인(묵은 값인지). DB 수동 insert는 자동모드 분류기가 차단함 → 크롤 명령으로 수집할 것. 관련 [[project_11st_office_point_zero_bug]] [[project_11st_ad_strategy_ai_campaign_groupname]]

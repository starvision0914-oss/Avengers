---
name: gmarket-ad-report-status-fixes
description: 지마켓 상품별광고비 대시보드 실행중표시/강제중지/0원계정 오탐 3종 수정 내역
metadata: 
  node_type: memory
  type: project
  originSessionId: b8d92864-667d-464d-ac72-2fa7126365a0
  modified: 2026-08-21T21:08:15.972Z
---

2026-08-22, [[gmarket-ad-report-lock-collision]] 후속으로 대시보드 UX 3종 수정:

1. **실행중 표시 부정확**: 재크롤 버튼은 `views.py GmarketRecrawlView`가 `threading.Thread`로 크롤 함수를 직접 호출(별도 프로세스 아님) → 기존 상태체크는 `ps -eo args`로 `crawl_gmarket_ad_report` 문자열을 찾아 스레드 실행은 절대 못 잡음. `eleven_block_guard.py`에 파일마커(`adreport_busy_info/set_adreport_busy/clear_adreport_busy`, `/tmp/avengers_gmarket_adreport.busy`)를 추가해 해결 — 지마켓 광고제어(`adcontrol_busy`)에 이미 있던 것과 동일 패턴을 ad_report용으로 별도 신설.
2. **강제중지 버튼 신설**: `is_adreport_stop`/`request_adreport_stop`/`clear_adreport_stop`(`/tmp/avengers_gmarket_adreport_stop`) — 크롤러 계정 루프 최상단에서 체크, 대시보드에 "수집 중"일 때만 버튼 노출. `POST /cpc/gmarket/recrawl-stop/`.
3. **광고 0원 계정 오탐**: 광고 미집행(0건)이면 GmarketProductAdCost에 저장할 행이 없어 collected_at이 안 남아 매번 "실패"로 오표시(rejoice444/678/911/tmxkql111/tmxkql222 등 상시 0원 계정 고정 패턴). 크롤러가 계정 처리 완료 시 CrawlerLog(level=info, message='상품별광고비 수집 완료(광고 미집행 포함)')를 남기고, `GmarketCrawlStatusView`가 오늘자 GmarketProductAdCost 존재 OR 오늘자 완료로그 존재 중 하나면 done으로 판정하도록 변경.

**Why:** 사용자가 "재크롤 눌렀는데 실행돼?"를 반복 질문할 정도로 상태표시를 신뢰 못 했음 + 0원계정이 매일 고정적으로 "실패"에 남아 혼란.

**How to apply:** 향후 지마켓 상품별광고비 대시보드에서 "실행중" 오판이나 0원계정 "실패" 재발 시, 이 3개 파일마커/로그 메커니즘부터 확인(`/tmp/avengers_gmarket_adreport.busy`, `/tmp/avengers_gmarket_adreport_stop`, CrawlerLog 'gmarket'+'상품별광고비 수집 완료'). pm2 재시작 시 진행 중이던 재크롤 스레드가 죽는다는 점 주의 — 코드 배포 전 `guard.adreport_busy_info('gmarket')`로 실행 여부 확인 후 재시작 타이밍 잡을 것.

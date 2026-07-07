---
name: project_gmarket_ad_control_bugs_2026-07-07
description: 지마켓 간편/AI광고 제어(ON/OFF) 실전에서 발견·수정한 버그 3종 + 락경합 구조
metadata: 
  node_type: memory
  type: project
  originSessionId: 65854cbc-8aa2-4568-95c3-193c08d99126
---

## 배경
지마켓 광고 ON/OFF가 "16:20 자동 OFF 됐어야 하는데 계속 광고비가 샌다"는 사용자 신고로
실측 조사·수정함(2026-07-07). [[project_coupang_integration]]과 별개 이슈.

## 발견·수정된 버그 3종

1. **로그인 실패 시 재시도 없이 그냥 스킵** (`gmarket_ad_combined_control.py`)
   - dlwodb000이 16:52 로그인 실패 → 아무 후속조치 없이 저녁까지 방치돼 광고비 계속 발생
   - 수정: 로그인 2회 재시도 + 그래도 실패하면 `failed_accounts` 리스트로 로그/CrawlerLog 남김
     (전엔 조용히 사라졌음)

2. **AI광고 그룹 목록 페이지, 고정 3초 대기만 함** (`gmarket_ai_control_crawler.py::_get_group_info`)
   - 그룹 수 많은 공유계정(rejoice234=235,236 그룹, dlwodbs666)이 렌더링 덜 끝난 상태에서
     읽혀 일부 그룹 누락 → 몇 개만 켜진 채로 남음
   - 수정: `WebDriverWait`로 실제 그룹행(`tr[data-groupno]`) 뜰 때까지 대기(최대10초)+여유1.5초

3. **AI ON 재시도 크론의 "오늘 이미 성공했나" 체크가 __date 버그로 무력화** (`run_ai_schedule.py`)
   - `event_time__date=today` 사용 → 프로젝트 전역의 타임존 함정([[feedback_timezone_pitfalls]])과
     동일 문제. 19:38에 이미 성공했는데 20:18 재시도 크론이 그걸 못 알아채고 또 실행함
   - 수정: KST 자정 기준 `make_aware(datetime.combine(...))` 범위비교로 교체, 검증완료

## 구조적 이슈 — 락 경합 (완전해결은 아님)
AI ON 스케줄(19:33)이 지마켓 광고비수집(19시/20시 크론)과 같은 'gmarket' 플랫폼 락을 공유해서
겹치면 30분 대기 후 포기·스킵됨(실측: 2026-07-05 25계정 전체 스킵). 대응책:
- `run_ai_schedule.py`의 `wait_timeout`은 30분(1800s) 유지(너무 길게 하지 말라는 사용자 피드백)
- 대신 **20:18에 재시도 크론 추가**(`cron_ai_on_retry.sh`, crontab 태그 `AD_SCHEDULE_RETRY`,
  요일 0,1,2,3,4) — "오래 기다리기"보다 "안되면 나중에 다시 시도"가 사용자가 원한 방향.

## AI 저녁 ON 스케줄의 의미 (처음엔 버그로 오해했었음)
"AI: ON 월화수목일 19:33"은 **당일 저녁에 켜서 다음날(시작일=내일) 광고를 준비**시키는 정상 설계.
저녁에 ON 기록이 보여도 버그 아님 — 사용자 확인: "오늘 켜야 내일 가동되잖아".

**Why:** 다음에 지마켓 광고제어 관련 이슈 나오면 이 3개 버그부터 재발 여부 확인.
**How to apply:** 광고비 누수 신고 오면 GmarketAiAdHistory/Cpc2History에서 시각대별 ON/OFF
기록 먼저 조회(단, `__date` 필터 쓰지 말고 aware datetime 범위로).

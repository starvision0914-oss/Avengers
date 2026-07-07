---
name: project_lotteon_and_11st_otp_cron
description: 롯데온(lotteon) 플랫폼이 SalesRecord에 이미 존재함을 발견 + 11번가 OTP 매일자동점검 크론 신규등록
metadata: 
  node_type: memory
  type: project
  originSessionId: 65854cbc-8aa2-4568-95c3-193c08d99126
---

## 롯데온 연동 존재 확인 (2026-07-07)
사용자가 "지마켓/옥션 롯데온 11번가 쿠팡 스마트스토어"라고 언급해서 확인해보니, `SalesRecord`
모델에 **`platform='lotteon'` 데이터가 이미 존재**함(예: 7/1~7/7 기간 1건/104,906원). 이전
세션들에서 롯데온 관련 작업을 한 기록/메모리가 전혀 없었음 — 아마 수동 업로드로만 채워지고
있고, 별도 크롤러/자동수집 시스템은 아직 없는 것으로 보임. **추가조사 필요**(크롤러 있는지,
왜 문서화가 안 됐는지).

## 11번가 OTP 일일점검 크론 신규 등록 (2026-07-07)
- 배경: 72개 계정 전부 쿠키만료로 인증팝업 반복 발생 → `verify_11st_fast`로 전체 재인증
  (1시간18분 소요, 72/72 성공)
- 재발방지: 매일 **10:00**에 `cron_11st_otp_check.sh` → `manage.py verify_11st_fast` 자동실행
  등록(크론탭에 `# 11번가 OTP/쿠키 일일점검(10:00)` 태그로 추가)
- `verify_11st_fast`는 쿠키 먼저 체크하고 만료된 것만 실제 OTP 진행하는 방식이라, 평소엔
  이번처럼 72개 전부 걸리는 일은 드물 것으로 예상(1회성 대량발생이었을 가능성).

**Why:** 롯데온은 이후 세션에서 "이것도 있었네" 하고 새로 발견하지 않도록. OTP 크론은 재발한
문제의 재발방지 조치임을 기록.
**How to apply:** 롯데온 관련 작업 요청 오면 먼저 SalesRecord/크롤러 존재여부부터 재확인.
OTP 인증 문제 재발하면 이 크론이 실제 작동 중인지(10시 로그) 먼저 확인.

## 롯데온 대시보드 구축 착수 (2026-07-07, 같은날 후속) — ⚠️ 아래 최신 진행상황은 [[project_lotteon_integration_attempt]] 참고
사용자가 "매출/구매가는 엑셀업로드, 광고비는 셀레니움 크롤링"으로 대시보드 구축 요청했을 때 조사한 내용:
- `apps/sales`의 범용 엑셀업로드(`SalesUploadView._classify()`)에 `'롯데'/'lotte'→'lotteon'` 분류가
  이미 있음 — 위에서 발견한 SalesRecord의 lotteon 데이터가 바로 이 경로로 들어온 것. **매출/구매가는
  기존 범용 업로드로 이미 처리 가능**, 새 업로드 기능 안 만들어도 될 가능성 높음.
- 계정/크롤러는 `apps/coupang`(자체 Account 모델) 패턴을 따라 `apps/lotteon` 신규 앱으로 계획.
  광고비 크롤러는 `crawlers/gmarket_cost_crawler.py` 패턴(Selenium+쿠키재사용+guard락) 재사용 예정,
  `platform='lotteon'`으로 [[project_platform_lock_split]]에 락 경로 사전 확인 완료
  (`avengers_crawl_chrome_lotteon.lock`, 타 플랫폼과 독립).

이 시점엔 계정정보를 아직 못 받은 걸로 착각했으나, **실제로는 같은 날 사용자가 계정 3개를 이미
제공했고 2FA(OTP) 릴레이 시도까지 진행됨** — 자세한 내용/현재 막힌 지점(VNC 전환 제안, 응답대기)은
[[project_lotteon_integration_attempt]] 참고. 이 파일의 코드/URL 계획은 유효하나 진행상황은 그쪽이 최신.

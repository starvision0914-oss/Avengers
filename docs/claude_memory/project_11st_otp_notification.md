---
name: project_11st_otp_notification
description: 11번가 OTP는 RCS/푸시(알림)로 옴 — adb 알림에서 읽어야 함(문자함 X)
metadata: 
  node_type: memory
  type: project
  originSessionId: 8cfc5d0f-21a9-45a7-8307-c0179c4ca099
---

2026-06-09 11번가 로그인 OTP가 **옛날 SMS(content://sms)가 아니라 RCS/푸시 메시지(발신자=11번가, "[Web발신][11번가] 인증번호 [XXXXXX]")** 로 옴. 그래서 문자함에 저장 안 되고, SMS 읽는 smsApp/Redis 파이프라인(`_wait_for_otp_redis`)이 못 잡아 로그인 5분×3회 전부 실패. 카카오톡 아님(카카오 알림 allowNoti=false로 꺼져있음).

**Why:** OTP 전달 방식이 SMS→RCS로 바뀜. 폰엔 분명히 오지만(알림에 뜸) 저장 위치가 달라 기존 SMS 리더가 놓침.

**How to apply:** `crawlers/eleven_crawler.py`에 `_otp_from_adb_notification(since_ms)` + `_wait_for_otp_any()` 추가 — `adb shell dumpsys notification --noredact` 출력에서 `인증번호\s*\[(\d{6})\][^}]*?time=(\d{13})` 정규식으로 추출, since_ms(전송직전-8초) 이후 최신 코드 사용. `_do_login` OTP 대기를 알림우선+SMS보조로 변경. 11번가 전 크롤(광고비/등급/셀러오피스/삭제) 공통. [[feedback_crawling_rule]]

**★USB 독립 업데이트(2026-06-13)**: 실측상 11번가 OTP가 **`[Web발신] [11번가] 인증번호 [XXXXXX]` 일반 SMS로도 와서 smsApp이 네트워크로 서버 DB(ReceivedSmsMessage)에 푸시**됨(USB 없이도 적재됨, 오늘 12:10~ 다수 확인). 그러나 `_wait_for_otp_any`는 adb만 보고, 폴백 `_wait_for_otp_redis`는 신규 Redis 이벤트만 기다려 **adb 대기 180초 중 도착한 OTP를 놓치는 타이밍 구멍** 있었음 → USB 없으면 OTP 실패 위험. **수정**: `_otp_from_db(since_ms)` 신설(ReceivedSmsMessage에서 since_ms 이후 '11번가 인증번호' 6자리 직접 조회) + `_wait_for_otp_any`가 매 루프 adb+DB 둘 다 확인. 검증: DB OTP(331662) USB 없이 추출 성공. → **폰 전원ON+앱실행+WiFi면 USB 없이 11번가 OTP 인증 가능**. adb는 백업/즉시성용. 문자수신 구조 [[project_sms_paths_and_watchdog]].

---
name: project_sms_paths_and_watchdog
description: "문자 수신 2경로(앱 네트워크 푸시=주, adb-USB=백업/OTP)와 adb_watchdog 오경보 수정"
metadata: 
  node_type: memory
  type: project
  originSessionId: fad4d127-1168-451f-87db-42bab5a25f72
---

**문자 수신 경로는 2개, 서로 독립:**
1. **주경로 = smsApp(안드로이드) 네트워크 푸시** — 폰이 문자/RCS/알림을 받으면 앱이 WiFi/네트워크로 서버에 직접 POST → ReceivedSmsMessage 저장 + 텔레그램. **USB와 무관.** 앱 생존은 `SmsDeviceHeartbeat.last_seen_at`(30초 주기)로 확인. 검증: USB 죽은 상태에서도 문자 0.16초만에 수신됨(2026-06-13).
2. **백업경로 = adb-USB 폴러** — `avengers-sms-poller`(PM2)가 `adb shell content query content://sms/inbox`로 5초마다 폴링. **데이터 USB 연결 필요.** 충전전용 케이블이면 `lsusb`에 폰 안 잡힘 → adb 무용 → 폴러가 "adb 오류: no devices" 로그 도배(무해).

**11번가 OTP는 경로 2개**(eleven_crawler `_wait_for_otp_any`): ①`_otp_from_adb_notification`(adb dumpsys, USB필요) ②`_otp_from_db`(ReceivedSmsMessage=앱푸시 SMS, **USB 불필요 폴백**). 11번가 OTP가 [Web발신] SMS로도 와서 DB에 적재되므로 **adb 죽어도 DB폴백으로 OTP 자동 인증됨**(2026-06-20 실증: adb 다운기간에도 풀로그인 933건 OTP없이/DB폴백으로 전부 성공, 로그인 실패 0). 즉 OTP는 adb 의존 아님. 단 RCS/푸시로만 오는 OTP는 adb 필요하니 백업 유지 권장.

**⚠️ last_otp_at 오해 주의**: `CrawlerAccount.last_otp_at`은 "11번가가 마지막으로 OTP를 *요구*한 시각"이지 실패/건강지표 아님. 11번가는 세션/위험도 따라 OTP를 띄울 때만 띄움 → 어떤 계정(rejoice1231)은 06-16 이후 OTP 요구가 안 와서 last_otp_at이 06-16에 멈춰도 로그인은 정상(쿠키갱신·OTP없는 풀로그인). 이 필드로 "OTP 실패" 판단 금지. 건강지표는 cookie_saved_at/로그인성공.

**adb 백업경로 무음장애 사건(2026-06-20)**: 폰이 06-17 모뎀모드(cdc_acm/ttyACM0)로 잘못 인식→06-18 09:31 USB분리→06-19 21:57 재연결됐으나 **adb 데몬이 죽은 채라 `adb devices` 빈값**, sms-poller "no devices" 12,709회+"(0,'')" 루프. 해결=`adb kill-server;start-server`(→R3CM902DCHA device 즉시 온라인)+`pm2 restart avengers-sms-poller`(문자수신 재개). 근본허점=워치독이 앱 하트비트 신선하면 경보 전면 억제→adb백업이 며칠 죽어도 무경보. 개선안: adb죽고 앱정상이면 '백업끊김' 저빈도 알림 분리, poller가 (0,'')/no-device 반복시 self 재기동.

**adb_watchdog.sh 오경보 수정(2026-06-13)**: cron `*/5` 워치독이 adb 죽으면 복구 시도 후 실패 시 "🚨 폰 연결 끊김/OTP 수신 불가" 텔레그램을 **5분마다 도배**하던 문제. 원인=adb만 보고 앱 네트워크 경로(문자 정상수신 중)를 무시. 수정: **하트비트 신선(<600s)이면 경보 억제(로그만), adb·앱 둘다 끊긴 진짜 오프라인일 때만 6시간 1회 경보**(/tmp/adb_watchdog_last_alert 스로틀). 워치독 자체의 adb 자동복구(kill/start-server·reverse·poller재시작)는 유지.

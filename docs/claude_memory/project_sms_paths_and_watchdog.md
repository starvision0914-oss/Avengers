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

**11번가 OTP는 adb 경로 의존**([[project_11st_otp_notification]]): adb dumpsys notification으로 읽음. 그래서 USB 죽으면 쿠키만료 후 풀로그인 OTP가 막힐 위험(평소 쿠키재사용이라 문제 적음). → 안정성 위해 데이터 USB 권장.

**adb_watchdog.sh 오경보 수정(2026-06-13)**: cron `*/5` 워치독이 adb 죽으면 복구 시도 후 실패 시 "🚨 폰 연결 끊김/OTP 수신 불가" 텔레그램을 **5분마다 도배**하던 문제. 원인=adb만 보고 앱 네트워크 경로(문자 정상수신 중)를 무시. 수정: **하트비트 신선(<600s)이면 경보 억제(로그만), adb·앱 둘다 끊긴 진짜 오프라인일 때만 6시간 1회 경보**(/tmp/adb_watchdog_last_alert 스로틀). 워치독 자체의 adb 자동복구(kill/start-server·reverse·poller재시작)는 유지.

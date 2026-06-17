---
name: project_11st_otp_adb
description: 11번가 OTP 로그인은 폰 adb 연결에 의존 — adb 죽으면 OTP 못읽어 0 수집. watchdog로 자동복구
metadata: 
  node_type: memory
  type: project
  originSessionId: 8cfc5d0f-21a9-45a7-8307-c0179c4ca099
---

11번가 크롤러 풀로그인 시 OTP가 필요할 수 있고(대부분 ID/PW만으로 통과, 약 5%만 OTP), OTP 인증번호는 **폰(01058417783)의 SMS를 adb로 읽어** 자동 입력한다(SMS poller: PM2 `avengers-sms-poller`, USB `adb reverse tcp:8010`).

**핵심 함정(2026-06-08 실제 장애):** adb 데몬이 죽으면 → SMS 인증번호 못 읽음 → OTP 로그인 실패 → (게다가 죽은쿠키 URL검증 버그와 겹쳐) **수집이 조용히 0건이 됨**. 6/6 저녁~6/8 광고비가 그래서 비었음. 복구는 `adb kill-server && adb start-server && adb reverse tcp:8010 tcp:8010` + `pm2 restart avengers-sms-poller`.

**대책(적용됨):** `Avengers/backend/scripts/adb_watchdog.sh` (cron `*/5`) — adb 연결 죽으면 자동 복구, 물리적으로 폰이 빠져 복구 불가하면 텔레그램 경보. `adb devices`에 기기 안 보이면 폰 USB 물리 연결부터 확인.

관련: [[project_11st_transient_fails]] (죽은쿠키 URL검증 버그·매시간 API 구조), [[project_server_ip]]

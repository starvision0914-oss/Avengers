---
name: project_phone_wireless_adb_wifi
description: "회사폰 USB adb 의존 탈피 시도 — 같은 WiFi+무선adb로 성공했으나 불안정, 정식 무선디버깅 미완료"
metadata: 
  node_type: memory
  type: project
  originSessionId: c8272f73-4610-4a02-b107-7e70ef950e0e
---

11번가 OTP 인증이 USB(adb reverse) 의존이라 폰이 USB에서 빠지면 인증 불가한 문제를 해결하려 시도(2026-07-06~07).

**시도한 경로**: ai100 원본 설계는 "사무실 WiFi 같은 대역 또는 VPN"이 정답([[reference_ai100]] SMS_MODULE.md 참조). Tailscale VPN을 먼저 시도했으나, **폰의 기본 브라우저가 "네이트"로 설정되어 있어서** Tailscale 로그인 시 구글 OAuth가 계속 `403 disallowed_useragent`로 막힘(임베디드 웹뷰로 오인). 폰 기본 브라우저를 Chrome으로 변경(설정→기본 앱→브라우저 앱)한 뒤에야 정상 통과 확인. 이후 사용자가 더 간단한 방법(같은 WiFi 직접 연결)을 선택.

**최종 방식**: 폰을 서버(192.168.45.100)와 같은 공유기 와이파이(SK_WiFiGIGAAC0C_5G, 게이트웨이 192.168.45.1, MAC이 게이트웨이와 근접해서 식별)에 연결 → `adb tcpip 5555` + `adb connect <폰IP>:5555`로 USB 없이 adb 성공(알림읽기·배터리조회 등 실사용 기능까지 확인).

**Why 아직 미완**: `adb tcpip` 모드는 폰 재부팅/장시간 유휴 시 자동으로 풀림(세션 중 여러 번 끊김 관찰). 근본 해결책은 안드로이드 정식 "무선 디버깅"(개발자옵션, `adb_wifi_enabled` 설정) — 이건 페어링 기반이라 훨씬 안정적인데, **보안상 `settings put global adb_wifi_enabled 1`로 자동 설정이 안 되고 화면에서 직접 토글해야 함**(우회 시도 금지 — 정당한 보안장치). 사용자에게 개발자옵션 화면 열어주고 "무선 디버깅" 직접 켜달라고 요청한 상태에서 다른 주제로 넘어감, 미완료.

**부수 발견**: 폰에 `com.google.chromeremotedesktop`(크롬 원격데스크톱)이 설치되어 있어 은행 앱이 "원격제어 앱 감지"로 거래를 막음 → 삭제로 해결(2026-07-07). Tailscale은 최종적으로 안 씀(설치는 남아있음, 필요시 제거 요청 대기중).

**How to apply**: 다음 세션에서 폰 USB 문제 재발 시, adb_watchdog.sh는 USB 재연결만 시도하고 무선 재연결 로직이 없음(개선 필요, 미완료). 우선 `adb connect <폰IP>:5555` 재시도해보고, 안 되면 "무선 디버깅" 토글 상태부터 확인.

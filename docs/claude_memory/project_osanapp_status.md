---
name: project-osanapp-status
description: 오산 이야기(OsanApp) React Native/Expo 앱 진행상황과 실기기 테스트 이슈
metadata: 
  node_type: memory
  type: project
  originSessionId: 1dcc06b3-8303-4b57-97cd-c4503b0e0701
---

/home/rejoice888/OsanApp — 오산시 소개 앱(Expo Router, SDK 57). 관광지 5곳·맛집 3곳·행사 2건 실데이터 채움 완료(2026-07-10), git 첫 커밋 완료.

**실기기 테스트 막힘(2026-07-10 기준 미해결)**: 서버(192.168.45.100)에 ufw 방화벽이 켜져 있고 sudo 비밀번호를 이 세션(비대화형)에서 입력할 수 없어 LAN 직접 연결(exp://192.168.45.100:8081) 불가 → `npx expo start --tunnel`(ngrok)로 우회, 터널 주소는 세션마다 바뀜(예: qillltu-anonymous-8081.exp.direct). 게다가 플레이스토어 Expo Go가 아직 SDK 57을 지원 안 함(2026년 5월부터 앱스토어 심사 밀림, [[feedback_formal_speech]] 세션 시점 기준 최신 상황 재확인 필요) → SDK 57 전용 APK(https://github.com/expo/expo-go-releases/releases)를 별도 설치해야 함. 사용자가 설치했다는 APK가 실제로 깔렸는지/기존 앱과 충돌했는지 불확실한 상태로 세션 종료.

**How to apply**: 다음 세션에서 이어간다면 먼저 `ps aux | grep expo`로 서버 살아있는지, ngrok 터널 주소 최신값을 다시 확인할 것. 방화벽을 영구 해결하려면 사용자가 직접 VNC/SSH 터미널에서 `sudo ufw allow from 192.168.45.0/24 to any port 8081 proto tcp`를 실행해야 함(이 프로젝트의 비대화형 세션에서는 sudo 실행 불가, [[feedback_sudo_noninteractive]]).

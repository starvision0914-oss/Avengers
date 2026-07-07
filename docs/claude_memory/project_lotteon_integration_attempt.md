---
name: project_lotteon_integration_attempt
description: "롯데온 신규 플랫폼 연동 시도 — 2FA(OTP) 릴레이 실패로 미완료, VNC 방식으로 이어가야 함"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3b74a53b-7c7e-4165-8a60-ec6720571afd
---

## 배경 (2026-07-07)
사용자가 롯데온 계정 3개(신규) 제공하며 구축 요청:
- rejoice234 / @dlwodbs00 / 스타피씨에스 롯데온
- tmxkql111 / @dlwodbs9 / 스타고급상점
- tmxkql222 / @dlwodbs9 / 스타드림딜

이전까지 이 프로젝트에 롯데온 연동 자체가 전혀 없었음(계정모델·크롤러·대시보드 전부 없음). apps/sales(수기 매출업로드)에서 "롯데온"을 라벨로만 인식하는 수준(테스트성 14건뿐).

## 확인된 정보
- 판매자센터: `https://store.lotteon.com` (아이디/비밀번호 로그인)
- 오픈API 센터: `https://api.lotteon.com/apiGuide/` — 판매자센터 로그인 후 [판매자 정보>OpenAPI관리]에서 키 발급(1년 유효). 광고주센터: `https://ad.lotteon.com/common/login`
- rejoice234로 로그인 테스트 → ID/PW는 정상 통과하지만 **2단계 인증(SMS OTP, 010-****-9019)**이 걸림. 이 번호는 기존 자동문자수신폰(01058417783)과 다른 번호라 자동화 불가.

## 실패한 접근 & 이유
- 채팅으로 사용자에게 OTP 코드를 받아 대신 입력하는 방식 **3회 연속 실패** — 인증코드 유효시간이 3분인데 채팅 왕복(질문→응답→스크립트 실행) 지연이 이를 초과. 추가로 스크립트 버그(WebSquare 자동생성 ID `mf_wq_uuid_109`가 페이지 상태마다 다른 버튼을 가리켜 재시도 시 로그인폼의 "로그인" 버튼을 잘못 클릭)도 한 번 겹침.
- 코드 재입력 시도마다 세션이 로그인폼으로 리셋됨 — persistent user_data_dir(`/tmp/lotteon_profiles/rejoice234`)로 쿠키는 유지되지만 3분 창을 못 맞추면 그냥 초기화면.

## 다음 시도 방법 (미실행)
**VNC 직접 조작으로 전환 제안함**: 서버에 x11vnc가 이미 떠 있음(포트 5905, 비밀번호 없음, `-display :99`). Selenium 크롤러도 같은 DISPLAY=:99를 쓰므로, 사용자가 VNC 뷰어로 `192.168.45.100:5905` 접속하면 자동화 중인 크롬 창을 직접 보고 SMS 코드를 그 자리에서 입력할 수 있음 — 채팅 릴레이보다 훨씬 빠름. **사용자 응답 대기 중, 진행 안 됨.**

**Why:** 롯데온은 판매자센터 로그인과 광고센터/오픈API 발급이 모두 동일 계정의 2FA를 거쳐야 해서, 자동화하려면 최초 1회는 반드시 사람이 OTP를 입력해 세션(또는 API 키)을 확보해야 함.
**How to apply:** 다음 세션에서 롯데온 얘기 나오면 VNC 접속 여부부터 확인. 성공하면 이후엔 Open API(api.lotteon.com) 방식으로 전환하는 게 Selenium 반복 로그인보다 안정적(쿠팡 사례와 동일 패턴, [[project_coupang_integration]] 참고).

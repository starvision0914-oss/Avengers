---
name: project_lotteon_login_success
description: "롯데온 rejoice234 로그인+2FA 자동화 성공(2026-07-07) — WebSquare는 ActionChains 클릭 필요, 스크립트 완성"
metadata: 
  node_type: memory
  type: project
  originSessionId: c8272f73-4610-4a02-b107-7e70ef950e0e
---

[[project_lotteon_integration_attempt]]에서 3회 실패했던 롯데온 2FA 로그인을 자동화 스크립트로 해결.

**최종 성공 스크립트**: `scripts/_lotteon_login_otp.py <login_id> <password>`
- `create_driver(user_data_dir=f'/tmp/lotteon_profiles/{login_id}', kill_existing=False)`로 계정별 프로필 분리(쿠키 재사용 가능)
- 로그인폼: `input[placeholder="사용자ID"]`, `input[type="password"]`, `.btn_login` — 표준 CSS로 잘 먹힘
- **2FA "휴대폰" 인증박스는 `#mf_phoneType` (실측 id)인데, 일반 Selenium `.click()`으로는 SMS 발송이 트리거 안 됨** —
  WebSquare(롯데 계열사 공통 프레임워크로 보임, KTP/한국거래소 등도 씀)가 커스텀 마우스이벤트 바인딩이라
  합성 클릭 이벤트를 무시함. **`ActionChains(driver).move_to_element(el).pause(0.3).click(el).perform()`로
  실제 마우스 이동+클릭을 흉내내야 정상 작동**(확인: 클릭 후 매번 새 SMS 코드 발급됨).
- 인증코드 입력: `input[placeholder*="코드"]`, 제출은 재사용 `.btn_login`.
- **채팅relay 방식도 성공**: 코드를 `/tmp/lotteon_otp_code.txt`에 쓰면 스크립트가 0.5초 간격으로 폴링해서
  즉시 입력 — 3분 유효시간 문제를 해결(기존 실패 원인이었던 지연 제거). VNC 없이도 가능해짐.
- 로그인 성공 확인: URL이 `login_SO.wsp` → `index_SO.wsp`로 바뀜. 판매자센터 홈 진입(스토어명 "스타피씨에스", 셀러ID LO10163804).

**부수 발견**: 010-****-9019 폰(별도 실물 기기, R59M60EQKXE)을 USB로 연결해 `adb shell dumpsys notification --noredact`로
SMS 내용까지 읽을 수 있음 — `content query --uri content://sms/inbox`는 이 기기에서 권한 문제로 실패했지만
notification dump의 `android.text`/`tickerText` 필드에서 문자 내용 그대로 추출 가능. 완전 자동화(폰 알림 폴링)로
발전시킬 수 있는 여지 있음(아직 수동 relay만 구현).

**Why**: 3번 실패했던 원인(3분 타임아웃)을 근본 해결 — 파일폴링 0.5초 간격이면 채팅으로 코드 전달해도 충분히 빠름.
**How to apply**: 프로필 디렉토리(`/tmp/lotteon_profiles/{id}`)에 쿠키 저장되므로 재실행시 이미 로그인된 상태면 바로 스킵됨.

**2026-07-07 완료**: 3계정(rejoice234/tmxkql111/tmxkql222) 전부 같은 방식으로 로그인 성공. 다음 단계는
각 계정 판매자센터의 "OpenAPI관리" 메뉴(사이드바 즐겨찾기에 보임)에서 API키 발급 → Selenium 반복로그인 대신
쿠팡처럼 API 기반 전환, 그리고 apps/lotteon 신규 앱(계정모델+대시보드) 실제 코드 작성 착수 필요(계획은
[[project_lotteon_and_11st_otp_cron]] 참고, 아직 미작성).

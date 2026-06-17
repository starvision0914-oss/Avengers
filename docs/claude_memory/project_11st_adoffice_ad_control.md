---
name: project_11st_adoffice_ad_control
description: "11번가 광고 ON/OFF·입찰가 자동화(adoffice 광고센터) — 17시 자동중지·입찰조정의 열쇠, Avengers 통합 대기중"
metadata: 
  node_type: memory
  type: project
  originSessionId: fad4d127-1168-451f-87db-42bab5a25f72
---

사용자가 **11번가 광고 ON/OFF + 입찰가 일괄변경 GUI 도구**(tkinter+Selenium, 단독 .py)를 갖고 있음. 이게 그동안 막혔던 **11번가 광고 자동제어**의 핵심 자산. (지금까지 Avengers엔 11번가 광고 ON/OFF가 미구현 — 지마켓만 있었음. 그래서 사용자가 "17시 자동중지 설정했는데 안 됨" 했던 것)

**도구가 알려준 핵심 사실:**
- 광고센터 = **`adoffice.11st.co.kr`** (셀러오피스 `soffice.11st.co.kr`와 별도 도메인, SSO 연결). 로그인: soffice/view/intro → loginName/passWord → submit → adoffice 진입.
- React SPA(`#root`). 플로우: 좌측 nav 광고관리 → 캠페인/그룹/소재 테이블 → 헤더 전체체크박스 → **선택ON/선택OFF 버튼** 또는 **입찰가 일괄변경**(버튼→`#ms-all-check` 모달→input→저장).
- 입찰가 기본 420원, 다계정(config.ini User 섹션).

**도구의 치명 결함(그대로 쓰면 안 됨):** ①OTP 처리 없음 ②쿠키 미재사용(매번 풀로그인→OTP·차단 위험) ③preflight 락 없음(동시크롤 IP차단) ④절대 XPath(`//*[@id="root"]/div/div[2]/main/...`)라 UI 변경에 취약 ⑤입찰 input 셀렉터 모호(`input[type=text]:not([readonly])` 첫번째).

**Avengers 통합 설계(합의됨):** 로직(adoffice 도메인+셀렉터)만 이식. 로그인→`_do_login`(쿠키재사용+adb OTP), 동시성→`eleven_block_guard.preflight`, 절대XPath→텍스트/속성 셀렉터, 실행→management command + 대시보드 버튼 + **cron(17시 자동OFF)**, 비번→`password_enc`. 이러면 17시 자동중지 + 입찰 자동조정(무전환↓/전환↑) 둘 다 해결.

**진행상태(2026-06-13):** 사용자가 "나중에 찾을테니 기억해두라" → **보류**. 읽기전용 셀렉터 검증 진단 `backend/crawlers/diag_adoffice.py` **작성완료·미실행**. 도구 원본 코드 사본: `/home/rejoice888/PUBLIC/11st_adoffice_onoff_tool.py`. 재개 시 diag_adoffice.py부터 실행해 adoffice 셀렉터 유효성 확인.

관련: [[project_11st_ip_block_prevention]] [[project_11st_otp_notification]] [[project_11st_cookie_intro_loop]] [[project_11st_perma_banned]]. 영구정지 계정(rejoice43 등)은 adoffice 접속불가라 제외.

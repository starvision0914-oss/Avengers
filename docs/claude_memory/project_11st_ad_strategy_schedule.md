---
name: project_11st_ad_strategy_schedule
description: 11번가 광고그룹 노출스케줄 전략설정 기능(/ad-settings) 구축 — 캠페인 실시간조회 필수·DOM미검증
metadata: 
  node_type: memory
  type: project
  originSessionId: e76d08ca-b676-492c-8ef3-735797020404
---

/ad-settings 에 "11번가 전략설정" 탭 신설(2026-06-18). 계정선택→캠페인 불러오기·선택→시간/요일 설정→광고그룹('전체-') 노출스케줄 일괄적용(지정 시간·요일만 ON 나머지 OFF). 사용자 GUI 도구(adoffice.11st.co.kr) 로직 이식.

- 크롤러: `crawlers/eleven_ad_strategy.py` — run_strategy()(전략적용)·list_campaigns()(캠페인조회). 로그인은 eleven_crawler._do_login(OTP/쿠키) 재사용, guard.preflight(platform='11st') 전역락, 기본 드라이런(execute=False면 바꿀칸수만 로그·저장안함).
- API: /cpc/eleven-ad-strategy/control/(POST 적용) · /campaigns/(GET=DB즉시, POST=실시간조회 백그라운드) · /logs/(폴링). 진행로그=St11AdStrategyLog(run_id, status START/INFO/CAMP/APPLIED/SKIP/ERROR/DONE).
- **St11AdofficeCampaign 테이블 0건** → 캠페인 이름은 DB에 없어 **광고센터 실시간 로그인 조회 필수**(list_campaigns가 조회후 최소 upsert). 캠페인명은 계정공통이라 **대표계정 1개만 로그인**(동시로그인=IP차단 위험, [[project_11st_ip_block_prevention]]).
- 스케줄 표 매핑: 첫 td=시(N시), 이후 td 7개 idx 1=월…7=일. want_on=(요일∈선택)&(on_start≤시≤on_end). class에 'on'/'off' 포함여부로 토글. 기본 평일(1-5) 8~16시.
- ✅ **라이브 검증된 실제 셀렉터(2026-06-18 rejoice888 드라이런)**:
  - 상세설정 라디오 = `//label[contains(.,'상세')]` (원본 #radio-schedule-setting은 안 맞음)
  - 스케줄 표 = 평범한 `//table` (MuiTable-root 아님). 첫 td=시(N시), 이후 7칸 1=월..7=일, class에 on/off. 평일8~16 → 바꿀칸 123(=168−45) 정상 계산.
  - 페이지크기 100 = **MUI Select(div.MuiSelect-select, 현재값 '30개')** — JS click 무효, **mousedown 이벤트라야 열림**. 옵션 li 텍스트에 ​ 포함(normalize-space 매칭 안됨→contains '100' 사용). 그룹 목록 페이지는 기본이 이미 100개.
  - 로그인 ~61s(OTP). 그룹 진입 후 set_page_size_100 호출. --max-groups N 으로 진단(1개만).
- ✅✅ **실제적용 end-to-end 검증완료(2026-06-18 rejoice888 자동_캠페인 전체-1)**:
  - ON칸 = `class` 정확히 `'on'`(배경 rgb(11,131,230) 파랑), OFF=그외. 'on' substring판정 금지(정확일치).
  - **칸 토글은 마우스이벤트(mousedown+mouseup+click) 디스패치라야 먹힘**(JS click·일반click 무효 — 드래그형 그리드). 토글후 재검증 잔여 0 확인.
  - **저장 버튼 = "그룹 수정"** (저장/적용 아님!). `//button[normalize-space()='그룹 수정']`.
  - 검증법: 적용후 같은 그룹 드라이런 재실행 → '바꿀 칸 0개'면 영속 성공(실측 0칸 확인).
  - 평일8~16 적용시 바꿀칸 123(=168−45). 전체-1 한 그룹은 실제로 평일8~16만 ON으로 변경·저장됨(라이브).
- **남은 것: rejoice888 나머지 50개 그룹·타 계정은 미적용.** 동시접속 금지(guard 11st 전역락이 스냅샷/광고비 크롤과 직렬화). [[project_11st_adoffice_ad_control]] [[project_11st_ip_block_prevention]]

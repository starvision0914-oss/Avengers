---
name: project_11st_tmxkzhfldk8_crash
description: 11번가 계정 tmxkzhfldk8(스타코3)은 Selenium 로그인/인증 시 프로세스 크래시 유발 — 제외
metadata: 
  node_type: memory
  type: project
  originSessionId: 2652a85c-f4de-41b6-8478-ea5e69ec25ed
---

11번가 계정 **tmxkzhfldk8 (스타코3)** 은 Selenium 로그인/인증 처리 시 **프로세스가 SIGTERM(exit 144)으로 죽는 문제** 유발. 2026-06-14 verify_11st_logins 전체 실행이 이 계정 [27/71] 시작 직후 통째로 종료됨(앞 26계정은 정상 OTP 성공).

기존에도 `scripts/orch_11st_status.sh`가 이 계정을 **명시적으로 제외**(`if a.login_id!='tmxkzhfldk8'`)하고 있었음 — 알려진 문제 계정.

**정정(2026-06-14)**: tmxkzhfldk8을 **단독 실행하니 정상 인증 성공(66초)**. 즉 계정 자체 문제가 아니라, **26계정 연속 실행 후 누적(크롬/리소스/좀비) 문제로 27번째에서 SIGTERM** 난 것으로 보임(그 계정 차례가 우연히 겹침). 결국 전체 71계정 인증 성공(1차26+재개44+단독1, 실패0).

**대응**: 장시간 연속 Selenium 일괄작업은 ~25계정쯤에서 죽을 수 있음 → **배치를 나눠 돌리면 안전**(재개 시 미완료분만 --only). 죽으면 정리(좀비chrome/락) 후 남은 계정 재개. tmxkzhfldk8은 단독으론 정상. 관련 [[project_crawler_zombie_pc]] [[feedback_crawling_rule]]

---
name: project_osan_homepage
description: 오산 지역정보+커뮤니티+쇼핑몰+블로그 통합 홈페이지(Avengers와 완전 독립). 서버/DB/구조/현황
metadata: 
  node_type: memory
  type: project
  originSessionId: 22f4c8ff-2f78-4400-9e88-27bf11b821dd
---

Avengers와 완전히 독립된 신규 워드프레스 사이트를 구축·운영 중. "오산" 지역 소개 홈페이지로 방향을 잡음.

**why:** 사용자가 커뮤니티+쇼핑몰+블로그(자동발행)+애드센스가 있는 홈페이지를 요청. 이후 "오산을 소개하는 홈페이지"로 구체화(소개/가볼만한곳/아파트정보 등).

**구조(2026-07-23 갱신 — 오라클 이전 완료):**
- **실서버는 이제 오라클 클라우드**(193.123.163.185, AMD E2.1.Micro 1GB) — 192.168.45.100(로컬)은 안전장치로만 유지, 더는 라이브 아님
- 접속: `ssh -i ~/.ssh/oracle_wp ubuntu@193.123.163.185`, 워드프레스 루트 `/var/www/osanguy`, DB `osan_wp`/`osan_wp_user`
- 도메인 osanguy.com 정상 연결 + SSL 발급 완료(Let's Encrypt, 2026-10-20 만료, 자동갱신). Dynadot API 토큰(`ea33be7fbb6f071685be8bde0a0f47fb`)으로 DNS 관리 — 단 유동IP 자동갱신 크론은 이전 시 제거함(고정IP라 불필요, 되살리면 안 됨)
- WP_CACHE 관련 상수(`WP_CACHE`, `WPCACHEHOME`)가 새 서버 wp-config.php에 누락되기 쉬움 — 캐시 안 먹히면 이 두 상수부터 확인
- wp-content 등 쓰기 필요 디렉토리는 `chmod g+w` 되어 있어야 함(복원 직후 기본 755라 www-data 쓰기 불가했던 적 있음)
- 자식테마 `astra-child`: 광고슬롯 3곳(wp_head 훅 방식) + 애드센스 연결 스크립트(ca-pub-7165751541433709) 삽입 완료, ads.txt도 배치됨. 애드센스는 신청만 하고 심사 대기 중(2026-07-23 기준)
- 구글서치콘솔/네이버서치어드바이저 등록·인증(meta 태그, functions.php wp_head 훅) + 사이트맵 제출 완료
- 관리자: `admin` / `@dlwodbs0` (DB 그대로 이전되어 동일)
- ARM(4코어/24GB) Always Free는 반복 재시도(150회+)해도 "Out of host capacity"로 실패 지속 — 되면 지금 AMD 서버에서 한번 더 이전 예정, 급하지 않음
- 관련: [[project_highcpc_content_batch]] (애드센스 고단가 콘텐츠 배치 작성 진행 중)

**현재 상태(2026-07-10 기준, 콘텐츠 규모는 계속 증가 중):**
- 블로그 글 다수 발행, 카테고리: 생활정보=20, 가성비·비교=19, 문제해결=21, 부업·수익화=18, 트렌드·추천=22, 경제뉴스=24, 해외주식=25, 핫이슈=26
- RankMath SEO, 사이트맵/robots.txt 정상. WP Super Cache 등 필수 플러그인 설치됨
- 이미지 정책: 구글 이미지 무단 사용 금지(저작권 위험), **위키미디어 커먼즈(CC BY-SA 등 라이선스 명시된 것만)** 사용 + 출처/저자 표기

**how to apply:** 이 사이트 관련 후속 요청 시 항상 Avengers와 무관하게 독립적으로 작업, **모든 파일 수정·글쓰기는 이제 오라클 서버(193.123.163.185) 기준**으로 진행(로컬 192.168.45.100 아님). 이미지 추가 시 반드시 라이선스 확인 후 출처 표기.

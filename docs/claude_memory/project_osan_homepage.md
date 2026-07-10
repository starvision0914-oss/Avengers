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

**구조:**
- 서버: 192.168.45.100 (Avengers와 같은 물리서버지만 완전 별개)
- 워드프레스: `/home/rejoice888/homepage`, DB는 Avengers `Avengers` DB에 `wp_` 접두사로 저장(신규DB 생성권한 없어 이 방식 택함)
- nginx 포트 80(default_server), 자식테마 `astra-child`(광고슬롯 3곳 준비, 애드센스 승인 후 코드만 넣으면 전체 적용)
- 관리자: `admin` / `@dlwodbs0`
- 그누보드6 비교용 별도 설치: `/home/rejoice888/gnuboard6`, 포트 8021(nginx 프록시), DB `gnuboard6_db`, 관리자 동일 계정/비번

**현재 상태(2026-07-10 기준):**
- 블로그 글 208개 발행 (부업39/가성비44/문제해결40/생활정보35/트렌드추천50), 전부 내부링크(관련글 3개) 적용
- 카테고리 5개로 구조화. RankMath SEO, 사이트맵/robots.txt 정상
- 필수 플러그인 설치: Limit Login Attempts Reloaded, UpdraftPlus, WP Super Cache, EWWW Image Optimizer, Cookie Notice (전부 무료판으로 충분)
- 사이트 언어 en_US → ko_KR 전환 완료
- 홈페이지를 "오산, 살기 좋은 도시"로 리브랜딩: 오산소개/가볼만한곳/아파트정보 페이지 신설 + 공지사항 게시판에 소개글 10개
- 이미지 정책: 구글 이미지 무단 사용 금지(저작권 위험), **위키미디어 커먼즈(CC BY-SA 등 라이선스 명시된 것만)** 사용 + 출처/저자 표기. 오산 관련 확보한 소스: File:독산성과세마대지-1~9.jpg(작가 Korearoadtour), File:Osan_city.jpg(작가 궐동요마), Category:Mulhyanggi_Arboretum 내 2025_Osan_Jjw_2.jpg 등(작가 Jjw) — 전부 CC BY-SA 4.0, 첨부 시 출처 링크 필수
- 도메인: 아직 미구매 (starvison.co.kr 등 후보만 논의, "나중에" 보류 중) → 애드센스/외부공개 전부 이 도메인 구매가 관문

**how to apply:** 이 사이트 관련 후속 요청 시 항상 Avengers와 무관하게 독립적으로 작업. 이미지 추가 시 반드시 라이선스 확인 후 출처 표기. [[project_gmarket_captcha_login]] 같은 크롤러 계정과 무관한 완전 별도 프로젝트임을 헷갈리지 말 것.

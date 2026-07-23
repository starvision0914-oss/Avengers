---
name: project-highcpc-content-batch
description: "고단가(부동산/건강/금융/법률) 키워드 대량 콘텐츠 작성 진행 상황 — 계속하려면 \"이어서 써줘\"라고만 하면 됨"
metadata: 
  node_type: memory
  type: project
  originSessionId: 16802694-722b-486c-9761-fd75804cf7a9
---

사용자가 오라클 서버로 이전한 osanguy.com에 애드센스 수익 최적화를 위해, 대량 키워드 목록(9,140개, 원본은 세션 transcript에서 추출)에서 고단가 카테고리(부동산/건강/금융/법률)만 필터링해 순서대로 정보성 글을 작성 중.

**진행 상황(2026-07-23 기준)**:
- 건강·금융·법률 11건: 완료 (아스퍼거증후군, A형간염, 교모세포종, 척수암, HIV, 에이즈, 음성여성화수술, KODEX200선물인버스2X, 애큐온저축은행, 얼라인파트너스자산운용, 헌법재판소장)
- 부동산 아파트 단지명: 98개 중 20개 완료, 78개 남음

**남은 목록 위치**: `/home/rejoice888/homepage/scripts/highcpc_realestate_progress.txt` — TODO/DONE 태그가 붙은 탭 구분 목록. "TODO"만 순서대로 이어서 처리하면 됨.

**계속하는 방법**: 사용자가 "이어서 써줘" / "계속해줘"라고만 말하면, 이 파일을 읽어 다음 TODO 항목부터 웹서치→작성→발행을 이어가면 됨. 별도 설명 불필요.

**작업 워크플로**:
- 사이트는 오라클 서버(193.123.163.185)로 이전 완료, SSH 키 `~/.ssh/oracle_wp`로 접속, `/var/www/osanguy`가 워드프레스 루트
- 헬퍼 함수는 서버의 `~/hotissue_helper.php`(이미지 생성) + `~/highcpc_helper_fn.php`(publish_info_post, 표+FAQ+요약+참고문헌 템플릿)에 있음 — 로컬에서 새 batch php 작성 후 scp로 업로드, `wp eval-file`로 발행
- 카테고리: 건강/부동산=생활정보(20), 금융=경제뉴스(24), 정치/기관=핫이슈(26)
- **1,500자 이상 필수** — 초안은 보통 1,000~1,200자로 짧게 나오므로 topup 스크립트로 문단 추가해 채워야 함(보통 2~4라운드 필요)
- 각 글은 wp_strip_all_tags 기준 1,500자↑, 키워드 5회 이상 언급, 대표이미지(GD 그라디언트) 필수

[[project_osan_homepage]]

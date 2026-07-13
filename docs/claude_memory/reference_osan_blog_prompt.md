---
name: reference_osan_blog_prompt
description: 오산 홈페이지 워드프레스 블로그 글 작성 프롬프트(시스템+요청) 위치
metadata: 
  node_type: memory
  type: reference
  originSessionId: dfbbf0b2-5cdd-4ddb-bc58-743ed7bf3711
---

오산 홈페이지([[project_osan_homepage]]) 블로그 글 자동생성에 쓰는 프롬프트는 코드에 하드코딩되어 있음 — 별도 프롬프트 파일이 아니라 `/home/rejoice888/homepage/scripts/content_gen.py`에 있음.

- `BLOG_SYSTEM_PROMPT` (파일 11~39행): 네이버 C-Rank/D.I.A.·구글 E-E-A-T·애드센스 승인 4대기준을 반영한 시스템 프롬프트. 분량 2200~3000자, 소제목 5개+, 1인칭 경험담 3회+, 이모지 금지 등 세부 규칙 포함.
- `generate_post()` 내부 요청 프롬프트 (67~82행): 키워드/카테고리를 채워 TITLE/META/본문/TAGS 형식으로 요청.
- 모델: `claude-sonnet-4-6`, API 직접 호출(urllib, ANTHROPIC_API_KEY 환경변수).
- 관련 스크립트: `topics.py`(주제 목록), `auto_publish.py`(발행 자동화).

**how to apply**: "워드프레스 글쓰던 프롬프트 불러와줘" 같은 요청 시 이 파일을 바로 Read해서 보여주면 됨. [[project_osan_blog_expansion_status]](콘텐츠 보강 작업)와는 별개 — 그쪽은 기존 글 분량 늘리기, 이건 신규 글 생성 프롬프트.

관련: [[project_osan_homepage]], [[project_osan_blog_expansion_status]], [[project_osan_kospi_news_series]]

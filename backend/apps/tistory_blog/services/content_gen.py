"""Gemini API를 이용한 티스토리 글 생성 — 워드프레스/티스토리 스타일 SEO 포스팅.
네이버 블로그(apps/naver_blog/services/gemini.py)와 같은 API 키(NaverBlogSetting.gemini_api_key,
없으면 GEMINI_API_KEY 환경변수)와 호출 방식을 재사용하되, 구조는 구글 검색 상위노출에 맞춘
명확한 소제목(H2) 구조 + 클릭을 유도하는 제목/도입부로 다르게 구성한다."""
import json
import re
import urllib.request
import urllib.error
import os

GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent'

TISTORY_PROMPT_TEMPLATE = """당신은 티스토리(구글 검색 유입 중심) 블로그 전문 작가입니다. 워드프레스식 SEO 포스팅처럼
명확한 소제목 구조와 스캔하기 쉬운 문단으로 작성합니다.

검색 키워드: {keyword}
카테고리: {category}
{context_line}

아래 규칙으로 포스팅을 작성하세요:
- 글자 수: 1800~2500자 (공백 포함)
- 제목: 검색 키워드를 포함하면서도 클릭을 유도하는 문구(숫자, 궁금증 유발, 구체적 효익 제시 등)를 넣을 것.
  단, 낚시성 과장(사실과 다른 결과 암시)은 금지 — 클릭 후 실망하지 않을 제목이어야 함
- 도입부(2~3문장): 이 글을 읽으면 무엇을 얻는지 바로 알려주는 요약형 도입(검색엔진 스니펫 노출 고려)
- 본문 구성: '## 소제목'으로 3~5개 섹션 구분(각 섹션 200~400자). 소제목 자체도 검색 키워드나 사용자 질문형으로 작성
- 키워드는 제목, 도입부, 최소 2개 이상의 소제목, 본문 전체에 자연스럽게 6~8회 포함(키워드 스터핑 금지)
- 실제로 겪지 않은 개인 경험이나 후기를 지어내지 말 것. 추가 맥락에 실제 경험이 주어졌으면 그것만 반영하고, 없으면 사실 정보 위주로 작성
- 비교/정리가 필요한 부분은 마크다운 표(| 기호) 대신 소제목+목록으로 풀어서 정리
- 문단은 2~3문장마다 줄바꿈해 가독성 확보
- 본문 중간(전체 분량의 60~70% 지점)에 다음 행동을 유도하는 짧은 문장 1개 삽입(실제 링크는 넣지 말고 유도 문구만)
- 마지막 섹션은 핵심 요약 + 댓글/공유를 유도하는 마무리
- 본문 전체에 별표(*) 기호와 이모지 사용 금지
- 출처가 불확실하거나 변동성이 큰 수치는 단정적으로 쓰지 말고 참고 수준으로 표현
{style_note}

형식 (반드시 지킬 것):
TITLE: [제목]
---
[본문]
---
TAGS: [태그1,태그2,태그3,태그4,태그5]"""


def _get_style_prompt():
    from apps.naver_blog.models import NaverBlogSetting
    try:
        s = NaverBlogSetting.objects.first()
        if s and s.style_prompt.strip():
            return '추가 스타일 지침(사용자 설정):\n' + s.style_prompt.strip()
    except Exception:
        pass
    return ''


def _get_api_key():
    """네이버 블로그와 같은 Gemini 키를 공유(NaverBlogSetting에 저장된 키, 없으면 환경변수)."""
    from apps.naver_blog.models import NaverBlogSetting
    try:
        s = NaverBlogSetting.objects.first()
        if s and s.gemini_api_key:
            return s.gemini_api_key
    except Exception:
        pass
    return os.environ.get('GEMINI_API_KEY', '')


def generate_post(keyword: str, category: str = '', extra_context: str = '') -> dict:
    """반환: {title, content, tags}"""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError('Gemini API 키 없음. 네이버 블로그 설정에서 등록하세요.')

    context_line = f'추가 맥락: {extra_context}' if extra_context else ''
    prompt = TISTORY_PROMPT_TEMPLATE.format(
        keyword=keyword, category=category or '일반',
        context_line=context_line, style_note=_get_style_prompt(),
    )

    body = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.8, 'maxOutputTokens': 8192},
    }).encode('utf-8')

    req = urllib.request.Request(
        f'{GEMINI_URL}?key={api_key}',
        data=body,
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        raise ValueError(f'Gemini API 오류 {e.code}: {error_body[:300]}')

    raw = resp['candidates'][0]['content']['parts'][0]['text']
    return _parse_post(raw, keyword)


def _parse_post(raw: str, keyword: str) -> dict:
    title_m = re.search(r'TITLE:\s*(.+)', raw)
    tags_m = re.search(r'TAGS:\s*(.+)', raw)
    body_m = re.search(r'---\n(.*?)---', raw, re.DOTALL)

    title = title_m.group(1).strip() if title_m else f'{keyword} 완전정리'
    if body_m:
        content = body_m.group(1).strip()
    else:
        after_first_dash = re.split(r'---\n', raw, maxsplit=1)
        content = (after_first_dash[1] if len(after_first_dash) > 1 else raw).strip()
    tags = tags_m.group(1).strip() if tags_m else keyword
    tags = tags.strip('[]').strip()  # 모델이 대괄호까지 그대로 반환하는 경우 대비(2026-07-26 실측)

    content = content.replace('*', '')

    _validate_generated(title, content)
    return {'title': title, 'content': content, 'tags': tags}


def _validate_generated(title: str, content: str):
    """모델이 형식 틀을 그대로 echo하는 경우를 걸러냄."""
    placeholder_markers = ['[제목]', '[본문', '[태그', '[키워드', 'TITLE: [', 'TAGS: [']
    if any(m in title for m in placeholder_markers) or any(m in content for m in placeholder_markers):
        raise ValueError(f'모델이 형식 틀을 그대로 반환함(재시도 필요): title={title!r}')
    if len(content) < 300:
        raise ValueError(f'생성된 본문이 너무 짧음({len(content)}자, 재시도 필요)')
    if content.count('|') >= 3:
        raise ValueError('마크다운 표(|) 유출 의심 — 재시도 필요')

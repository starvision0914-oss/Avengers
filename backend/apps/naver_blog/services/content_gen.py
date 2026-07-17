"""Claude API를 이용한 블로그 글 생성"""
import os
import re

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = 'claude-sonnet-4-6'

BLOG_SYSTEM_PROMPT = """당신은 네이버 블로그 전문 작가입니다.
규칙:
- 글자 수: 1500~2000자 (공백 포함)
- 구성: 서론(도입) → 본론(핵심정보 3~4단락) → 결론(요약)
- 키워드는 제목과 본문에 자연스럽게 5~6회 포함
- 실제로 겪지 않은 개인 경험이나 후기를 지어내지 말 것. 주어진 정보(추가 맥락)에 실제 경험이 있으면 그것만 반영하고, 없으면 사실 정보 위주로 작성
- 딱딱한 나열식 문체보다 대화하듯 자연스러운 톤을 쓰되, 사실관계를 과장하거나 확정적으로 단정하지 말 것
- 소제목은 '## '으로 구분
- 이모지 사용 금지
- 출처가 불확실하거나 변동성이 큰 수치(가격, 예측치 등)는 단정적으로 쓰지 말고 참고 수준으로 표현"""


def _call_claude(prompt: str, system: str = BLOG_SYSTEM_PROMPT) -> str:
    if not ANTHROPIC_API_KEY:
        raise ValueError('ANTHROPIC_API_KEY 환경변수 없음')

    import urllib.request
    import json

    body = json.dumps({
        'model': MODEL,
        'max_tokens': 3000,
        'system': system,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=body,
        headers={
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode('utf-8'))
    return resp['content'][0]['text']


def generate_post(keyword: str, category: str = '', extra_context: str = '') -> dict:
    """
    반환: {title, content, tags}
    """
    prompt = f"""키워드: {keyword}
카테고리: {category or '일반'}
{f"추가 맥락: {extra_context}" if extra_context else ""}

위 키워드로 네이버 블로그 포스팅을 작성해주세요.
형식:
TITLE: [제목]
---
[본문 내용]
---
TAGS: [태그1,태그2,태그3,태그4,태그5]"""

    raw = _call_claude(prompt)

    title_match = re.search(r'TITLE:\s*(.+)', raw)
    tags_match = re.search(r'TAGS:\s*(.+)', raw)
    body_match = re.search(r'---\n(.*?)---', raw, re.DOTALL)

    title = title_match.group(1).strip() if title_match else f'{keyword} 완전정복'
    content = body_match.group(1).strip() if body_match else raw
    tags = tags_match.group(1).strip() if tags_match else keyword

    content = _humanize(content)

    return {
        'title': title,
        'content': content,
        'tags': tags,
    }


def _humanize(text: str) -> str:
    """딱딱한 정형 문구를 자연스러운 어조로 치환 (사실 왜곡·경험 조작 없음)"""
    replacements = [
        ('첫째,', '먼저'),
        ('둘째,', '그다음으로'),
        ('셋째,', '마지막으로'),
        ('결론적으로,', '정리하자면'),
        ('다음과 같습니다:', '이렇습니다.'),
        ('중요합니다.', '중요해요.'),
        ('필요합니다.', '필요해요.'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text

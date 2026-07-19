"""Claude API를 이용한 블로그 글 생성"""
import os
import re

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = 'claude-sonnet-4-6'

# 이 아래 규칙은 고정(사용자가 설정 화면에서 바꿀 수 없음) — 정직성/정확성 관련 규칙.
# 톤·서식 취향은 NaverBlogSetting.style_prompt로 사용자가 별도 추가 가능(get_system_prompt 참고).
BLOG_SYSTEM_PROMPT = """당신은 네이버 블로그 전문 작가입니다.
규칙:
- 글자 수: 1500~2000자 (공백 포함)
- 구성: 서론(도입) → 본론(핵심정보 3~4단락) → 결론(요약)
- 키워드는 제목과 본문에 자연스럽게 5~6회 포함
- 실제로 겪지 않은 개인 경험이나 후기를 지어내지 말 것. 주어진 정보(추가 맥락)에 실제 경험이 있으면 그것만 반영하고, 없으면 사실 정보 위주로 작성
- 전형적인 AI식 서두("안녕하세요! 오늘은 ~에 대해 알아보겠습니다")나 딱딱한 나열식 문체 대신, 대화하듯 자연스러운 구어체 톤을 쓰되 사실관계를 과장하거나 확정적으로 단정하지 말 것
- 가독성을 위해 2~3문장마다 줄바꿈
- 비교가 필요한 부분은 간단한 표로 정리해도 좋음
- 소제목은 '## '으로 구분 (크롤러가 자동으로 굵은 글씨로 변환함)
- 본문 전체에 별표(*) 기호를 절대 쓰지 말 것 (강조는 문단 구성이나 소제목으로만 표현)
- 마지막 문단은 댓글·소통을 유도하는 다정한 인사로 마무리
- 이모지 사용 금지, 본문 끝 해시태그 나열 금지(태그는 별도 필드로 처리됨)
- 출처가 불확실하거나 변동성이 큰 수치(가격, 예측치 등)는 단정적으로 쓰지 말고 참고 수준으로 표현"""


def get_system_prompt() -> str:
    """고정 규칙 + 사용자가 설정에서 추가한 톤/스타일 프롬프트(있으면)."""
    from apps.naver_blog.models import NaverBlogSetting
    base = BLOG_SYSTEM_PROMPT
    try:
        s = NaverBlogSetting.objects.first()
        if s and s.style_prompt.strip():
            base += '\n\n추가 스타일 지침(사용자 설정):\n' + s.style_prompt.strip()
    except Exception:
        pass
    return base


def _call_claude(prompt: str, system: str = None) -> str:
    system = system or get_system_prompt()
    if not ANTHROPIC_API_KEY:
        raise ValueError('ANTHROPIC_API_KEY 환경변수 없음')

    import urllib.request
    import json

    body = json.dumps({
        'model': MODEL,
        'max_tokens': 6000,
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


def generate_shopping_post(product_info: dict, product_match: str, category: str = '', extra_context: str = '') -> dict:
    """쇼핑커넥트 링크에서 읽어온 실제 상품 정보(product_info)로 리뷰형 포스팅 생성.
    product_match: 쇼핑커넥트 삽입 시 상품을 찾는 데 쓸 문자열(보통 브랜드명) — 반드시 본문에 [쇼핑상품:{product_match}] 마커로 포함시킴.
    반환: {title, content, tags}
    """
    facts_lines = [f"- 상품명: {product_info.get('title') or '(확인 불가)'}"]
    if product_info.get('price'):
        facts_lines.append(f"- 판매가: {product_info['price']:,}원")
    if product_info.get('orig_price'):
        facts_lines.append(f"- 정가: {product_info['orig_price']:,}원")
    if product_info.get('discount_pct'):
        facts_lines.append(f"- 할인율: {product_info['discount_pct']}%")
    if product_info.get('rating'):
        facts_lines.append(f"- 평점: {product_info['rating']}")
    if product_info.get('review_count'):
        facts_lines.append(f"- 리뷰 수: {product_info['review_count']}건")
    facts = '\n'.join(facts_lines)

    prompt = f"""아래는 실제 상품 페이지에서 읽어온 사실 정보입니다. 이 정보만 근거로 쓰고, 여기 없는 스펙(색상, 소재, 상세 기능 등)은 추측해서 지어내지 마세요 — 확실하지 않으면 언급하지 않거나 "상세페이지에서 확인 가능"이라고 안내하세요.

{facts}
{f"카테고리: {category}" if category else ""}
{f"추가 맥락: {extra_context}" if extra_context else ""}

이 상품을 소개하고 구매를 설득하는 네이버 블로그 포스팅을 작성해주세요.
구성: 서론 → 핵심 요약 → 스펙 기반 설득 → 장단점(단점 포함) → 가격 안내 → [쇼핑상품] 마커 → 마무리 결론 문단(댓글/공감 유도). 마커 이후 마무리 문단 없이 끝내지 마세요.
비교가 필요하면 마크다운 표(파이프 | 기호)를 절대 쓰지 마세요 — 에디터가 표로 렌더링하지 못해 기호가 그대로 노출됩니다. 문장으로 풀어서 비교하세요.
본문 중 상품 카드를 삽입할 위치(설득이 끝난 후반부, 1곳만)에 정확히 아래 마커를 단독 줄로 넣어주세요:
[쇼핑상품:{product_match}]

형식:
TITLE: [제목]
---
[본문 내용]
---
TAGS: [태그1,태그2,태그3,...]"""

    raw = _call_claude(prompt)

    title_match = re.search(r'TITLE:\s*(.+)', raw)
    tags_match = re.search(r'TAGS:\s*(.+)', raw)
    body_match = re.search(r'---\n(.*?)---', raw, re.DOTALL)

    title = title_match.group(1).strip() if title_match else (product_info.get('title') or '상품 소개')
    if body_match:
        content = body_match.group(1).strip()
    else:
        after_first_dash = re.split(r'---\n', raw, maxsplit=1)
        content = (after_first_dash[1] if len(after_first_dash) > 1 else raw).strip()
    tags = tags_match.group(1).strip() if tags_match else ''

    content = _humanize(content)

    if f'[쇼핑상품:{product_match}]' not in content:
        content += f'\n\n[쇼핑상품:{product_match}]'

    _validate_generated(title, content)
    return {'title': title, 'content': content, 'tags': tags}


def _validate_generated(title: str, content: str):
    """모델이 형식 틀(예: '[제목]', '[본문]')을 그대로 echo하는 경우를 걸러냄(2026-07-19 발견)."""
    placeholder_markers = ['[제목]', '[본문', '[태그', '[키워드', 'TITLE: [', 'TAGS: [']
    if any(m in title for m in placeholder_markers) or any(m in content for m in placeholder_markers):
        raise ValueError(f'모델이 형식 틀을 그대로 반환함(재시도 필요): title={title!r}')
    if len(content) < 300:
        raise ValueError(f'생성된 본문이 너무 짧음({len(content)}자, 재시도 필요)')
    if content.count('|') >= 3:
        raise ValueError('마크다운 표(|) 유출 의심 — 재시도 필요')


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
    text = text.replace('*', '')
    return text

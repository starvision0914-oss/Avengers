"""Gemini API 블로그 글 생성"""
import json
import urllib.request
import base64
import os


GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent'

BLOG_PROMPT_TEMPLATE = """당신은 네이버 블로그 전문 작가입니다.

키워드: {keyword}
카테고리: {category}
{context_line}

아래 규칙으로 네이버 블로그 포스팅을 작성하세요:
- 글자 수: 1500~2000자 (공백 포함)
- 구성: 서론(도입) → 본론(핵심정보 3~4단락, 소제목 ## 사용) → 결론(요약)
- 키워드를 제목과 본문에 자연스럽게 5~6회 포함
- 실제로 겪지 않은 개인 경험이나 후기를 지어내지 말 것. 추가 맥락에 실제 경험이 주어졌으면 그것만 반영하고, 없으면 사실 정보 위주로 작성
- 전형적인 AI식 서두("안녕하세요! 오늘은 ~에 대해 알아보겠습니다")나 딱딱한 나열식 문체 대신, 대화하듯 자연스러운 구어체 톤을 쓰되 사실관계를 과장하거나 확정적으로 단정하지 말 것
- 가독성을 위해 2~3문장마다 줄바꿈
- 비교가 필요한 부분은 간단한 표로 정리해도 좋음
- 본문 전체에 별표(*) 기호를 절대 쓰지 말 것 (강조는 문단 구성이나 소제목으로만 표현)
- 마지막 문단은 댓글·소통을 유도하는 다정한 인사로 마무리
- 이모지 사용 금지, 본문 끝 해시태그 나열 금지(태그는 별도 필드로 처리됨)
- 출처가 불확실하거나 변동성이 큰 수치(가격, 예측치 등)는 단정적으로 쓰지 말고 참고 수준으로 표현
{style_note}
{image_note}

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
    from apps.naver_blog.models import NaverBlogSetting
    try:
        s = NaverBlogSetting.objects.first()
        if s and s.gemini_api_key:
            return s.gemini_api_key
    except Exception:
        pass
    return os.environ.get('GEMINI_API_KEY', '')


def generate_post_gemini(keyword: str, category: str = '', extra_context: str = '',
                          image_paths: list = None) -> dict:
    """
    image_paths: 로컬 이미지 파일 경로 리스트 (인라인 base64)
    반환: {title, content, tags}
    """
    api_key = _get_api_key()
    if not api_key:
        raise ValueError('Gemini API 키 없음. 설정에서 등록하세요.')

    image_paths = image_paths or []
    context_line = f'추가 맥락: {extra_context}' if extra_context else ''
    image_note = f'첨부 이미지 {len(image_paths)}장을 참고해 관련 내용을 본문에 자연스럽게 포함하세요.' if image_paths else ''

    prompt = BLOG_PROMPT_TEMPLATE.format(
        keyword=keyword,
        category=category or '일반',
        context_line=context_line,
        image_note=image_note,
        style_note=_get_style_prompt(),
    )

    # 메시지 파트 구성
    parts = [{'text': prompt}]

    # 이미지 인라인 추가 (최대 5장)
    for img_path in image_paths[:5]:
        try:
            with open(img_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            ext = img_path.rsplit('.', 1)[-1].lower()
            mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                    'png': 'image/png', 'webp': 'image/webp'}.get(ext, 'image/jpeg')
            parts.append({'inline_data': {'mime_type': mime, 'data': img_data}})
        except Exception as e:
            print(f'[gemini] 이미지 로드 실패: {img_path} — {e}')

    body = json.dumps({
        'contents': [{'parts': parts}],
        'generationConfig': {
            'temperature': 0.8,
            'maxOutputTokens': 8192,
        },
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


SHOPPING_PROMPT_TEMPLATE = """당신은 네이버 블로그 전문 작가입니다.

아래는 실제 상품 페이지에서 읽어온 사실 정보입니다. 이 정보만 근거로 쓰고, 여기 없는 스펙(색상, 소재, 상세 기능 등)은 추측해서 지어내지 마세요 — 확실하지 않으면 언급하지 않거나 "상세페이지에서 확인 가능"이라고 안내하세요.

{facts}
{category_line}
{context_line}

아래 규칙으로 이 상품을 소개하고 구매를 설득하는 네이버 블로그 포스팅을 작성하세요:
- 구성: 서론(공감되는 고민 제기) → 핵심 요약 → 스펙 기반 설득 → 장단점(단점도 포함) → 가격 안내 → [쇼핑상품] 마커 → 마무리 결론 문단(댓글/공감 유도)
- 전체 글이 위 구성을 다 마치고 마무리 결론까지 반드시 포함하도록, 앞부분에서 너무 길게 쓰지 말고 각 섹션을 간결하게 배분할 것. 마커 이후 마무리 문단 없이 끝내지 말 것
- 비교가 필요하면 마크다운 표(파이프 | 기호)를 절대 쓰지 말 것 — 에디터가 표로 렌더링하지 못해 기호가 그대로 노출됨. 문장으로 풀어서 비교 설명할 것
- 실제로 써보지 않은 제품에 "제가 써보니" 같은 표현을 절대 쓰지 말 것. 스펙과 논리로 설득
- 전형적인 AI식 서두 대신 대화하듯 자연스러운 구어체 톤
- 가독성을 위해 2~3문장마다 줄바꿈
- 소제목은 '## '으로 구분
- 본문 전체에 별표(*) 기호를 절대 쓰지 말 것
- 이모지 사용 금지, 본문 끝 해시태그 나열 금지(태그는 별도 필드로 처리됨)
- 가격 언급 시 "가격/혜택은 판매처와 시기에 따라 변동될 수 있다"는 안내 포함
- 이 글에 제휴 링크가 포함된다는 사실을 본문 초반에 명확히 고지하는 문장을 넣을 것
- 본문 중 상품 카드를 삽입할 위치(설득이 끝난 후반부, 딱 1곳)에 정확히 아래 마커를 단독 줄로 넣을 것: [쇼핑상품:{product_match}]
- '핵심 요약' 섹션 바로 뒤에는 카드 없이 텍스트로만 "실제 가격/할인율은 글 아래쪽에서 확인 가능"이라는 안내 문장을 추가할 것
{style_note}

형식 (반드시 지킬 것):
TITLE: [제목]
---
[본문]
---
TAGS: [태그1,태그2,태그3,...]"""


def generate_shopping_post_gemini(product_info: dict, product_match: str, category: str = '', extra_context: str = '') -> dict:
    """쇼핑커넥트 링크에서 읽어온 실제 상품 정보로 리뷰형 포스팅 생성 (Gemini).
    반환: {title, content, tags}"""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError('Gemini API 키 없음. 설정에서 등록하세요.')

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

    prompt = SHOPPING_PROMPT_TEMPLATE.format(
        facts='\n'.join(facts_lines),
        category_line=f'카테고리: {category}' if category else '',
        context_line=f'추가 맥락: {extra_context}' if extra_context else '',
        product_match=product_match,
        style_note=_get_style_prompt(),
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
    result = _parse_post(raw, product_info.get('title', ''))
    if f'[쇼핑상품:{product_match}]' not in result['content']:
        result['content'] += f'\n\n[쇼핑상품:{product_match}]'
    return result


def _parse_post(raw: str, keyword: str) -> dict:
    import re
    title_m = re.search(r'TITLE:\s*(.+)', raw)
    tags_m = re.search(r'TAGS:\s*(.+)', raw)
    body_m = re.search(r'---\n(.*?)---', raw, re.DOTALL)

    title = title_m.group(1).strip() if title_m else f'{keyword} 완전정복'
    if body_m:
        content = body_m.group(1).strip()
    else:
        # 응답이 잘려서 닫는 '---'가 없는 경우 — 첫 '---' 뒤부터만 취해 TITLE 줄이 본문에 섞이지 않게 함
        after_first_dash = re.split(r'---\n', raw, maxsplit=1)
        content = (after_first_dash[1] if len(after_first_dash) > 1 else raw).strip()
    tags = tags_m.group(1).strip() if tags_m else keyword

    content = content.replace('*', '')

    _validate_generated(title, content, tags)
    return {'title': title, 'content': content, 'tags': tags}


def _validate_generated(title: str, content: str, tags: str):
    """모델이 형식 틀(예: '[제목]', '[본문]')을 그대로 echo하는 경우를 걸러냄(2026-07-19 발견).
    실제 생성 대신 플레이스홀더가 그대로 나오면 조용히 저장하지 말고 여기서 예외를 던져 재시도/실패 처리되게 함."""
    placeholder_markers = ['[제목]', '[본문]', '[태그', '[키워드', 'TITLE: [', 'TAGS: [']
    if any(m in title for m in placeholder_markers) or any(m in content for m in placeholder_markers):
        raise ValueError(f'모델이 형식 틀을 그대로 반환함(재시도 필요): title={title!r}')
    if len(content) < 300:
        raise ValueError(f'생성된 본문이 너무 짧음({len(content)}자, 재시도 필요)')
    if content.count('|') >= 3:
        raise ValueError('마크다운 표(|) 유출 의심 — 재시도 필요')

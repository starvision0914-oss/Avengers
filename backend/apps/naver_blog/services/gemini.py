"""Gemini API 블로그 글 생성"""
import json
import urllib.request
import base64
import os


GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent'

BLOG_PROMPT_TEMPLATE = """당신은 네이버 블로그 전문 작가입니다.

키워드: {keyword}
카테고리: {category}
{context_line}

아래 규칙으로 네이버 블로그 포스팅을 작성하세요:
- 글자 수: 1500~2000자 (공백 포함)
- 구성: 서론(경험/공감) → 본론(핵심정보 3~4단락, 소제목 ## 사용) → 결론(요약)
- 키워드를 제목과 본문에 자연스럽게 5~6회 포함
- 개인 경험담, 의견, 팁을 담아 생동감 있게
- AI 특유의 나열식 작성 금지, 대화하듯 자연스럽게
- 이모지 사용 금지
{image_note}

형식 (반드시 지킬 것):
TITLE: [제목]
---
[본문]
---
TAGS: [태그1,태그2,태그3,태그4,태그5]"""


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
            'maxOutputTokens': 4096,
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


def _parse_post(raw: str, keyword: str) -> dict:
    import re
    title_m = re.search(r'TITLE:\s*(.+)', raw)
    tags_m = re.search(r'TAGS:\s*(.+)', raw)
    body_m = re.search(r'---\n(.*?)---', raw, re.DOTALL)

    title = title_m.group(1).strip() if title_m else f'{keyword} 완전정복'
    content = body_m.group(1).strip() if body_m else raw
    tags = tags_m.group(1).strip() if tags_m else keyword

    return {'title': title, 'content': content, 'tags': tags}

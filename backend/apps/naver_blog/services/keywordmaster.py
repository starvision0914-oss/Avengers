"""네이버 블로그 검색 수 → 경쟁도 분류 (공식 Blog Search API 사용)"""
import os
import time
import urllib.request
import urllib.parse
import json

NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID', '')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET', '')
BLOG_SEARCH_URL = 'https://openapi.naver.com/v1/search/blog.json'


def _naver_blog_count(keyword: str) -> int:
    """공식 Blog Search API로 블로그 게시물 수 조회"""
    if not NAVER_CLIENT_ID:
        return 0
    try:
        url = f'{BLOG_SEARCH_URL}?query={urllib.parse.quote(keyword)}&display=1'
        req = urllib.request.Request(url, headers={
            'X-Naver-Client-Id': NAVER_CLIENT_ID,
            'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
        return data.get('total', 0)
    except Exception as e:
        print(f'[keywordmaster] blog count 오류: {e}')
        return 0


def collect_keyword_data(keyword: str) -> dict:
    """
    반환: search_pc, search_mobile, search_total, blog_count, competition
    """
    blog_count = _naver_blog_count(keyword)
    time.sleep(0.3)

    # 경쟁도 분류 (블로그 수 기준 — 네이버 블로그 SEO 기준)
    # low: 3만 미만 (상위노출 가능)
    # mid: 3만~20만 (노력하면 가능)
    # high: 20만 초과 (상위노출 어려움)
    if blog_count < 30000:
        competition = 'low'
    elif blog_count < 200000:
        competition = 'mid'
    else:
        competition = 'high'

    return {
        'search_pc': 0,
        'search_mobile': 0,
        'search_total': 0,
        'blog_count': blog_count,
        'competition': competition,
    }

"""네이버 데이터랩 검색어 트렌드 API"""
import os
import json
import urllib.request
import urllib.parse
from datetime import date, timedelta


NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID', '')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET', '')
DATALAB_URL = 'https://openapi.naver.com/v1/datalab/search'


def get_trend(keywords: list[str], start_date: str = None, end_date: str = None,
              time_unit: str = 'month') -> dict:
    """
    keywords: 최대 5개 키워드 리스트
    time_unit: date/week/month
    반환: {keyword: [{period, ratio}, ...]}
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return {}

    if not end_date:
        end_date = date.today().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (date.today() - timedelta(days=365)).strftime('%Y-%m-%d')

    keyword_groups = [
        {'groupName': kw, 'keywords': [kw]}
        for kw in keywords[:5]
    ]

    body = json.dumps({
        'startDate': start_date,
        'endDate': end_date,
        'timeUnit': time_unit,
        'keywordGroups': keyword_groups,
    }).encode('utf-8')

    req = urllib.request.Request(DATALAB_URL)
    req.add_header('X-Naver-Client-Id', NAVER_CLIENT_ID)
    req.add_header('X-Naver-Client-Secret', NAVER_CLIENT_SECRET)
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, data=body, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'[datalab] API 오류: {e}')
        return {}

    output = {}
    for item in result.get('results', []):
        kw = item['title']
        output[kw] = item.get('data', [])
    return output


def get_trend_score(keyword: str) -> float:
    """최근 3개월 평균 트렌드 점수 (0~100)"""
    end = date.today()
    start = end - timedelta(days=90)
    data = get_trend([keyword], start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), 'week')
    points = data.get(keyword, [])
    if not points:
        return 0.0
    return round(sum(p['ratio'] for p in points) / len(points), 1)

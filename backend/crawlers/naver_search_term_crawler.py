"""네이버 검색어(expKeyword) 리포트 수집 — 광고센터 내부 API(ads.naver.com/apis/sa/api/advanced-report/values).

실측 확인(2026-07-10):
  - "키워드"(keyword) 차원은 쇼핑검색광고(자동타겟팅)라 전부 빈값("-") — 수집 의미 없음.
  - "검색어"(expKeyword) 차원에 실사용 검색어 데이터가 있음(계정당 월 5~10만 행).
  - expKeyword는 API 제약상 상품/소재(nccAdId) 차원과 동시 조회 불가(상호배타) → 상품별 매칭 불가,
    계정 단위 월 집계만 가능. 광고그룹 단위는 결합 가능하나 그룹 하나에 상품이 수십~수백개 묶여 있어
    사실상 "상품별"이라 보기 어려워 채택하지 않음.
  - 인증: naver_ads_cookies.json 저장 쿠키 세션(XSRF-TOKEN) + X-AD-customer-id 헤더.
    (naver_search_ad.py의 _internal_stats_session과 동일한 세션 소스 재사용)

노이즈(노출만 있고 클릭 0인 검색어) 제외 — 클릭 또는 매출 있는 행만 저장.
"""
import json
import logging
import time

import requests

logger = logging.getLogger('smartstore')

_STATS_URL = "https://ads.naver.com/apis/sa/api/advanced-report/values"
_PAGE_SIZE = 1000


def _session_for(login_id: str):
    from apps.smartstore.services.naver_search_ad import _internal_stats_session
    return _internal_stats_session(login_id)


def fetch_search_terms(customer_id: str, login_id: str, since: str, until: str, log_fn=None) -> list:
    """계정의 검색어 리포트 전체 페이지네이션 수집 → 클릭 또는 매출 있는 행만 반환.
    Returns: [{"keyword": ..., "impression": ..., "click": ..., "cost": ..., "conv_cnt": ..., "conv_amt": ...}, ...]
    """
    def _log(m):
        logger.info(m)
        if log_fn:
            log_fn(m)

    sess, xsrf = _session_for(login_id)
    if not sess:
        _log(f'[naver-searchterm:{login_id}] 쿠키 없음')
        return []

    headers = {
        'Accept': 'application/json',
        'X-AD-customer-id': str(customer_id),
        'X-XSRF-TOKEN': xsrf,
        'X-Accept-Language': 'ko',
        'Referer': 'https://ads.naver.com/',
    }
    params_base = {
        'attributes': 'expKeyword',
        'values': json.dumps({"type": "metric", "fields": "impCnt,clkCnt,salesAmt,ccnt,convAmt"}),
        'since': since, 'until': until,
        'numberOfResults': _PAGE_SIZE, 'requestTotalResults': 1,
    }

    rows = []
    start = 0
    total = None
    while total is None or start < total:
        params = dict(params_base, startIndex=start)
        try:
            r = sess.get(_STATS_URL, headers=headers, params=params, timeout=30)
        except Exception as e:
            _log(f'[naver-searchterm:{login_id}] 요청 오류(startIndex={start}): {e}')
            break
        if not r.ok:
            _log(f'[naver-searchterm:{login_id}] HTTP {r.status_code} (startIndex={start})')
            break
        d = r.json()
        if total is None:
            total = d.get('totalResults', 0)
            _log(f'[naver-searchterm:{login_id}] 총 {total}행 (검색어, {since}~{until})')
        for row in d.get('body', []):
            keyword, imp, clk, sales, ccnt, conv = row
            clk_i, conv_i = int(clk or 0), int(conv or 0)
            if clk_i == 0 and conv_i == 0:
                continue
            rows.append({
                'keyword': keyword,
                'impression': int(imp or 0),
                'click': clk_i,
                'cost': int(float(sales or 0)),
                'conv_cnt': int(ccnt or 0),
                'conv_amt': conv_i,
            })
        start += _PAGE_SIZE
        time.sleep(0.15)

    _log(f'[naver-searchterm:{login_id}] 클릭/매출 있는 검색어 {len(rows)}건')
    return rows


def _upsert(account, ym, rows, log_fn=None):
    from apps.smartstore.models import NaverSearchTermReport
    if not rows:
        return 0
    objs = [
        NaverSearchTermReport(account=account, ym=ym, keyword=r['keyword'],
                               impression=r['impression'], click=r['click'], cost=r['cost'],
                               conv_cnt=r['conv_cnt'], conv_amt=r['conv_amt'])
        for r in rows
    ]
    NaverSearchTermReport.objects.filter(account=account, ym=ym).delete()
    NaverSearchTermReport.objects.bulk_create(objs, batch_size=500)
    return len(objs)


def crawl_one_account(account, ym: str, log_fn=None, save=True) -> int:
    """1계정 1개월 검색어 리포트 수집. ym: 'YYYY-MM'. 반환: 저장(또는 조회)건수."""
    def _log(m):
        logger.info(m)
        if log_fn:
            log_fn(m)

    y, m = ym.split('-')
    since = f'{ym}-01'
    import calendar
    last_day = calendar.monthrange(int(y), int(m))[1]
    until = f'{ym}-{last_day:02d}'

    login_id = account.naver_ad_login_id or account.naver_ad_ai_login_id
    customer_id = account.naver_ad_customer_id or account.naver_ad_ai_customer_id
    if not login_id or not customer_id:
        _log(f'[naver-searchterm:{account.id}] 계정/쿠키 미설정 — 스킵')
        return 0

    rows = fetch_search_terms(customer_id, login_id, since, until, log_fn)
    if not save:
        return len(rows)
    n = _upsert(account, ym, rows, log_fn)
    _log(f'[naver-searchterm:{account.display_name or account.store_name}] {n}건 저장')
    return n


def run_all_accounts(ym: str, account_filter=None, log_fn=None, save=True) -> dict:
    """검색어 리포트 전 계정 수집 (naver_ads_cookies.json에 쿠키 있는 계정만)."""
    import json as _json
    import os
    from apps.smartstore.models import SmartStoreAccount

    def _log(m):
        logger.info(m)
        if log_fn:
            log_fn(m)

    cookie_file = os.path.join(os.path.dirname(__file__), 'naver_ads_cookies.json')
    try:
        cookie_login_ids = set(_json.load(open(cookie_file)).keys())
    except Exception:
        cookie_login_ids = set()

    qs = SmartStoreAccount.objects.filter(is_active=True)
    accounts = [a for a in qs if (a.naver_ad_login_id in cookie_login_ids
                                   or a.naver_ad_ai_login_id in cookie_login_ids)]
    if account_filter:
        accounts = [a for a in accounts if a.id in account_filter or a.naver_ad_login_id in account_filter]

    _log(f'네이버 검색어 리포트 수집 시작 — {len(accounts)}계정, {ym}')
    total = 0
    for a in accounts:
        try:
            total += crawl_one_account(a, ym, log_fn=log_fn, save=save)
        except Exception as e:
            _log(f'[naver-searchterm:{a.id}] 오류: {e}')
        time.sleep(1)
    result = {'accounts': len(accounts), 'saved': total, 'ym': ym}
    _log(f'완료: {result}')
    return result

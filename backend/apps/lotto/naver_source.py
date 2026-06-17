"""네이버 검색 결과 기반 로또 데이터 소스 (dhlottery WAF 차단 우회용)."""
import re
import time
import random
import requests

NAVER_URL = 'https://search.naver.com/search.naver?query=로또+{}회'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'


def _make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.5',
    })
    return s


_RE_WIN_BLOCK = re.compile(r'<div class="winning_number">(.*?)</div>', re.S)
_RE_BONUS_BLOCK = re.compile(r'<div class="bonus_number">(.*?)</div>', re.S)
_RE_BALL = re.compile(r'<span class="ball[^"]*">(\d+)</span>')
_RE_DATE_NAVER = re.compile(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일')


def fetch_one(session, drw_no, timeout=8):
    """returns dict | None.
    dict: {'drwNo': int, 'date': 'YYYY-MM-DD' or '', 'nums': [6], 'bonus': int}
    None: 해당 회차 정보 없음 (미발행 또는 검색 결과 없음)
    raise: 네트워크 에러
    """
    r = session.get(NAVER_URL.format(drw_no), timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f'네이버 HTTP {r.status_code}')
    html = r.text
    m = _RE_WIN_BLOCK.search(html)
    if not m:
        return None
    nums = [int(n) for n in _RE_BALL.findall(m.group(1))]
    if len(nums) != 6:
        return None
    bonus = None
    bm = _RE_BONUS_BLOCK.search(html)
    if bm:
        bn = _RE_BALL.findall(bm.group(1))
        if bn:
            bonus = int(bn[0])
    # 추첨일 — winning_number 이후 ±20KB 범위에서 '회 로또 ... YYYY년 M월 D일에 추첨' 패턴
    near = html[m.start(): m.start() + 30000]
    date_str = ''
    dm = _RE_DATE_NAVER.search(near)
    if dm:
        y, mo, d = dm.groups()
        date_str = f'{int(y):04d}-{int(mo):02d}-{int(d):02d}'
    return {
        'drwNo': drw_no, 'date': date_str,
        'nums': nums, 'bonus': bonus,
    }


def bulk_sync(start=1, end=None, existing_drws=None, sleep_range=(0.25, 0.55),
              stop_on_missing=10, log_fn=None, max_retries=2):
    """1~end 까지 네이버에서 가져와 yield.
    - 네트워크 에러는 max_retries 회 재시도 (지수 백오프)
    - 페이싱 0.25~0.55초 (네이버 친화적)
    - consec_missing >= stop_on_missing (정보없음 + 영구실패) 시 자동 중단
    """
    existing = existing_drws or set()
    sess = _make_session()
    consec_missing = 0
    drw = start
    while True:
        if end and drw > end:
            break
        if drw in existing:
            drw += 1
            continue

        rec = None
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                rec = fetch_one(sess, drw)
                last_err = None
                break
            except Exception as e:
                last_err = e
                if attempt < max_retries:
                    wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                    if log_fn:
                        log_fn(f'{drw}회 임시 오류 {type(e).__name__} — {wait:.1f}s 후 재시도')
                    time.sleep(wait)

        if last_err is not None:
            if log_fn:
                log_fn(f'{drw}회 영구 실패: {type(last_err).__name__}')
            consec_missing += 1
            if consec_missing >= stop_on_missing:
                break
            drw += 1
            time.sleep(random.uniform(*sleep_range))
            continue

        if rec is None:
            if log_fn:
                log_fn(f'{drw}회 정보 없음')
            consec_missing += 1
            if consec_missing >= stop_on_missing:
                break
        else:
            consec_missing = 0
            yield rec
        drw += 1
        time.sleep(random.uniform(*sleep_range))

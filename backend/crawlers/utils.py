import re
from datetime import datetime

def parse_int(value):
    if not value:
        return 0
    if isinstance(value, float):
        return int(value)
    cleaned = re.sub(r'[^\d-]', '', str(value))
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return 0

def classify_description(desc):
    desc_lower = (desc or '').lower()
    if 'ai' in desc_lower or '매출업' in desc_lower:
        return 'AI'
    if 'cpc' in desc_lower or '키워드' in desc_lower:
        return 'CPC'
    if '서버이용료' in desc_lower:
        return '서버이용료'
    if '프라임' in desc_lower:
        return '프라임'
    return '기타'

def classify_11st_description(desc):
    desc = desc or ''
    if 'NewCPC' in desc or 'CPC' in desc:
        return 'CPC'
    # '수수료결제' = 광고 관련 수수료(사용자 확인, 2026-07-19) — CPC에 합산.
    # '서버이용료 결제' 등 다른 수수료 항목과 헷갈리지 않게 정확한 문자열로만 매칭.
    if '수수료결제' in desc:
        return 'CPC'
    # 서버이용료 — 지마켓 '서버비용'과 동일 성격의 광고비. 2026-09-02까지 OTHERS로 새어
    # 광고비 집계에서 누락되던 것 발견·수정(15건, -1,155,000원).
    if '서버이용료' in desc:
        return 'CPC'
    if '프로모션' in desc or '보상' in desc:
        return 'REWARD'
    if '충전' in desc:
        return 'CHARGE'
    if '미수금상환' in desc or '정산' in desc or '입금' in desc:
        return 'SETTLE'
    # '셀러 광고포인트 지급' 등 — "광고"라는 글자 때문에 안전망 규칙에 걸려 CPC(광고비)로
    # 잘못 집계되던 것 발견·수정(2026-09-04). 실제 지출이 아니라 11번가가 주는 포인트
    # 지급(+)이라 CHARGE(충전/정산)로 분류.
    if '포인트' in desc and '지급' in desc:
        return 'CHARGE'
    # 안전망: 위 규칙에 못 걸려도 '광고'라는 글자가 있으면 광고비로 집계.
    # 11번가가 광고상품명을 바꿔도(지마켓 AI매출업→AI Product AD 사례처럼) 개별 규칙
    # 추가가 늦어 그 사이 누락되는 걸 방지.
    if '광고' in desc:
        return 'CPC'
    return 'OTHERS'

def wait_for_download(directory, timeout=60, ext='.xls'):
    import time
    from pathlib import Path
    start = time.time()
    while time.time() - start < timeout:
        dl_files = list(Path(directory).glob('*.crdownload'))
        target_files = list(Path(directory).glob(f'*{ext}')) + list(Path(directory).glob('*.xlsx'))
        if target_files and not dl_files:
            newest = max(target_files, key=lambda f: f.stat().st_mtime)
            return newest
        time.sleep(1)
    raise Exception(f'다운로드 타임아웃 ({timeout}초)')

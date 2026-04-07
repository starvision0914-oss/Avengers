import re
from datetime import datetime

def parse_int(value):
    if not value:
        return 0
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
    if '프로모션' in desc or '보상' in desc:
        return 'REWARD'
    if '충전' in desc:
        return 'CHARGE'
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

"""11번가 셀러오피스 대량등록 변환 — PlayAuto 최적화엑셀(87컬럼) → 11번가 양식(Ver2.70, 113컬럼).

변환된 .xls를 셀러오피스 view/35922 의 excelFile 에 업로드 → 등록.
소량(5개) 테스트 → 등록실패 다운로드 확인 → 보완 → 확대.

⚠️ 카테고리 코드(PlayAuto 값이 11번가 카테고리인지)·고시유형코드는 5개 테스트로 검증 필요.
"""
import openpyxl
import xlrd
from xlutils.copy import copy as xl_copy

TEMPLATE = '/tmp/11st_template_dl/ExcelProductList-Ver2.70.xls'
NICKNAME = '스타블루'   # jinag7460 셀러 닉네임

# PlayAuto 최적화엑셀 컬럼 인덱스
PA = {
    'model': 1, 'manufacturer': 3, 'origin': 4, 'product_name': 5, 'opt_name': 6,
    'promo': 7, 'category': 9, 'sell_price': 14, 'ship_fee': 16, 'tax': 17, 'qty': 18,
    'image1': 19, 'image2': 20, 'image3': 21, 'image4': 22,
    'opt_div': 30, 'sel_option': 31, 'detail': 34, 'cert_type': 44, 'notice_code': 59,
}


def parse_playauto(path, limit=5):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    next(it)  # 헤더
    rows = []
    for i, r in enumerate(it):
        if limit and i >= limit:
            break
        rows.append(r)
    return rows


def _opt_convert(sel_option):
    """PlayAuto 옵션 '[색상=사이즈]\\n진분홍=M==0=999=0=0\\n...' → 11번가 옵션명/값/가격/재고.
    형식 추정 — 5개 테스트로 검증·보정."""
    s = str(sel_option or '').strip()
    if not s or '=' not in s:
        return None
    lines = s.split('\n')
    head = lines[0].strip('[]')
    if '=' not in head:
        return None
    names = head.split('=')
    vals = [[] for _ in names]
    prices, stocks = [], []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        # 값 부분: 옵션값들 == 뒤에 추가가격/재고
        before = ln.split('==')[0]
        parts = before.split('=')
        for i in range(len(names)):
            vals[i].append(parts[i] if i < len(parts) else '')
        tail = ln.split('==')[1].split('=') if '==' in ln else []
        prices.append((tail[0] if len(tail) > 0 and tail[0] else '0'))
        stocks.append((tail[1] if len(tail) > 1 and tail[1] else '999'))
    return {
        'name': '\n'.join(names),
        'val': '\n'.join('|'.join(v) for v in vals),
        'price': '|'.join(prices),
        'stock': '|'.join(stocks),
    }


def convert(playauto_path, out_path, nickname=NICKNAME, limit=5,
            notice_type='', rebate='2500', exchange='5000'):
    """PlayAuto 엑셀 → 11번가 양식 .xls 생성. 생성 행수 반환."""
    rows = parse_playauto(playauto_path, limit)
    rb = xlrd.open_workbook(TEMPLATE, formatting_info=True)
    wb = xl_copy(rb)
    ws = wb.get_sheet(0)
    for ri, pa in enumerate(rows):
        R = 4 + ri   # 데이터는 5행(0-index 4)부터
        def g(k):
            i = PA[k]
            v = pa[i] if i < len(pa) else None
            return '' if v is None else v
        ship_fee = str(g('ship_fee') or 0).replace('.0', '')
        ship_set = '01' if (not ship_fee or ship_fee == '0') else '02'
        v = {
            1: nickname, 3: '01',                       # 닉네임 / 판매방식 고정가
            9: str(g('category')).replace('.0', ''),    # 카테고리(11번가 코드)
            10: g('opt_name') or g('product_name'),     # 상품명(최적화)
            11: g('promo'), 13: '01',                   # 홍보문구 / 원산지 국내
            18: '01', 19: '01', 20: 'Y',                # 해외구매대행 일반 / 새상품 / 미성년자가능
            21: g('image1'), 22: g('image2'), 23: g('image3'), 24: g('image4'),
            25: g('detail'), 29: '108',                 # 상세 / 판매기간 120일
            31: str(g('sell_price')).replace('.0', ''), # 판매가
            46: str(g('qty') or 999).replace('.0', ''), # 재고
            53: '01', 54: '01', 58: ship_set, 59: ship_fee,   # 배송 전국/택배/설정/배송비
            62: '03', 63: rebate, 64: '01', 65: exchange,     # 결제 선결제 / 반품·교환비
            66: '상세설명을 참고하세요.', 67: '상세설명을 참고하세요.',  # AS / 반품안내
            70: str(notice_type or g('notice_code') or '').replace('.0', ''),  # 고시유형코드
            99: g('manufacturer'), 100: g('model'),
        }
        opt = _opt_convert(g('sel_option'))
        if opt:
            v[40] = '01'; v[41] = opt['name']; v[42] = opt['val']
            v[43] = opt['price']; v[44] = opt['stock']
        for ci, val in v.items():
            ws.write(R, ci, val)
    wb.save(out_path)
    return len(rows)

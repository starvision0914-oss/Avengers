"""11번가 상품 등록 서비스 (OpenAPI ProductService).

PlayAuto 최적화 엑셀(87컬럼, 최적화_*.xlsx) → 11번가 OpenAPI 상품등록(POST XML).

안전 원칙(실제 등록은 되돌리기 어려움):
- dry_run=True 기본 → XML만 생성(실제 등록 안 함). 검증 후 dry_run=False.
- limit으로 소량(5개) 테스트 → 검증 → 확대.
- 누적 보유 한도(등급별 5천~1만개) 준수. 등록 전 현재 상품수 확인.
- rate limit: 호출 간 지연(기본 1초).

⚠️ _build_product_xml의 정확한 11번가 ProductService XML 필수필드는
   deep-research(11번가 상품등록 OpenAPI 스펙) 확정 후 완성한다. 아래는 골격.
"""
import logging
import time

import openpyxl
import requests

logger = logging.getLogger('crawler')

# 11번가 OpenAPI 상품등록 엔드포인트 (REST, POST). 정확 경로는 스펙 확정 시 보정.
ELEVEN_REGISTER_URL = 'http://api.11st.co.kr/rest/prodservices/product'

# 최적화 엑셀(87컬럼) 컬럼 인덱스 매핑
COL = {
    'product_code': 0, 'model': 1, 'brand': 2, 'manufacturer': 3, 'origin': 4,
    'product_name': 5, 'opt_product_name': 6, 'promo': 7, 'summary_name': 8,
    'category_code': 9, 'user_category': 10,
    'market_price': 11, 'cost': 12, 'supply_price': 13, 'sell_price': 14,
    'ship_method': 15, 'ship_fee': 16, 'tax_type': 17, 'qty': 18,
    'image1': 19, 'image2': 20, 'image3': 21, 'image4': 22,
    'opt_div': 30, 'sel_option': 31, 'input_option': 32, 'add_option': 33,
    'detail_html': 34, 'keywords': 43, 'cert_type': 44, 'cert_info': 45,
    'notice_code': 59,  # 상품상세코드(고시) + 상품상세1~27(60~86)
}


def parse_excel(path, limit=None):
    """최적화 엑셀 → 상품 dict 리스트."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    next(it)  # 헤더 스킵
    products = []
    for i, row in enumerate(it):
        if limit and i >= limit:
            break
        p = {k: (row[v] if v < len(row) and row[v] is not None else '') for k, v in COL.items()}
        # 고시 상세1~27
        p['notice_details'] = [row[c] for c in range(60, min(87, len(row)))]
        products.append(p)
    return products


def _esc(v):
    """XML 이스케이프."""
    s = '' if v is None else str(v)
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def _build_product_xml(p):
    """상품 dict → 11번가 ProductService 등록 XML.

    ⚠️ TODO(스펙 확정 후 완성): 11번가 상품등록 XML의 정확한 필수 태그·코드값
       (dispCtgrNo, prdNm, selPrc, prdStckQty, prdImage, htmlDetail, 옵션, 고시템플릿,
        배송정보, A/S, 반품, 인증) — deep-research 결과로 채운다.
    아래는 주요 필드 골격(인코딩 euc-kr).
    """
    name = p.get('opt_product_name') or p.get('product_name') or ''
    xml = f"""<?xml version="1.0" encoding="euc-kr"?>
<Product>
  <selMthdCd>01</selMthdCd>
  <dispCtgrNo>{_esc(p.get('category_code'))}</dispCtgrNo>
  <prdNm>{_esc(name)}</prdNm>
  <selPrc>{_esc(p.get('sell_price'))}</selPrc>
  <prdSelQty>{_esc(p.get('qty') or '999')}</prdSelQty>
  <prdImage01>{_esc(p.get('image1'))}</prdImage01>
  <htmlDetail>{_esc(p.get('detail_html'))}</htmlDetail>
  <!-- TODO: 옵션/고시/배송/AS/반품/인증 필드 — 스펙 확정 후 추가 -->
</Product>"""
    return xml


def register_product(api_key, xml, timeout=30):
    """11번가 OpenAPI 상품등록 POST. (status_code, response_text) 반환."""
    headers = {'openapikey': api_key, 'Content-Type': 'text/xml; charset=euc-kr'}
    resp = requests.post(ELEVEN_REGISTER_URL, data=xml.encode('euc-kr', 'ignore'),
                         headers=headers, timeout=timeout)
    return resp.status_code, resp.text


def register_batch(login_id, excel_path, limit=5, dry_run=True, delay=1.0, log_fn=None):
    """배치 등록.
    dry_run=True(기본): XML만 생성·검증(실제 등록 안 함).
    dry_run=False: 실제 11번가 등록(소량 테스트 후에만!).
    """
    from apps.cpc.models import CrawlerAccount

    def _log(m):
        logger.info(m)
        if log_fn:
            log_fn(m)

    acc = CrawlerAccount.objects.filter(platform='11st', login_id=login_id).first()
    if not acc:
        return {'ok': False, 'error': f'계정 없음: {login_id}'}
    if not acc.api_key:
        return {'ok': False, 'error': f'{login_id} api_key 없음'}

    products = parse_excel(excel_path, limit=limit)
    _log(f'[등록] {login_id} / 엑셀 {len(products)}개 / dry_run={dry_run}')
    results = []
    for i, p in enumerate(products, 1):
        xml = _build_product_xml(p)
        nm = (p.get('opt_product_name') or p.get('product_name') or '')[:40]
        if dry_run:
            results.append({'no': i, 'name': nm, 'dry_run': True, 'xml_len': len(xml)})
            _log(f'  [{i}] (dry) {nm} — XML {len(xml)}자')
        else:
            try:
                code, text = register_product(acc.api_key, xml)
                ok = code == 200 and ('성공' in text or '<resultCode>0' in text or 'SUCCESS' in text.upper())
                results.append({'no': i, 'name': nm, 'status': code, 'ok': ok, 'resp': text[:150]})
                _log(f'  [{i}] {"✅" if ok else "❌"} {nm} — {code}')
            except Exception as e:
                results.append({'no': i, 'name': nm, 'error': str(e)[:120]})
                _log(f'  [{i}] 오류 {nm} — {str(e)[:80]}')
            time.sleep(delay)  # rate limit
    return {'ok': True, 'count': len(results), 'dry_run': dry_run, 'results': results}

"""starvis7942 상품 N개의 hulk detail을 가져와 JSON으로 덤프 (Claude API 호출 없이 원본 데이터만)."""
import os, sys, django, json, time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/home/rejoice888/Avengers/backend')
django.setup()

from apps.cpc.models import CrawlerAccount, ElevenMyProduct
from apps.cpc.management.commands.optimize_11st_product_names import _get_session, _get_hulk_detail, _byte_len

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'starvis7942'
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 30
OFFSET = int(sys.argv[3]) if len(sys.argv) > 3 else 0
OUT = sys.argv[4] if len(sys.argv) > 4 else '/tmp/11st_raw_products.json'

acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='11st')
qs = ElevenMyProduct.objects.filter(account=acct, status_type='판매중').order_by('id')[OFFSET:OFFSET+LIMIT]
products = list(qs)
print(f'대상 {len(products)}개')

print('로그인 중...')
sess = _get_session(acct)
print('로그인 완료')

results = []
for i, mp in enumerate(products):
    prd_no = mp.product_no
    try:
        detail = _get_hulk_detail(sess, prd_no)
        results.append({
            'prd_no': prd_no,
            'current_name': detail.get('productName', mp.product_name or ''),
            'current_name_bytes': _byte_len(detail.get('productName', '')),
            'ad_phrase': detail.get('advertisementPhrase', ''),
            'category_no': detail.get('displayCategoryNo', ''),
            'seller_code': detail.get('sellerManagementCode', ''),
            'brand_name': (detail.get('brand') or {}).get('name', ''),
            'sell_price': detail.get('sellPrice', ''),
        })
        print(f'  [{i+1}/{len(products)}] {prd_no} {detail.get("productName","")[:40]}')
    except Exception as e:
        print(f'  [{i+1}/{len(products)}] {prd_no} 오류: {e}')
    time.sleep(0.5)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f'저장: {OUT} ({len(results)}건)')

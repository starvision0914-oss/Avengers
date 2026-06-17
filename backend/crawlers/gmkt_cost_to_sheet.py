"""지마켓+옥션 계정별 기간 광고비 집계 → 구글 시트 업로드.
실행: python -u -c "import crawlers.gmkt_cost_to_sheet" START END [SHEET_KEY] [TAB]
기본 시트: 지마켓 CPC 스프레드시트, 탭: '계정별광고비_START_END'
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from datetime import datetime
from collections import defaultdict
from apps.cpc.models import GmarketCostHistory, CrawlerAccount
from crawlers import gsheet_upload

a = sys.argv[1:]
START = datetime.strptime(a[0], '%Y-%m-%d').date()
END = datetime.strptime(a[1], '%Y-%m-%d').date()
SHEET_KEY = a[2] if len(a) > 2 else '10YWiqQcDdzij_eTmoTFPN9hGe2h3xsWlkIaKG4p4m80'  # 지마켓 CPC 시트
TAB = a[3] if len(a) > 3 else f'계정별광고비_{START}_{END}'
AD = ['CPC', 'AI매출업']

# 표시순서(config User 번호) 매핑
order = {acc.login_id: getattr(acc, 'display_order', 0) or 0
         for acc in CrawlerAccount.objects.filter(platform='gmarket')}

# 집계: seller_id × market × type
agg = defaultdict(lambda: defaultdict(int))
qs = GmarketCostHistory.objects.filter(use_date__gte=START, use_date__lte=END,
                                       transaction_type__in=AD).only('seller_id', 'market', 'transaction_type', 'amount')
for r in qs:
    key = (r.market, 'CPC' if r.transaction_type == 'CPC' else 'AI')
    agg[r.seller_id][key] += r.amount

rows = [['계정', '지마켓CPC', '지마켓AI', '옥션CPC', '옥션AI', '합계']]
tot = defaultdict(int)
sellers = sorted(agg.keys(), key=lambda s: (order.get(s, 999), s))
for s in sellers:
    gc = abs(agg[s][('gmarket', 'CPC')]); ga = abs(agg[s][('gmarket', 'AI')])
    ac = abs(agg[s][('auction', 'CPC')]); aa = abs(agg[s][('auction', 'AI')])
    tt = gc + ga + ac + aa
    rows.append([s, gc, ga, ac, aa, tt])
    tot['gc'] += gc; tot['ga'] += ga; tot['ac'] += ac; tot['aa'] += aa
rows.append(['합계', tot['gc'], tot['ga'], tot['ac'], tot['aa'],
             tot['gc'] + tot['ga'] + tot['ac'] + tot['aa']])

print(f'기간 {START}~{END} / 계정 {len(sellers)} / 총광고비 {rows[-1][5]:,}원')
print(f'시트 업로드: key={SHEET_KEY[:12]}… tab={TAB}')
ss = gsheet_upload.open_spreadsheet(SHEET_KEY)
ok = gsheet_upload.upload_rows(rows, TAB, ss)
print('업로드:', 'OK' if ok else '실패')
for r in rows:
    print('  ', r)

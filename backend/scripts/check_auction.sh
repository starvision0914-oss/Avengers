#!/bin/bash
# 옥션/지마켓 광고비 빠른 조회 — 거래원장(실제청구) + 상품별리포트 계정별 대조.
# 사용: bash scripts/check_auction.sh [YYYY] [MM]   (기본 당월)
cd /home/rejoice888/Avengers/backend
Y=${1:-$(date +%Y)}; M=${2:-$(date +%-m)}
/usr/bin/python3 manage.py shell -c "
from apps.cpc.models import GmarketCostHistory as H, GmarketProductAdCost as P
from django.db.models import Sum, Count
import datetime, calendar
y,m=$Y,$M
ms=datetime.date(y,m,1); me=datetime.date(y,m,calendar.monthrange(y,m)[1])
AD=['CPC','AI매출업']
print(f'=== {y}-{m:02d} 옥션 vs 지마켓 광고비 ===')
hg=abs(H.objects.filter(use_date__gte=ms,use_date__lte=me,market='gmarket',transaction_type__in=AD).aggregate(s=Sum('amount'))['s'] or 0)
ha=abs(H.objects.filter(use_date__gte=ms,use_date__lte=me,market='auction',transaction_type__in=AD).aggregate(s=Sum('amount'))['s'] or 0)
pg=P.objects.filter(year=y,month=m,site='G').aggregate(s=Sum('cost'))['s'] or 0
pa=P.objects.filter(year=y,month=m,site='A').aggregate(s=Sum('cost'))['s'] or 0
print(f'[거래원장-실제청구] 지마켓 {hg:,}원 / 옥션 {ha:,}원 ({ha*100/(hg+ha) if hg+ha else 0:.2f}%)')
print(f'[상품별리포트    ] 지마켓 {pg:,}원 / 옥션 {pa:,}원 ({pa*100/(pg+pa) if pg+pa else 0:.2f}%)')
print()
print('=== 옥션 광고비 있는 계정 (거래원장) ===')
for r in H.objects.filter(use_date__gte=ms,use_date__lte=me,market='auction',transaction_type__in=AD).values('seller_id').annotate(s=Sum('amount')).order_by('s'):
    print(f\"   {r['seller_id']:<12} {abs(r['s'] or 0):>8,}원\")
"

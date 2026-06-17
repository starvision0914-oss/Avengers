#!/bin/bash
cd /home/rejoice888/Avengers/backend
while pgrep -f "backfill_starvis7942.sh" >/dev/null 2>&1; do
  python3 manage.py shell -c "
from apps.cpc.models import St11ProductDaily
from apps.cpc.eleven_block_guard import _send_telegram_alert
from django.utils import timezone
qs=St11ProductDaily.objects.filter(eleven_id='starvis7942',stat_date__year=2026)
n=qs.count()
ds=list(qs.dates('stat_date','day'))
mx=max(ds).strftime('%m-%d') if ds else '아직없음'
_send_telegram_alert(f'⏳ [starvis7942 수집중 {timezone.localtime():%H:%M}]\n현재 {n:,}행 / 최근일자 {mx}')
" 2>/dev/null
  sleep 1800
done

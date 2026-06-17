#!/bin/bash
cd /home/rejoice888/Avengers/backend
LOG=/tmp/backfill_starvis7942.log
echo "=== starvis7942 월별 백필 시작 $(date '+%F %T') ===" > "$LOG"
for m in 2026-01-01:2026-01-31 2026-02-01:2026-02-28 2026-03-01:2026-03-31 2026-04-01:2026-04-30 2026-05-01:2026-05-31 2026-06-01:2026-06-08; do
  f=${m%%:*}; t=${m##*:}
  echo "--- [$f ~ $t] 시작 $(date '+%T') ---" >> "$LOG"
  /usr/bin/python3 manage.py crawl_11st_product_daily --accounts starvis7942 --from "$f" --to "$t" >> "$LOG" 2>&1
done
echo "=== starvis7942 백필 완료 $(date '+%F %T') ===" >> "$LOG"
python3 manage.py shell -c "
from apps.cpc.models import St11ProductDaily
from apps.cpc.eleven_block_guard import _send_telegram_alert
n=St11ProductDaily.objects.filter(eleven_id='starvis7942',stat_date__year=2026).count()
_send_telegram_alert(f'✅ [starvis7942 백필 완료]\n상품ROAS {n:,}행 수집 완료')
" >> "$LOG" 2>&1

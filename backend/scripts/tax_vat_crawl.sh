#!/bin/bash
# 세무 페이지 "크롤링" 버튼 — 플랫폼별 락 확인 후 부가세신고내역 크롤 실행.
# 사용법: tax_vat_crawl.sh <11st|gmarket|smartstore|coupang> <start_yyyymm> <end_yyyymm>
PLATFORM="$1"
START="$2"
END="$3"
cd /home/rejoice888/Avengers/backend
export PATH="/home/rejoice888/.local/bin:$PATH"
LOG="/tmp/tax_vat_crawl_${PLATFORM}.log"
echo "$(date '+%F %T') 세무 부가세 수동크롤 시작 platform=$PLATFORM ${START}~${END}" >> "$LOG"

python3 -c "
from apps.cpc import eleven_block_guard as guard
ok, holder = guard.acquire_global_lock('tax_vat_manual', platform='$PLATFORM')
import sys
sys.exit(0 if ok else 1)
"
if [ $? -ne 0 ]; then
  echo "$(date '+%F %T') 락 획득 실패 — 같은 플랫폼의 다른 크롤과 겹쳐 중단" >> "$LOG"
  exit 1
fi

python3 manage.py "crawl_${PLATFORM}_vat" --start "$START" --end "$END" >> "$LOG" 2>&1

python3 -c "
from apps.cpc import eleven_block_guard as guard
guard.release_global_lock(platform='$PLATFORM')
"
echo "$(date '+%F %T') 완료" >> "$LOG"

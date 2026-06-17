#!/bin/bash
# 11번가 2026 데이터 완결: 현재 백필 종료 대기 → 차단해제 대기 → 누락 상품ROAS + 광고비 단독 수집
# 동시 크롤 금지(차단 유발). 항상 단독·순차로만 실행.
set -u
cd /home/rejoice888/Avengers/backend
LOG=/tmp/finish_11st_2026.log
echo "=== 시작 $(date '+%F %T') ===" > "$LOG"

# 1) 현재 돌고 있는 상품ROAS 백필 종료 대기
echo "[1] 기존 백필 종료 대기..." >> "$LOG"
while pgrep -f "crawl_11st_product_daily" >/dev/null 2>&1; do sleep 60; done
echo "    백필 종료 확인 $(date '+%T')" >> "$LOG"

# 2) 글로벌 차단 해제까지 대기 (차단파일 기준, 추가 차단 방지)
echo "[2] 차단 해제 대기..." >> "$LOG"
while :; do
  BLK=$(python3 manage.py shell -c "from apps.cpc.eleven_block_guard import is_blocked; b,_,_=is_blocked(); print('1' if b else '0')" 2>/dev/null | tail -1)
  [ "$BLK" = "1" ] || break
  echo "    아직 차단중 $(date '+%T') — 60s 대기" >> "$LOG"
  sleep 60
done
sleep 120
echo "    차단 해제 확인 $(date '+%T')" >> "$LOG"

# 3) 상품ROAS 누락 계정 산출(백필 결과 반영) 후 단독 수집
MISS=$(python3 manage.py shell -c "
from apps.cpc.models import St11ProductDaily, CrawlerAccount
active=list(CrawlerAccount.objects.filter(platform='11st',is_active=True).values_list('login_id',flat=True))
have=set(St11ProductDaily.objects.filter(stat_date__year=2026).values_list('eleven_id',flat=True))
print(' '.join(a for a in active if a not in have))
" 2>/dev/null | tail -1)
echo "[3] 상품ROAS 누락계정: $MISS" >> "$LOG"
if [ -n "$MISS" ]; then
  python3 manage.py crawl_11st_product_daily --accounts $MISS --from 2026-01-01 >> "$LOG" 2>&1
fi
echo "    상품ROAS 수집 종료 $(date '+%T')" >> "$LOG"

# 4) 광고비(CPC) 누락 계정 산출 후 단독 수집 (2026-01-01부터)
CMISS=$(python3 manage.py shell -c "
from apps.cpc.models import ElevenCostHistory, CrawlerAccount
active=list(CrawlerAccount.objects.filter(platform='11st',is_active=True).values_list('login_id',flat=True))
have=set(ElevenCostHistory.objects.filter(transaction_datetime__year=2026).values_list('seller_id',flat=True))
print(' '.join(a for a in active if a not in have))
" 2>/dev/null | tail -1)
echo "[4] 광고비 누락계정: $CMISS" >> "$LOG"
if [ -n "$CMISS" ]; then
  python3 manage.py crawl_11st_cost --accounts $CMISS --start-date 2026-01-01 >> "$LOG" 2>&1
fi
echo "=== 완료 $(date '+%F %T') ===" >> "$LOG"

# 5) 최종 커버리지 요약
python3 manage.py shell -c "
from apps.cpc.models import St11ProductDaily, ElevenCostHistory, CrawlerAccount
active=list(CrawlerAccount.objects.filter(platform='11st',is_active=True).values_list('login_id',flat=True))
p=set(St11ProductDaily.objects.filter(stat_date__year=2026).values_list('eleven_id',flat=True))
c=set(ElevenCostHistory.objects.filter(transaction_datetime__year=2026).values_list('seller_id',flat=True))
print('최종 상품ROAS:', len([a for a in active if a in p]),'/',len(active))
print('최종 광고비:', len([a for a in active if a in c]),'/',len(active))
print('상품ROAS 여전히 누락:', [a for a in active if a not in p])
print('광고비 여전히 누락:', [a for a in active if a not in c])
" >> "$LOG" 2>&1

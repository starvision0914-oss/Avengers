#!/bin/bash
# 지마켓+옥션 오늘 광고비 갱신 — 11번가와 동일 패턴:
#  계정당 5분 리미트(초과 시 스킵→다음) + 스킵계정 1회 재시도(7분) + 최종실패 텔레그램.
#  계정별 전용 크롬프로필 격리(동시 11번가 크롤과 안전). 한 계정 지연이 전체를 막지 않음.
cd /home/rejoice888/Avengers/backend
LOG=/tmp/gmkt_today_orch.log
: > "$LOG"
PER_TIMEOUT=300
RETRY_TIMEOUT=420

ACCTS=$(/usr/bin/python3 -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from apps.cpc.models import CrawlerAccount as C;print(' '.join(a.login_id for a in C.objects.filter(platform='gmarket',is_active=True) if not (a.gmarket_origin_id and a.gmarket_origin_id!=a.login_id)))" 2>/dev/null)
N=$(echo $ACCTS | wc -w)
echo "[ORCH] 지마켓+옥션 오늘 광고비 ${N}계정 시작 $(date '+%F %T')" >> "$LOG"

run_one(){   # $1=account $2=timeout ; 성공=0 실패=1
  local a=$1 to=$2 tmp=/tmp/gmkt_one_${1}.log
  : > "$tmp"
  pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null
  rm -rf /tmp/gmkt_chrome_* 2>/dev/null
  rm -f /tmp/avengers_crawl_chrome_gmarket.lock
  sleep 2
  timeout "$to" /usr/bin/python3 -u -c "import crawlers.gmkt_today" "$a" >> "$tmp" 2>&1
  local rc=$?
  cat "$tmp" >> "$LOG"
  # 성공판정: 타임아웃(124) 아니고, '오늘 광고 N건' 출력(=로그인후 정상처리) 있으면 성공.
  # (광고 0건도 정상. '로그인 실패'만 있으면 미출력 → 실패)
  if [ "$rc" -ne 124 ] && grep -q "오늘 광고" "$tmp"; then
    return 0
  fi
  return 1
}

FAILED=""
i=0
for a in $ACCTS; do
  i=$((i+1))
  echo "[ORCH $i/$N] $a 시작 $(date +%H:%M:%S)" >> "$LOG"
  if run_one "$a" "$PER_TIMEOUT"; then
    echo "[ORCH $i/$N] $a ✅" >> "$LOG"
  else
    echo "[ORCH $i/$N] $a ⏭스킵(재시도예정)" >> "$LOG"
    FAILED="$FAILED $a"
  fi
done

STILL=""
if [ -n "$FAILED" ]; then
  echo "[ORCH] 2차 재시도 대상:$FAILED $(date +%H:%M:%S)" >> "$LOG"
  for a in $FAILED; do
    echo "[ORCH-R] $a 재시도 $(date +%H:%M:%S)" >> "$LOG"
    if run_one "$a" "$RETRY_TIMEOUT"; then
      echo "[ORCH-R] $a ✅재시도성공" >> "$LOG"
    else
      STILL="$STILL $a"
    fi
  done
fi

pkill -9 -f "user-data-dir=/tmp/gmkt_chrome" 2>/dev/null; rm -rf /tmp/gmkt_chrome_* 2>/dev/null
echo "[ORCH] === 완료 $(date '+%F %T') / 최종실패:[$STILL] ===" >> "$LOG"

if [ -n "$STILL" ]; then
  /usr/bin/python3 -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from apps.cpc import eleven_block_guard as g;g._send_telegram_alert('⚠️ [지마켓 오늘 광고비 갱신] 1차+재시도 후에도 실패한 계정:\n$STILL\n→ 수동 확인 필요')" 2>/dev/null
  echo "[ORCH] 텔레그램 통보 발송" >> "$LOG"
fi

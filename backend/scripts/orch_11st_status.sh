#!/bin/bash
# 11번가 판매상태 갱신 — 계정당 5분 리미트(초과 시 스킵→다음) + 스킵계정 1회 재시도 + 최종실패 텔레그램.
# 순차·사람페이싱 유지(차단 위험 없음). 한 계정 지연이 전체를 막지 않게 격리.
cd /home/rejoice888/Avengers/backend
LOG=/tmp/cron_11st_status_orch.log
: > "$LOG"
PER_TIMEOUT=300      # 1차: 계정당 5분(=1분×5회 폴링 상당)
RETRY_TIMEOUT=420    # 2차: 7분(서버 엑셀 생성 완료됐을 가능성↑)

ACCTS=$(/usr/bin/python3 -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from apps.cpc.models import CrawlerAccount as C;print(' '.join(a.login_id for a in C.objects.filter(platform='11st',is_active=True) if a.login_id!='tmxkzhfldk8'))" 2>/dev/null)
N=$(echo $ACCTS | wc -w)
echo "[ORCH] 11번가 판매상태 대상 ${N}계정 시작 $(date '+%F %T')" >> "$LOG"

run_one(){   # $1=account $2=timeout ; 성공=0 실패=1
  local a=$1 to=$2 tmp=/tmp/st_one_${1}.log
  : > "$tmp"
  timeout "$to" /usr/bin/python3 manage.py crawl_11st_products --accounts "$a" --all --force >> "$tmp" 2>&1
  local rc=$?
  cat "$tmp" >> "$LOG"
  if [ "$rc" -ne 124 ] && grep -qE "완료 .*UPSERT|성공=[1-9]" "$tmp"; then
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

# 2차 재시도(스킵계정만, 1회)
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

echo "[ORCH] === 완료 $(date '+%F %T') / 최종실패:[$STILL] ===" >> "$LOG"

# 최종 실패 계정만 텔레그램 통보
if [ -n "$STILL" ]; then
  /usr/bin/python3 -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from apps.cpc import eleven_block_guard as g;g._send_telegram_alert('⚠️ [11번가 판매상태 갱신] 1차+재시도 후에도 실패한 계정:\n$STILL\n→ 수동 확인 필요')" 2>/dev/null
  echo "[ORCH] 텔레그램 통보 발송" >> "$LOG"
fi

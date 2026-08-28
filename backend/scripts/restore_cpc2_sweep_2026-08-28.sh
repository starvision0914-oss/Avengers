#!/bin/bash
# 일회성: 2026-08-28(금) 사용자 요청으로 잠시 꺼둔 21:30 간편+일반광고 전체점검 크론을
# 월요일 새벽에 자동 복구. 복구 후 이 크론엔트리 자신도 crontab에서 제거(1회성).
TMP=$(mktemp)
crontab -l | sed 's|^#SKIP-2026-08-28-FRI: 30 21 \* \* 1-5 |30 21 * * 1-5 |' \
  | grep -v 'restore_cpc2_sweep_2026-08-28.sh' > "$TMP"
crontab "$TMP"
rm -f "$TMP"
echo "$(date '+%F %T') cpc2_full_sweep 21:30 크론 복구 완료" >> /tmp/restore_cpc2_sweep.log

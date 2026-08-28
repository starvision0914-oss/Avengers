#!/bin/bash
# 일회성: 2026-08-28(금) 저녁 사용자 요청으로 잠시 꺼둔 지마켓 광고비 관련 크론 4개를
# 다음날(토) 새벽에 자동 복구. 복구 후 이 크론엔트리 자신도 crontab에서 제거(1회성).
TMP=$(mktemp)
crontab -l | sed 's|^#SKIP-2026-08-28-EVENING: ||' \
  | grep -v 'restore_adcost_2026-08-28.sh' > "$TMP"
crontab "$TMP"
rm -f "$TMP"
echo "$(date '+%F %T') 지마켓 광고비 크론 4개 복구 완료" >> /tmp/restore_cpc2_sweep.log

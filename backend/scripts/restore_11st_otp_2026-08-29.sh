#!/bin/bash
# 일회성: 2026-08-29(토) 사용자 요청으로 일요일 12시까지 스킵해둔 11번가 OTP/쿠키 일일점검(일요일 05:20)을
# 정오에 자동 복구. 복구 후 이 크론엔트리 자신도 crontab에서 제거(1회성).
TMP=$(mktemp)
crontab -l | sed 's|^#SKIP-UNTIL-2026-08-30-NOON: ||' \
  | grep -v 'restore_11st_otp_2026-08-29.sh' > "$TMP"
crontab "$TMP"
rm -f "$TMP"
echo "$(date '+%F %T') 11번가 OTP 일요일 크론 복구 완료" >> /tmp/restore_cpc2_sweep.log

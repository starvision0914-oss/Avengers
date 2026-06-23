#!/bin/bash
# 11번가 OTP 인증 갱신 (매일 05:00) — 3배치로 분할해 크롬 누적 방지
# 배치1: 25개 / 배치2: 25개 / 배치3: 22개
# 야간 판매상태 크롤(02:00~04:33) 완료 후 실행

cd /home/rejoice888/Avengers/backend
LOG=/tmp/cron_11st_verify.log
JSON1=/tmp/11st_verify_b1.json
JSON2=/tmp/11st_verify_b2.json
JSON3=/tmp/11st_verify_b3.json

echo "$(date '+%F %T') ===== 11번가 OTP 인증 갱신 시작 =====" >> "$LOG"

_kill_chrome() {
    pkill -9 -f 'undetected_chromedriver' 2>/dev/null
    pkill -9 -f 'chromedriver' 2>/dev/null
    pkill -9 -f 'chrome --' 2>/dev/null
    sleep 5
}

BATCH1="rejoice666,tmxkqlwus1,tmxkqlwus,tmxkql27,rejoice41,rejoice42,rejoice43,starvis7944,rejoice567,rejoice1233,rejoice678,starvis7943,starvis7941,rejoice7941,rejoice999,rejoice7943,rejoice7944,rejoice1232,rejoice1231,tmxkqlwus11,tmxkqlwus12,tmxkqlwus13,tmxkqlwus14,tmxkqlwus2,tmxkqlwus3"
BATCH2="tmxkzhfldk6,tmxkzhfldk7,tmxkzhfldk8,tmxkzjavjsl777,tmxkzjavjsl888,tmxkzjavjsl999,jinag7460,starvis7942,starvisi,rejoice888,rejoice777,rejoice7942,rejoice1234,i92372664,tmxkqhrhksth000,tmxk26,tmxk28,starvis8942,dlrmsgh012,rejoice44,dlrmsgh7942,tmxkzjavjsl666,tmxk24,tmxkql234,tmxkfkdlvm333"
BATCH3="tmxkdnpdlqm8,tmxkzhfldk9,tmxkql25,tmxkql22,rejoice321,rejoice119,rejoice794,dlrmsgh011,dlrmsgh013,dlrmsgh014,dlrmsgh7941,dlrmsgh7943,dlrmsgh7944,jinag7461,jinag7462,jinag7463,tmxkrmsh55,rejoice345,tmxkql235,tmxkql237,tmxkql238,tmxkql21"

# 배치1
echo "$(date '+%F %T') [1/3] 배치1(25개) 시작" >> "$LOG"
_kill_chrome
/usr/bin/python3 manage.py verify_11st_logins --only "$BATCH1" --cooldown 5 --out "$JSON1" >> "$LOG" 2>&1
echo "$(date '+%F %T') [1/3] 배치1 완료" >> "$LOG"

# 배치2
echo "$(date '+%F %T') [2/3] 배치2(25개) 시작" >> "$LOG"
_kill_chrome
/usr/bin/python3 manage.py verify_11st_logins --only "$BATCH2" --cooldown 5 --out "$JSON2" >> "$LOG" 2>&1
echo "$(date '+%F %T') [2/3] 배치2 완료" >> "$LOG"

# 배치3
echo "$(date '+%F %T') [3/3] 배치3(22개) 시작" >> "$LOG"
_kill_chrome
/usr/bin/python3 manage.py verify_11st_logins --only "$BATCH3" --cooldown 5 --out "$JSON3" >> "$LOG" 2>&1
echo "$(date '+%F %T') [3/3] 배치3 완료" >> "$LOG"

# 전체 결과 집계 + 텔레그램 통보
/usr/bin/python3 - <<'PYEOF' >> "$LOG" 2>&1
import json, os

totals = {'success': 0, 'failed': 0, 'otp_required': 0, 'error': 0}
failed_list = []

for f in ['/tmp/11st_verify_b1.json', '/tmp/11st_verify_b2.json', '/tmp/11st_verify_b3.json']:
    try:
        data = json.loads(open(f).read())
        for r in data:
            s = r.get('status', 'error')
            totals[s] = totals.get(s, 0) + 1
            if s != 'success':
                failed_list.append(f'{r["login_id"]}({s})')
    except Exception as e:
        print(f'[집계] {f} 읽기실패: {e}')

total = sum(totals.values())
msg = (
    f'✅ [11번가 OTP 인증 갱신 완료]\n'
    f'성공: {totals["success"]}/{total}\n'
    f'실패: {totals["failed"]} | OTP미완: {totals["otp_required"]} | 오류: {totals["error"]}'
)
if failed_list:
    msg += '\n\n실패계정:\n' + '\n'.join(failed_list)

print(msg)

import django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.cpc.eleven_block_guard import _send_telegram_alert
_send_telegram_alert(msg)
PYEOF

echo "$(date '+%F %T') ===== 11번가 OTP 인증 갱신 완료 =====" >> "$LOG"

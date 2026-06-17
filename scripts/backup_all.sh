#!/bin/bash
# Avengers 전체 백업 — 매일 23:00. (Claude 계정 변경 대비: 코드·문서·메모리는 GitHub, DB는 서버 보관)
#  1) MySQL Avengers 덤프 → ~/backups (gzip, 7일 보관)
#  2) Claude 메모리 → 레포 docs/claude_memory/ 동기화
#  3) git add/commit/push (코드+문서+메모리). DB덤프는 용량(>2GB)으로 git 제외.
set -u
TS=$(date +%Y%m%d_%H%M%S)
DAY=$(date +%Y-%m-%d)
BK=/home/rejoice888/backups
REPO=/home/rejoice888/Avengers
MEM=/home/rejoice888/.claude/projects/-home-rejoice888/memory
LOG=/tmp/backup_all.log
mkdir -p "$BK"
echo "$(date '+%F %T') ===== 백업 시작 =====" >> "$LOG"

# 1) DB 덤프 (Django settings에서 접속정보 추출)
cd "$REPO/backend"
read DBNAME DBUSER DBPASS DBHOST DBPORT < <(/usr/bin/python3 -c "
import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup()
from django.conf import settings as s;d=s.DATABASES['default']
print(d['NAME'],d['USER'],d.get('PASSWORD',''),d.get('HOST','localhost') or 'localhost',d.get('PORT','') or '3306')
" 2>/dev/null)
if [ -n "${DBNAME:-}" ]; then
  mysqldump -h"$DBHOST" -P"$DBPORT" -u"$DBUSER" -p"$DBPASS" --single-transaction --quick --routines "$DBNAME" 2>>"$LOG" | gzip > "$BK/avengers_db_${TS}.sql.gz"
  SZ=$(du -h "$BK/avengers_db_${TS}.sql.gz" | cut -f1)
  echo "$(date '+%F %T') DB덤프 완료: $SZ" >> "$LOG"
  ls -1t "$BK"/avengers_db_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -f   # 7일분만 유지
else
  echo "$(date '+%F %T') DB접속정보 추출 실패 — 덤프 건너뜀" >> "$LOG"
fi

# 2) 메모리 → 레포 동기화 (GitHub로 보존)
mkdir -p "$REPO/docs/claude_memory"
if [ -d "$MEM" ]; then cp -f "$MEM"/*.md "$REPO/docs/claude_memory/" 2>/dev/null; fi

# 3) git commit + push (코드+문서+메모리). DB덤프는 .gitignore로 제외.
cd "$REPO"
grep -q '^backups/' .gitignore 2>/dev/null || echo 'backups/' >> .gitignore
grep -q 'sql.gz' .gitignore 2>/dev/null || echo '*.sql.gz' >> .gitignore
git add -A 2>>"$LOG"
if ! git diff --cached --quiet 2>/dev/null; then
  git -c user.name='avengers-backup' -c user.email='backup@avengers.local' commit -m "auto backup ${DAY}" >> "$LOG" 2>&1
  git push origin main >> "$LOG" 2>&1 && echo "$(date '+%F %T') git push 완료" >> "$LOG" || echo "$(date '+%F %T') git push 실패" >> "$LOG"
else
  echo "$(date '+%F %T') 변경 없음 — 커밋 생략" >> "$LOG"
fi
echo "$(date '+%F %T') ===== 백업 종료 =====" >> "$LOG"

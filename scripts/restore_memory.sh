#!/bin/bash
# Claude 메모리 복원 — GitHub 백업(docs/claude_memory)을 로컬 Claude 메모리 폴더로 복사.
# 새 PC/새 계정/초기화 후 메모리가 없을 때 1회 실행하면 새 세션이 인식한다.
# 사용: bash scripts/restore_memory.sh
SRC="$(cd "$(dirname "$0")/.." && pwd)/docs/claude_memory"
DST="$HOME/.claude/projects/-home-rejoice888/memory"
mkdir -p "$DST"
if [ -d "$SRC" ]; then
  cp -f "$SRC"/*.md "$DST"/ 2>/dev/null
  echo "✅ 복원 완료: $(ls "$DST"/*.md 2>/dev/null | wc -l)개 메모리 → $DST"
  echo "이제 새 Claude 세션을 시작하면 MEMORY.md가 자동 로드됩니다."
  echo "추가로 새 세션에 'docs/HANDOVER.md 읽고 이어서 작업해줘'라고 하면 전체 맥락을 파악합니다."
else
  echo "❌ $SRC 없음 — 먼저 git clone/pull 하세요."
fi

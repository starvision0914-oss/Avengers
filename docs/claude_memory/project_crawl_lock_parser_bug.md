---
name: project_crawl_lock_parser_bug
description: views._crawl_lock_busy가 락(pid|name|time)을 통째 int변환해 멀쩡한 락 삭제하던 버그 (2026-06-11 수정)
metadata: 
  node_type: memory
  type: project
  originSessionId: b822c371-0117-4ceb-8494-a5dc15123c58
---

크롤 락 파일 `/tmp/avengers_crawl_chrome.lock` 형식은 `pid|name|time`(eleven_block_guard.acquire_global_lock이 씀, bash cron은 cut -f1로 pid 읽음).

**버그**: apps/cpc/views.py `_crawl_lock_busy()`가 파일을 통째로 `int(content)` 변환 → `int('1124006|광고비|...')` ValueError → pid=0 → 락을 '손상'으로 보고 **os.remove로 삭제** + running=False 반환.
**증상**: St11 대시보드가 5초마다 `/cpc/crawler/eleven-cost/status/` 폴링 → 매번 실행 중인 크롤의 락을 지워버림. 결과 (1)대시보드가 크롤을 '실행 안 함'으로 표시 → crawlRunning=false → 데이터 자동갱신(10s) 안 켜짐, (2)동시실행 가드 무력화 → 11st 크롤 도중 다른 크롤이 동시 시작 가능 = **IP 차단 위험**.
**수정(2026-06-11)**: `raw.split('|')[0]`로 첫 필드만 pid 파싱(바06-11 bare-pid도 호환). 수정 후 _crawl_lock_busy=(pid,True) 유지, 락 안 지워짐 확인.

관련: St11Dashboard.tsx에 crawlRunning이면 10초마다 refresh()하는 자동갱신 추가(2026-06-11). 락 분리는 [[project_platform_lock_split]] [[project_11st_ip_block_prevention]]. 별개로 지마켓 크롤이 release_global_lock을 platform 인자 없이(기본11st) 호출해 11st 락 지우는 의심 정황 있음 — 추후 확인 필요.

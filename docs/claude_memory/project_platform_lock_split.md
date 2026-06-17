---
name: project_platform_lock_split
description: 크롤러 락을 플랫폼별로 분리 — 11st ∥ gmarket 동시 실행 가능(2026-06-11)
metadata: 
  node_type: memory
  type: project
  originSessionId: 354070d6-c8cd-4591-8ad8-ac8c18636875
---

2026-06-11 구현. 기존엔 모든 크롤러가 전역 크롬 락 1개(`/tmp/avengers_crawl_chrome.lock`)를 공유해 11번가/지마켓이 서로를 막았다(직렬). 쇼핑몰 5개 확장 + 동시 크롤 목적으로 **플랫폼별 락**으로 분리.

**eleven_block_guard.py 일반화**: `preflight`, `acquire_global_lock`, `release_global_lock`, `is_blocked`, `set_blocked`, `clear_block`, `live_reachable` 에 `platform='11st'` 인자 추가(기본값이라 11st 호출 전부 하위호환 무변경). 헬퍼: `_lock_path(platform)`, `_block_file(platform)`, `_REACH_URL`.
- 11st 락 = `/tmp/avengers_crawl_chrome.lock` (레거시 경로 유지 → 11st bash 크론 호환)
- gmarket 락 = `/tmp/avengers_crawl_chrome_gmarket.lock`
- 차단파일도 분리: `avengers_11st_blocked_until` / `avengers_gmarket_blocked_until`
- 도달성: 11st→11st.co.kr, gmarket→gmarket.co.kr (이전엔 지마켓도 11st.co.kr로 점검하던 결합버그 해소)

**바꾼 호출처**: gmarket_cost_crawler/gmarket_product_crawler/gmarket_adgroup_crawler 의 preflight·release·is_blocked → `platform='gmarket'`. bash 크론 5개(cron_gmarket_cost/cron_gmarket_ai/cron_ai_on/cron_ai_off/cron_cpc2_on) LOCKFILE → gmarket 락. (gmarket_crawler.py 스냅샷은 guard 안 쓰고 bash 락만 의존.)

검증: 11st 락 잡은 채 gmarket 락 동시 획득 True/True → 동시 실행 가능 확인.

**메모리**: 분리 자체는 비용 0(파일경로일 뿐). 메모리는 실제 동시 크롬 실행시에만(크롬 1개 ~2.4GB). 호스트 4코어/15GB → 동시 2~3플랫폼 쾌적, 5개 전부 동시는 한계(RAM 증설 권장). 새 쇼핑몰은 _REACH_URL에 추가 + 크롤러별 platform 지정.

관련: [[project_11st_ip_block_prevention]] (동일 플랫폼 내부는 여전히 직렬), [[project_gmarket_esm_groups]].

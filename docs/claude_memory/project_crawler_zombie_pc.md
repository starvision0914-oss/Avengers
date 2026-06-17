---
name: project_crawler_zombie_pc
description: "크롤러 좀비PC — 고아 Xvfb/chrome 누적으로 크롤 실패, 리퍼+atexit/SIGTERM로 해결"
metadata: 
  node_type: memory
  type: project
  originSessionId: 34b8a2c1-a725-49d1-836d-7e26a001dc32
---

크롤 프로세스가 timeout(SIGTERM)/크래시로 죽으면 `crawlers/browser.py`의 Xvfb·chrome·chromedriver가 **고아(PPID=1)로 영구 잔존**('좀비PC'). `run_all_accounts` finally의 `stop_display()`/`driver.quit()`는 정상종료 시에만 실행되고, `create_driver(kill_existing=False)`는 잔여 chrome을 안 죽임 → 누적(한때 Xvfb 18개·chrome 38개 ≈ 3.5GB)되어 디스플레이/메모리 고갈로 크롤이 응답이상·실패.

**해결(2026-06-12):** browser.py에 ① `_reap_orphans()` = PPID==1 인 Xvfb/chromedriver/chrome만 SIGKILL(실행중 크롤은 부모살아있어 보존), ② `_register_cleanup()` = atexit+SIGTERM 핸들러로 timeout/크래시에도 stop_display 보장. 둘 다 `create_driver()` 진입 시 호출(웹서버는 create_driver 미사용이라 영향 없음).

**Why:** 고아만(PPID=1) 죽여야 동시 크롤 안전. timeout 300 manage.py 패턴이 SIGTERM으로 죽이므로 SIGTERM 핸들러가 핵심.
**How to apply:** 좀비 의심 시 `ps -eo pid,ppid,comm | awk '$2==1 && /Xvfb|chrome/'`로 고아 확인. 수동정리는 활성 크롤(manage.py crawl) 트리 보호 필수. [[project_gmarket_adcost_source]] [[feedback_crawling_rule]]

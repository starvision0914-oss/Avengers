---
name: project_gmarket_keyword_lock_gotcha
description: 지마켓 키워드 크롤(crawl_gmarket_keywords) 수동 실행 시 수동 락 만들면 preflight self-오판으로 스킵됨
metadata: 
  node_type: memory
  type: project
  originSessionId: 4b81a2de-3c94-48d2-a767-9d7a7a3fd4ae
---

`crawl_gmarket_keywords`는 내부에서 `guard.preflight(platform='gmarket')`가 **전역락 `/tmp/avengers_crawl_chrome_gmarket.lock`을 스스로 획득**한다.

**함정:** 수동 실행할 때 `echo $$ > /tmp/avengers_crawl_chrome_gmarket.lock` 으로 락을 미리 써넣으면, preflight가 그 락(살아있는 래퍼 PID)을 "같은 플랫폼 다른 크롤 실행 중"으로 오판해 **⏭️ 스킵**한다. (광고비 cost 크롤은 guard.preflight를 안 써서 수동락 필요하지만, 키워드는 정반대)

**How to apply:** 키워드 크롤은 **수동 락 만들지 말고** `nohup python3 manage.py crawl_gmarket_keywords ...` 만 실행 — guard가 락 관리. 강제 -9 kill 시 guard 락/`avengers_gmarket_blocked_until`이 스테일로 남을 수 있으니 재실행 전 둘 다 삭제. [[project_gmarket_keyword_report]] [[project_platform_lock_split]] [[project_gmarket_captcha_login]]

---
name: project-wordpress-backup-gap
description: 워드프레스(오산홈페이지) DB가 자동 일일백업 대상에서 빠져있던 것을 발견·수정(2026-07-20)
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c0700b1-ffe8-412d-987e-6c8fdb9241fa
---

`backup_all.sh`(매일 23:00 cron)는 원래 Avengers DB만 백업했고, 워드프레스(오산홈페이지, DB명 `homepage_wp`)는 자동백업 대상이 아니었다. 마지막 수동 백업이 2026-07-13이었고, 그 이후(코스피뉴스 200개, 생활정보 다수, 이 날 발행한 블로그 글 22개 포함) 전부 무방비 상태였다는 것을 사용자가 컴퓨터 재부팅 전 백업 확인을 요청하면서 발견했다.

**조치**: `backup_all.sh`에 워드프레스 DB 덤프 단계 추가(2026-07-20) — `wp-config.php`에서 DB_NAME/USER/PASSWORD/HOST를 grep으로 파싱해 `~/backups/homepage_db_*.sql.gz`로 저장, 7일 로테이션. 재부팅 직전 수동 백업 1회도 즉시 실행해둠(`homepage_db_20260720_114558.sql.gz`).

**Why:** 일반 재부팅 자체는 데이터를 지우지 않지만(디스크의 MySQL 데이터는 그대로 유지), 백업은 재부팅과 무관하게 사고 대비용 안전장치라 별도로 챙겨야 했다. Avengers DB는 이미 매일 정상 백업+GitHub push 중이었음(git push까지 확인, 실패 시 텔레그램 알림 기존에 구축돼 있음).

**How to apply**: 새 DB나 서비스(예: gnuboard6 등)를 추가로 구축할 때는 `backup_all.sh`에 자동으로 포함되지 않으므로, 백업 대상에 넣을지 매번 확인할 것. 관련: [[project_osan_homepage]], [[project_server_reboot_2026-07-13]]

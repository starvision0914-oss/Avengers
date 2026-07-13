---
name: project_server_reboot_2026-07-13
description: 서버 컴퓨터(192.168.45.100) 재부팅 예정/실시 기록 및 재부팅 후 확인사항
metadata: 
  node_type: memory
  type: project
  originSessionId: dfbbf0b2-5cdd-4ddb-bc58-743ed7bf3711
---

2026-07-13 사용자가 서버 컴퓨터(192.168.45.100) 재부팅 예정. 재부팅 시점에 진행 중이던 크롤: `crawl_gmarket_adcost`(지마켓 광고비), `crawl_11st_cost --force --focused`(11번가 광고비) — 강제 종료됨. [[project_11st_transient_fails]]에 따라 수집실패는 대부분 다음 회차 자동회복되는 일시적 현상이라 데이터 손상 우려는 낮음.

**재부팅 후 확인할 것:**
- PM2: `pm2-rejoice888.service`가 systemd에 enabled 등록되어 있어 재부팅 시 자동 시작됨(`pm2 list`로 avengers-backend/frontend/sms-poller/telegram-bot/x11vnc/xvfb-vnc 6개 프로세스 다 살아있는지 확인)
- crontab: 사용자 crontab이라 재부팅과 무관하게 유지됨(파일시스템에 저장), 별도 재등록 불필요
- adb(문자 수신): USB 재연결 필요할 수 있음 — adb_watchdog.sh가 5분마다 자동감시하지만, 물리적 USB 케이블은 재부팅 후 재인식 안 될 수 있으니 SMS/OTP 수신 안 되면 USB 재꽂기 확인
- VNC(x11vnc/xvfb-vnc): PM2로 관리되니 자동 재기동되나, 실제 화면표시 필요한 크롤(지마켓 캡차 등)이 있다면 VNC 접속(192.168.45.100:5905 또는 Tailscale 100.114.20.52:5905)해서 화면 정상 뜨는지 1회 확인 권장
- 좀비 프로세스([[project_crawler_zombie_pc]])는 재부팅으로 자연히 정리됨(오히려 긍정적 효과)

관련: [[project_server_ip]], [[project_crawler_zombie_pc]], [[project_11st_transient_fails]]

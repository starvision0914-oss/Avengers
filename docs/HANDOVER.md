# Avengers 핸드오버 (Claude 계정 변경 대비) — 2026-06-17

> 새 Claude 계정/세션이 이어받을 수 있도록 시스템·작업·지식을 정리. 메모리 원본은 `docs/claude_memory/`.

## 1. 시스템 개요
- 서버 단일호스트 **192.168.45.100** (DB·백엔드·프론트 동일)
- 백엔드: Django5+DRF, 포트 8010, `/usr/bin/python3 manage.py`, MySQL **Avengers** 스키마 (~2.4GB)
- 프론트: React18+Vite, 포트 5173 (pm2 `avengers-frontend` = vite dev/HMR)
- pm2: avengers-backend / avengers-frontend / avengers-sms-poller / avengers-telegram-bot
- 로그인 admin/admin123. GitHub: starvision0914-oss/Avengers (main)
- 코드 수정 후: 백엔드는 `pm2 restart avengers-backend`, 프론트는 HMR(새로고침)

## 2. 이번 세션 핵심 작업 (2026-06-16~17)

### 지마켓 판매불가 탐지 (해결완료)
- 문제: 판매불가 상품이 goods/search API에서 제외돼 마지막 "판매중"으로 박제됨(적자리스트 77.6%가 실은 판매불가).
- 해결: **"계정 최신크롤보다 synced_at 12h+ 이전 = 누락 = 판매불가"** 규칙.
  - 실시간: `apps/cpc/views.py::_gmarket_realsales` (비고 계산시 자동)
  - DB영구반영: `manage.py mark_gmarket_unavailable` (매일 05:30 cron `cron_gmarket_mark_unavailable.sh`)
- 검증: 플래깅 중 1회누락(<24h)=0%, 95%가 4일+ 연속누락 = 진짜 드롭.

### 지마켓 광고효율 진단엔진 (신규)
- `manage.py gmarket_ad_diagnose` (읽기전용): 실ROAS+11번가원가 손익분기로 승자/회색/적자/무전환/판매불가 분류.
- 매일 09:30 cron `cron_gmarket_ad_diagnose.sh` → 텔레그램 발송.

### 광고 ON/OFF 크롤러 로그인 수정
- 원인: ad.esmplus.com 로그인에 `rdoSiteSelect` 라디오 누락 → "로그인 실패". 기존 OFF크론 비활성 이유.
- 수정: cpc2/AI 제어기가 `gmarket_crawler._full_login`(rdoSiteSelect+쿠키재사용) 사용.
- 신규: 일반광고(파워클릭) 제어기 `gmarket_cpc1_control_crawler` + `crawl_gmarket_cpc1`.
- guard 전역락(wait=True) 추가로 크롤 충돌 방지. alert("다른광고주") 처리 추가.
- ⚠️ 광고 OFF/ON 크론 스크립트(cron_gmarket_ads_off/cpc_on/ai_on)는 작성됐으나 **미등록**(계정전체 OFF만 가능, per-product 미지원).

### 상품크롤 스케줄 02시로 변경 (기존 03시)

### 상품명 변경 프롬프트 3종
- 11번가: `OwnerclanElevenPromptModal`, 지마켓: `OwnerclanGmarketPromptModal`, 옥션: `OwnerclanAuctionPromptModal`(신규)
- 버튼: 예비상품(/ownerclan)·상품가공(/product-processing) 상단 툴바.
- 단순·매출기준 공식: [대표검색어][규격/수량][속성][타겟/용도] 35~38자.

## 3. 딥리서치 결과 (2026 광고센터)
- 광고비 9,425만/전환 2.22억/ROAS 235%. CTR 0.22%(매우낮음).
- **승자(ROAS≥400) 광고비10%가 전환92% / 적자(≤100) 광고비82%가 전환1%** — 극단 양극화.
- 진짜 손익분기 ROAS **~450~490%**(11번가 원가 매칭, 평균마진22%). ROAS100은 적자기준 너무 낮음.
- CPC 76%(ROAS228·CPC600) / AI 24%(ROAS258·CPC379) → **AI 효율우위인데 저활용**.
- 클릭多·무전환 중 90%(2,316만)는 실매출0=순낭비.

## 4. 신규 cron (crontab, ~/cron_backups/에 백업본)
```
0 2  * * *  cron_gmarket_products.sh            # 상품크롤(02시, 기존03→02)
30 5 * * *  cron_gmarket_mark_unavailable.sh    # 판매불가 DB반영
0 8  * * *  cron_gmarket_ad_report_kw.sh        # 광고비+키워드
30 9 * * *  cron_gmarket_ad_diagnose.sh         # 광고효율진단+텔레그램
0 23 * * *  backup_all.sh                       # 전체백업(DB+git)
```

## 5. 미완 과제
- per-product 광고 OFF 크롤러(현재 계정전체만). 무전환 40개·적자 컷 자동화 필요.
- 키워드 전체수집(현재 ROAS≥200 승자만 수집 → 적자 키워드 사각).
- 판매불가 실제 사유 수집(ESM 안전센터/상품상세 — 브라우저 불안정으로 보류).
- 손익분기 기준 적자 자동컷(실매출 보정+단계적).

## 6. 백업 체계
- `scripts/backup_all.sh` 매일 23:00: DB덤프(~/backups, gzip 7일) + 메모리→docs/claude_memory + git push.
- DB(2.4GB)는 용량상 GitHub 제외, 서버 ~/backups 보관(서버는 Claude계정 무관).
- 새 계정에서 컨텍스트 복원: 이 문서 + docs/claude_memory/*.md 읽기.

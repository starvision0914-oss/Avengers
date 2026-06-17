# ai100 기능 정리 (어벤저스 구현 참조용)

> 출처: `betona1/ai100` (로컬 `/tmp/ai100`). 메인 앱 = `viewer/gmarket_cpc/` (Django + React/Vite).
> 목적: 어벤저스 대시보드·서버에 이식할 기능 카탈로그 + 우선순위 로드맵.
> 규모: 백엔드 서비스 26개 · 크롤러 24개 · 프론트 페이지 35개 · 관리커맨드 40개 · 모델 64개.

---

## 1. 마켓 커버리지 & 크롤러

### 1-1. 광고비/성과 크롤러
| 크롤러 | 마켓 | 수집 내용 |
|--------|------|-----------|
| `gmarket_cost` | G마켓 | 일일 광고비 + 예치금 잔액 |
| `gmarket_ai` / `gmarket_ai_control` | G마켓 | AI광고 집행액 / ON·OFF 제어 |
| `gmarket_cpc_status` / `gmarket_cpc2_control` | G마켓 | CPC 광고상태 / 간편광고 제어 |
| `gmarket_cpp_control` | G마켓 | 프라임 입찰 관리 |
| `gmarket_seller_grade` | G마켓 | 셀러등급·최대등록수·승인상태 |
| `st11_cost` | 11번가 | 광고비 XLS (셀러포인트/캐시) |
| `st11_adoffice` | 11번가 | Adoffice AI캠페인 (병렬 크롬) |
| `st11_ai_control` | 11번가 | AI광고 스케줄 ON·OFF (공휴일 자동스킵) |
| `st11_seller_grade` | 11번가 | 셀러등급 |

### 1-2. 부가세(VAT) 크롤러 ⭐어벤저스 미구현
`gmarket_vat` · `st11_vat` · `coupang_vat` · `auction_vat` · `smartstore_vat` · `ably_vat` · `cafe24_vat` · `toss_vat` (+ ESM)
→ 마켓별 부가세 자료 자동수집 → `tax` DB 통합조회

### 1-3. Lohas(로하스/대량상품) 크롤러
`lohas_daily_stats`(일매출), `lohas_session_monitor`(세션풀 감시), `lohas_recrawl_manager`(병렬 재크롤)

### 1-4. 공통 인프라
`browser.py`(UC+Xvfb non-headless), `config.py`, `utils.py`

---

## 2. 백엔드 기능 서비스 (`backend/cpc/*_service.py`)

### 2-1. 광고/성과/리포트
- `services.py` (2100줄+) — CPC/AI/LCE 일·시계열·기간 요약 (G마켓+11번가+다마켓)
- `crawler_service` — 계정 CRUD + 작업/로그 관리 (fail_count, crawling_status)
- `gmarket_rank` ⭐ — G마켓 검색순위 추적 + 키워드 이력
- `telegram` / `tg_report` — 자동발송 스케줄(5분/시간/15분) + 야간 모니터링

### 2-2. 세무
- `vat` ⭐ — 11개 마켓 부가세 + 사업자 통합 조회 (어벤저스 최대 공백)

### 2-3. 상품/마켓 연동
- `eleven` / `eleven_product` — 11번가 셀러관리 + 상품등록
- `smartstore` / `smartstore_product` ⭐ — 스마트스토어 카테고리·속성 매핑
- `ownerclan_product` — 오너클랜 대량업로드 + 이미지

### 2-4. Lohas 대량상품 자동화
- `lohas_product`(LCP코드 상품DB), `lohas_edit`(원격워커 일괄수정), `lohas_verify`(이미지검수),
  `lohas_worker`(원격워커 큐+PID추적), `lohas_keyword_upload`(키워드업로드+금지어필터),
  `lohas_stats`(.xls 파싱 매출집계), `lohas_bid_crawl`(입찰분석)

### 2-5. AI
- `keyword_ai` ⭐ — Claude API 기반 상품 키워드 추천

### 2-6. 협업/운영 도구 (어벤저스 일부 보유)
- `board`(게시판), `chat`(실시간채팅), `todo`/`todo_auth`(칸반)
- `email`(IMAP/SMTP 14계정), `email_classify` ⭐(AI 분류), `email_urgent` ⭐(긴급탐지)

### 2-7. 인프라
- `hub` ⭐ — 분산 크롤러 서버 관리(SSH 프로비저닝·크롬버전동기화·원격실행·헬스체크)
- `tester` ⭐ — 4-method 로그인 테스터(Selenium/Playwright/Cookie/httpx + 2FA감지)

---

## 3. 프론트 페이지 (35개)

### 3-1. 통합/매출 대시보드 ⭐대부분 미구현
`OverviewDashboard`(전마켓 합산·도넛) · `SalesOnlyDashboard`(매출/원가/순익) · `BestProductsDashboard`(베스트상품)

### 3-2. 마켓별 대시보드
`CpcDashboard`(G마켓 메인) · `St11Dashboard` · `SmartStoreDashboard` · `CoupangDashboard` ⭐ · `AuctionDashboard` ⭐ · `AblyDashboard` ⭐ · `OwnerClanDashboard`

### 3-3. 분석/순위/키워드 ⭐미구현
`GmarketAnalyticsPage` · `St11AnalyticsPage` · `GmarketRankPage` · `GmarketKeywordTool` · `KeywordTool` · `NaverRankPage` · `NaverTermsPage` · `NaverExtDownloadPage`

### 3-4. 세무 ⭐
`VatPage` (11개 마켓 부가세)

### 3-5. 상품관리
`ElevenProductsPage` · `SmartStoreProductsPage` · `OwnerClanProductsPage` · `LohasProductsPage` · `LohasProductDetailPage` · `LohasDailyDashboard` · `LohasTool`

### 3-6. 크롤러 운영 ⭐미구현
`CrawlerHubPage`(분산서버) · `CrawlerTesterPage`(로그인테스터) · `RecrawlManagerPage`(스트리밍 재크롤) · `CrawlerPage`

### 3-7. 협업/기타 (어벤저스 보유)
`EmailPage` · `SmsPage` · `TodoPage` · `BoardPage` · `InstallHelperPage`

---

## 4. AI / 자동화 레이어 ⭐어벤저스 미구현 (Node.js, 최상위)
- `agents/claudeAgent.js` — Claude API 래퍼
- `agents/productAgent.js` — 상품명 생성
- `orchestrator/main.js` — `runFlow()` 상품생성 워크플로 오케스트레이션
- `skills/smartstoreUpload.js` — 스마트스토어 자동 업로드 스킬

---

## 5. 인프라 / 운영

### 5-1. 멀티 DB 구조 ⭐ (어벤저스는 단일 DB)
- `ads`(메인: 광고비·크롤러·이메일·SMS·투두·게시판)
- `joacham`(주문: orders_order — 매출/손익 계산용, 읽기전용)
- `tax`(부가세: 11개 마켓)
- `sms2`(문자: MariaDB Docker 3307)

### 5-2. SMS 시스템 (어벤저스 보유, ai100은 v2 확장)
- Android 앱 ↔ 서버 (heartbeat 기반), Docker 8010 수신/발송 API
- v2: 연락처 그룹 + 대량발송 + 엑셀 업로드 ⭐어벤저스 미구현

### 5-3. 텔레그램
자동발송 모드(수동/변동감지15분/시간별/스케줄) + matplotlib 그래프 + 야간 모니터링

### 5-4. 스케줄/락
APScheduler + 관리커맨드(40개) + flock 동시실행 방지 + cron(셀러등급 월1회)

### 5-5. 확장 프로그램 ⭐어벤저스 미구현
`gmarket_ext`(검색결과 HTML 캡처→순위), Naver/Lohas 확장

---

## 6. 어벤저스 대비 격차 & 우선순위 로드맵

> ⭐ = 어벤저스 미구현. 어벤저스가 이미 가진 것: 채팅·투두·이메일뷰어·문자(OTP)·텔레그램·판매기록(수동)·스피드고·상품업로드·로또.

### Phase 0 — 보안 (선행)
- GitHub 토큰 회수+환경변수화, `password_enc` 평문→Fernet 암호화

### Phase 1 — 즉시 가치 (진행중/완료)
- ✅ **통합 Overview 대시보드** (G마켓+11번가 합산) — 2026-06-06 1차 완료
- 로그인 테스터(4-method)

### Phase 2 — 세무·손익
- **부가세(VAT) 모듈** (vat_service + crawl_*_vat + VatPage) — 최대 공백
- 주문DB 연동 자동 손익(LCE)

### Phase 3 — 마켓 확장
- 쿠팡/스마트스토어/옥션/에이블리 크롤러 + 대시보드

### Phase 4 — 고도화
- Recrawl 매니저(스트리밍) / 키워드AI(Claude) / 순위추적+크롬확장 / 분산 크롤러 허브 / AI 오케스트레이터

---

## 7. 참조 경로
- ai100 로컬: `/tmp/ai100/` (클론: `git clone https://<token>@github.com/betona1/ai100.git /tmp/ai100`)
- 크롤러: `/tmp/ai100/viewer/gmarket_cpc/crawlers/`
- 백엔드: `/tmp/ai100/viewer/gmarket_cpc/backend/cpc/`
- 프론트: `/tmp/ai100/viewer/gmarket_cpc/frontend/src/`
- 문서: `/tmp/ai100/viewer/gmarket_cpc/docs/` (SMS_MODULE.md, SMS_SERVER_GUIDE.md, lohas_keyword_criteria.md)

_작성: 2026-06-06 (어벤저스 docs/ai100_reference.md)_

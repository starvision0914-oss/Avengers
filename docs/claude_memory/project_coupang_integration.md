---
name: project_coupang_integration
description: 쿠팡 연동 구축 현황 — 오픈API(주문/상품) + 부가세크롤러 + 상품명 최적화 프롬프트 2종
metadata: 
  node_type: memory
  type: project
  originSessionId: 65854cbc-8aa2-4568-95c3-193c08d99126
---

## 배경 (2026-07-03 하루 만에 구축)
사용자가 "쿠팡 전체적으로 구현해줘" 요청 → ai100(betona1/ai100) 참조했으나 ai100엔 부가세(VAT)
크롤러만 있고 상품/주문/광고는 없어서 새로 설계. "아이디/비번만 넣으면 세팅"이 목표였는데,
브라우저 로그인 자동화(Selenium)는 쿠팡 Akamai 봇탐지에 걸려 반복 실패 → **정식 오픈API(Wing
Open API, Access Key+Secret Key 방식)로 전환**해서 안정화 완료.

## 앱 구조
- `apps/coupang/` (신규 앱, INSTALLED_APPS 등록됨)
- `CoupangAccount`: login_id/login_pw(브라우저용) + vendor_id/access_key/secret_key(오픈API용) 둘 다 보유
- `CoupangVatSales`: 부가세신고 매출(판매자윙/로켓그로스), 브라우저크롤 방식
- `CoupangOrder`: 오픈API ordersheets 결과(주문/매출 단위)
- `CoupangProduct`: 오픈API seller-products 결과(등록상품)
- `crawlers/coupang_crawler.py`: Wing 로그인(Keycloak OAuth, xdotool 클립보드붙여넣기)
- `apps/coupang/services.py`: 오픈API HMAC 클라이언트

## 오픈API 핵심 발견사항 (실측, 2026-07-03)
- **HMAC 서명 형식**: `message = datetime+method+path+query` — **query에 '?' 포함하면 401
  "Invalid signature"**. '?' 없이 조합해야 정상(공식문서와 다름, 반드시 이 형식 유지).
- **datetime은 UTC**(`time.gmtime()`) 필수 — 서버 로컬시간(KST) 쓰면 "signature expired" 에러.
- **IP 화이트리스트는 계정(vendor)별로 개별 등록 필요** — 서버 공인IP `218.50.211.173`을
  각 셀러의 Wing "오픈API 관리"에서 등록해야 함. 등록 후 반영까지 몇 분 소요.
- **5개 상태(ACCEPT/INSTRUCT/DEPARTURE/DELIVERING/FINAL_DELIVERY) 연속조회시 429 발생** →
  0.3초 딜레이 추가함. 주문은 이 5개 상태를 각각 조회해야 전체가 잡힘(한 상태=한 시점 주문만).
- **ordersheets 기간제한**: 약 31일 단위로 분할 조회 필요.
- API 매출(orderPrice, 수수료 차감 전 총액)과 매출페이지(SalesRecord, 수수료 차감 후 정산액)는
  차이 남 — 정상. **세무상 매출 인식은 API쪽(총액) 기준이 맞음**(마켓수수료는 별도 비용처리).

## 등록 완료 계정 (7개, 2026-07-03)
rejoice234(유진오피스)·rejoice567(유진쇼핑몰)·rejoice678(유진문구)·rejoice999(유진스타일)·
dlrmsgh012·rejoice666·rejoice444 — 전부 오픈API 키 등록+IP허용+데이터수집 검증 완료.

## 발견된 이상 데이터
- **rejoice567(유진쇼핑몰)**: 2026년 매출 0원 — 원인 확인됨: 등록상품 230개 **전부 승인반려**
  (판매 가능한 상품이 하나도 없음). 반려사유 추가조사 필요.
- **rejoice999(유진스타일)**: 상품 9,399개(전체의 85%)인데 매출은 2건뿐 — 상품수 대비
  판매전환 극히 저조, 조사 필요.
- **rejoice678(유진문구)**: 상품 10개뿐인데 매출은 제일 큼(35건/400만원) — 소수 상품 집중판매형.

## 상품명 최적화 프롬프트 2종 (PUBLIC 폴더, 11번가 프롬프트와 동일 포맷)
- `/home/rejoice888/PUBLIC/쿠팡_상품명_프롬프트.txt` — SEO/상위노출용(글자수·검색로직·제재위험 규칙)
- `/home/rejoice888/PUBLIC/쿠팡_상품묶임방지_프롬프트.txt` — 아이템위너(묶임) 회피 전용.
  핵심전략: 옵션구성 차별화(최우선)>동의어치환>표현재구성>고유시리즈명. 허위 구성/인증
  기재는 금지.

**Why:** 향후 세션에서 쿠팡 작업 이어갈 때 오픈API 서명형식(특히 '?' 이슈)과 IP화이트리스트
필요성을 다시 헤매지 않도록.
**How to apply:** 신규 계정 추가시 add_coupang_account + API키 직접 모델에 저장 →
sync_coupang_orders / sync_coupang_products 실행 → IP 미등록시 403 발생하므로 사용자에게
Wing IP등록 요청 먼저 확인.

## 업데이트 (2026-07-06~07)
- **대시보드 완성**: `/coupang` 페이지(CoupangDashboard.tsx) — 계정별 상품수/승인반려/주문/
  부가세매출 표. 백엔드 `apps/coupang/views.py::CoupangDashboardView`. 만들 때 타임존 함정
  (`__date` 필터→0건) 또 걸렸다가 aware datetime 범위로 수정.
- **쿠팡 애즈(광고)는 별도 시스템**: `ads.coupang.com`(Wing과 다른 도메인). 확인된 7계정 중
  4개(rejoice678,234,567,999) **전부 광고 한번도 시작 안 함**("처음이신가요?" 랜딩페이지).
  나머지 3개(dlrmsgh012,666,444)는 사용자가 직접 확인하기로 함(브라우저 자동화 반복시 Akamai
  차단 심해짐 확인).
- **VAT크롤러(부가세) 2025년 백필 시도 실패**: Akamai 차단이 하루 지나도 재발(같은 계정
  rejoice678 이틀 연속 차단) — 완전한 해결책 없음, 속도조절이 유일한 완화책.
- **2025년 매출도 오픈API로 수집완료**: 239건/6,490,730원(3계정만 활동). rejoice999는 API
  150건 vs 매출페이지업로드 733건으로 5배 차이 — 원인 미확인(ordersheets 상태별 페이징 누락
  가능성), 추가조사 필요할 수 있음.

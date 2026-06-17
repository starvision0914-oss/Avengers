---
name: project_11st_myproduct_status_source
description: 11번가 판매상태(ElevenMyProduct.status_type) 진짜 출처 + sync_eleven_my_products(OpenAPI)는 고장
metadata: 
  node_type: memory
  type: project
  originSessionId: b822c371-0117-4ceb-8494-a5dc15123c58
---

11번가 ROAS 비고의 판매상태(판매중/판매중지/품절/판매금지)는 ElevenMyProduct.status_type에서 옴. 비고는 조회시점 실시간 조인(_eleven_product_rows, views.py:1493), 저장 안 됨.

**진짜 출처**: `crawl_11st_products` → crawlers/eleven_product_crawler.py (Selenium + soffice.11st.co.kr 셀러오피스 + 등록상품 엑셀 다운로드 파싱). 전역락 사용하는 정식 브라우저 크롤. 다운로드 폴더 /tmp/avengers_11st_product_downloads.

**고장난 경로(쓰지 말 것)**: `sync_eleven_my_products --api-all` → eleven_my_product_service.fetch_all_products_from_eleven. 사용하는 OpenAPI `apiCode=ProductSearch`는 **buyer용 전체 카탈로그 검색(TotalCount=2.29억)** 이라 셀러 본인 상품이 아님. 응답에 ProductNo/SelStatCd/SellerPrdCd 없음(ProductCode/ProductPrice/SellerNick뿐) → 파싱 0건. 게다가 종료조건이 '짧은페이지'인데 공개카탈로그는 항상 꽉찬페이지 → 사실상 무한페이징하며 전역락 점유+API폭격+차단위험. **0건 수집하며 광고비크론까지 막는 지뢰.** 절대 cron 등록 금지(2026-06-11 잘못 등록했다 즉시 회수).

**현황/조치(2026-06-11)**: crawl_11st_products가 cron에 없어 status가 6/8자로 묵음 → 비고가 실제(삭제 등)와 안 맞는다는 사용자 지적의 근본원인. 실측 페이스 ~5분/계정(엑셀 서버생성 대기 지배적) → 70계정 5~6시간이라 주간 실행 시 11·15시 광고비 크론을 막음. 그래서 **야간 cron 신설: `scripts/cron_11st_product_status.sh` = crawl_11st_products --all --force, 매일 01:00**(07:30 상품ROAS 전에 끝나도록 02시 아님 01시). 빠른 단축은 셀러오피스 product-list 실시간 XHR(JSON) 경로 확보가 필요(미완 과제). 주의: 11번가에서 삭제된 상품은 새 동기화 후 ElevenMyProduct에서 빠져 비고가 '미등록'이 됨('삭제' 명시 원하면 광고비有+동기화목록無 → '삭제' 규칙 추가 필요).

**stale 판매상태 오판 + 자동정정 시스템(2026-06-14)**: _upsert_products(eleven_product_crawler.py:449)는 엑셀에 '나온' 상품만 bulk upsert(update_conflicts). 판매중지/종료로 엑셀에서 빠진 상품은 행이 안 갱신돼 status_type이 마지막 본 '판매중'에 **얼어붙음(stale)** — 삭제로 빠지는 게 아니라 **stale로 남음**(위 16행 '미등록' 설명 정정). 그래서 적자상품이 DB상 '판매중'으로 보여 오판함(실측 14,276건이 stale '판매중'이었음). **판별 키: 한 계정 한 회차 수집은 모든 행이 동일 synced_at(=그 회차 now)을 받음 → `synced_at < 그 계정 MAX(synced_at)` = 이번 목록에서 빠짐 = 판매중지/이탈.** 해법: `reconcile_11st_product_status` 명령 신설(synced_at<max인 행을 status_type='판매중지'로, 최근2일내수집계정만+이탈비율60%↑계정은 부분수집의심 건너뜀, 멱등·재등록시 자동복원). crawl_11st_products 끝에 자동 호출되도록 연결(매일 01시 크론에 포함). 즉 **상품수집 직후 판매상태가 항상 정확**. 오판 났을 때 점검법: synced_at(신선도)을 status_type과 반드시 교차확인.

**셀러오피스 JSON API 프로브 결과(2026-06-11, probe_api.py jinag7461)**: BASE=https://apis.11st.co.kr/product/bruce/selleroffice/v1. `/main/login-seller`→셀러정보 OK(쿠키로그인 세션). 하지만 `/product-list/?pageNo..` 등은 실시간 목록이 아니라 **엑셀 대량생성 이력**(76218301_ALL_*.zip presigned S3 downloadUrl) 반환. `/product/count`는 400(path가 long 기대)→`/product/{productNo}` 단건상세 라우트만 확인. 실시간 상품목록+판매상태 일괄 엔드포인트는 미확정 → 셀러오피스 화면의 실제 XHR을 CDP Network로 떠야 함(다음 과제). fetch_all_products_from_eleven엔 buyer카탈로그 감지 즉시중단+페이지상한 안전장치 추가함(2026-06-11). 관련 [[project_11st_ip_block_prevention]] [[feedback_crawling_rule]] [[project_platform_lock_split]]

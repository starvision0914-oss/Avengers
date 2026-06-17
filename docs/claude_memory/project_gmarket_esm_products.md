---
name: project_gmarket_esm_products
description: 지마켓/옥션(ESM) 나의상품 수집 방법 — ESM Plus 로그인·상품관리 엑셀다운·GmarketMyProduct
metadata: 
  node_type: memory
  type: project
  originSessionId: 01fbf4ca-8075-41d1-994d-3cdbad6cd8fe
---

지마켓/옥션 상품수집 = **ESM Plus 본포털 상품관리 엑셀 다운로드 파싱** (라이브 확인 2026-06-10).
`crawlers/gmarket_product_crawler.py` + `crawl_gmarket_products` 커맨드.

- **로그인(본포털, 광고포털과 별개)**: `www.esmplus.com` → `signin.esmplus.com`. **지마켓 탭**(`button.button__tab` 텍스트 "지마켓") 클릭 → `#typeMemberInputId01`/`#typeMemberInputPassword01` → 로그인버튼 `button.button--blue`. 보안문자 없이 통과.
  - 주의: `ad.esmplus.com`(광고포털, gmarket_crawler 광고비) 로그인과 **세션 분리** — 상품엔 본포털 로그인 필요.
- **상품목록 = 신버전 API(권장, 라이브검증)**: `www.esmplus.com/Home/v2/goods-manage` → iframe `item.esmplus.com/goods/list`. "검색" 버튼(`button.button--blue.button--xlarge`)이 호출하는 **`POST https://item.esmplus.com/api/ea/goods/search`** 를 직접 호출(같은 origin=iframe 컨텍스트에서 fetch, `execute_async_script`). body: `{query:{goodsIds:"",keyword:"",sellStatus:[],category:{},registrationDate:{},shipping:{},additionalService:[]},pageIndex:N,pageSize:500}`. pageIndex 증가로 전량 페이지네이션.
  - 응답 item: `goodsNo`, `siteGoodsNo:{gmkt,iac}`(사이트별 상품번호), `managedCode`(판매자코드), `goodsName`, `price:{gmkt,iac}`, `stock:{gmkt,iac}`, `sellStatus:{gmkt,iac}`(코드), `category.esm.catName`. 한 상품이 gmkt+iac 동시면 각 사이트로 1행씩.
  - dlrmsgh012 검증: 지마켓 15,233 + 옥션 4,027 = 19,260행 수집 성공.
- 구버전 `Sell/Items/ItemsMng`(엑셀다운 `#aExcelDownload`, `ItemMngEvent.Search`)는 **마스터 본인 1건만** 나와 부적합 — 신버전 API 사용.
- **저장**: `GmarketMyProduct` (account+market+상품번호 유니크). MySQL은 `bulk_create(update_conflicts=True, update_fields=[...], **unique_fields 지정 금지**)` 로 누적 upsert.
- ⚠️ sellStatus 코드 한글매핑 미완(21~25만 매핑, 11/01 등 미확인). 중복로그인 18명은 크롤 반복로그인 누적(쿠키재사용/만료로 해소). [[project_gmarket_overview]]

진행 순서(지마켓 11번가화): ③상품수집(완료) → ④상품별광고비 → ⑤AI/CPC/간편 → ①광고비실적 → ②매출/수익.
관련: 지마켓 광고비(ESM+ CPC)는 `gmarket_crawler.py`(ad.esmplus.com)에 이미 있음.

---
name: project_gmarket_esm_groups
description: "지마켓 공유ESM 그룹 맵 + 대시보드 광고비 0 원인(서브계정 미설정), id별 정확수집 요구"
metadata: 
  node_type: memory
  type: project
  originSessionId: 354070d6-c8cd-4591-8ad8-ac8c18636875
---

2026-06-11 확인. 지마켓 대시보드에서 일부 계정 광고비가 0으로 나오는 원인: **여러 판매자 id가 한 ESM을 공유**하는데, 로그인되는 대표 id로만 GmarketDepositSnapshot이 쌓이고 나머지 id는 0. (id 불일치/매칭버그 아님 — 설정 문제)

**ESM 그룹 맵(대표=로그인 / 하위):**
- rejoice222 = 223, 224
- rejoice234 = 235, 236
- dlwodb000 = starvisi (이미 gmarket_origin_id로 묶여 작동)
- tmxkqlwus = 단독계정
- dlwodbs222 = 단독계정

**서브 묶기 메커니즘**: CrawlerAccount.gmarket_origin_id=대표login_id 로 설정하면 gmarket_crawler가 `_get_sub_accounts`로 같은 ESM 세션에서 서브도 수집(`_collect_sub_account`).

**중요 한계/요구**: 현재 `_collect_sub_account`는 광고센터 CPC 페이지를 **그대로 다시 읽어 메인과 동일 값**을 서브 id로 저장(예: dlwodb000=9,746 ↔ starvisi=9,746 동일). 사용자 요구는 **"각 id별 자기 광고비(정확)"** → 광고센터에서 판매자 id를 전환해 각 id 실제 광고비를 따로 읽도록 구현 필요(라이브 ESM 탐색으로 전환 방법 확인). 합계 중복집계 주의.

**단독계정 tmxkqlwus/dlwodbs222**: 쿠키 없음·fail=1·last_crawled=None — ESM 로그인 자체가 실패('수집 결과 없음 시도 2/2'). 대표 id로 1회 정상 로그인시켜야 수집 시작(원인 라이브 진단 필요).

**판매예치금 거래내역 = 지마켓/옥션 별도 (실측 2026-06-11):**
- **지마켓**: `esmplus.com/Member/Settle/GmktSellBalanceManagement` — sellerId 드롭다운에 복수아이디 다 뜸(rejoice234 로그인시 [234,235,236]). **id별 분리 가능**. 단 API(GmktSellBalanceUseListSearch)는 HTML반환 → ai100처럼 **엑셀 다운로드** 필요(searchSDT/EDT JS설정→btnSearch→excelDown 클릭). 엑셀 컬럼: 거래일시/거래내역/금액/비고.
- **옥션**: `IacSellBalanceManagement` — 드롭다운 마스터 1개만. **API(IacSellBalanceUseListSearch) 조회됨**. 현 크롤러(gmarket_cost_crawler)가 쓰는 게 이거 = **옥션만 수집 중, 지마켓 판매예치금은 미수집**이었음.
- 일부 계정(rejoice666→마스터rejoice7942(계정아님), rejoice987/dlwodb111/678/777/888/dlwodbs222)은 마스터로도 판매예치금 2026 전체 0 → 광고캐시 등 다른 결제수단 의심(판매예치금 밖).

**진행(2026-06-11)**: ①대시보드 그룹화 완료(222/234/dlwodb000 그룹 origin+display_order 인접) ②GmarketCostHistory에 `market`(gmarket/auction) 필드+마이그레이션 완료(유니크 seller_id+market+use_date+seq).

**해결됨 — 복수아이디 지마켓 판매예치금 수집 방법(검증 2026-06-11)**:
1. 마스터로 _esm_login → `GmktSellBalanceManagement` 진입
2. `sellerId` 드롭다운 옵션 = 그 ESM의 서브 id 전부(rejoice234→[234,235,236]). `Select.select_by_value(sub)`로 각 서브 선택
3. **1개월 제한**: searchSDT/EDT를 한 달로 JS설정(dispatch change) → `//*[@id="btnSearch"]/img` 클릭 → 한 달 초과시 alert "한달 이내에..." → accept. 월별 루프 필수
4. 추출: `table id=grid_sortingData`의 tr 파싱. td 인덱스: [0]차감/적립 [1]거래일시(YYYY-MM-DD HH:MM:SS) [2]금액 [7]코멘트("[광고] CPC 광고구매"/"AI매출업"/"서버비용") [9]주문번호. (엑셀 다운로드도 됨: excelDown→'G마켓_판매예치금_*.xls', 단 1개월 범위일 때만)
5. 저장: GmarketCostHistory(seller_id=서브, market='gmarket', ...) 멱등(seller+market+year 삭제후 삽입)

결과: 8계정 id별 2026 지마켓 광고비 수집 성공(rejoice234=123,079 235=16,060 236=25,289 dlwodb000=91,729 starvisi=59,422 222=79,629 223=62,766 224=36,058, 합494,032, 중복0). 옥션(Iac)만 볼 땐 5개 서브가 0이었음.

**남음**: 일회성 스크립트(collect_gmkt_balance)로 수집함 → gmarket_cost_crawler에 정식 통합(지마켓 Gmkt 그리드 + 옥션 Iac API 둘 다, market태그) + 나머지 22계정도 지마켓 판매예치금 수집(현재 옥션만). 광고캐시 결제계정(rejoice987/dlwodb111/678/777/888/dlwodbs222 등)은 판매예치금 밖이라 별도. ai100 원본: /tmp/ai100/viewer/gmarket_cpc/crawlers/backup_200_esmcost2db/esmcost2dbct.py.

**해결됨 — 공유ESM 상품수(GmarketMyProduct) id별 정확분배(2026-06-12)**: 버그=크롤러가 공유ESM 전체 상품목록을 각 서브계정에 통째 복사저장→대시보드 상품수 동일(222=223=224 각17427). 원인=goods/search item의 **`siteSellerId.{gmkt,iac}`**(=각 상품 실소유 판매자id, 라이브확인 item[0].siteSellerId.gmkt='rejoice222')를 무시하고 로그인계정에 전부 저장. 수정: `gmarket_product_crawler._save_items`가 siteSellerId로 실소유 계정에 분배 저장(`_owner_map`=origin그룹 login_id→account, 매핑없으면 로그인계정 폴백) + `run_all_accounts`가 명시필터 없으면 서브(gmarket_origin_id 보유) 자동스킵(마스터가 그룹전체 수집). 재수집은 마크앤스윕(t0前 synced_at 삭제). 결과 실측: 222/223/224=9426/3999/4002, 234/235/236=14977/2152/2098, dlwodb000/starvisi=12257/13467(옥션은 마스터단일ID라 서브0). SELL_STATUS에 '11'(판매중) 추가.

**상품 수집 스케줄(2026-06-12 신설)**: 그전엔 cron 없음(수동 crawl_gmarket_products만)이었음 → `scripts/cron_gmarket_products.sh` + crontab **매일 02:00** 추가(상품수·판매상태 비고 신선도). 11번가는 08:30(상품)+01:00(상태). ROAS페이지 이름 '지마켓/옥션 상품 ROAS'로 변경(광고비·실매출 이미 옥션 포함).

관련: [[project_gmarket_adcost_source]] (광고비 신뢰값=스냅샷), [[project_gmarket_esm_products]] (ESM 로그인 구조), [[project_gmarket_product_status]] (비고 상품상태), [[reference_ai100]].

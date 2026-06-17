---
name: project_gmarket_subaccount_token
description: 지마켓 복수아이디 서브계정 광고비 수집법 — GmktSellBalanceManagement에서 드롭다운 선택+검색
metadata: 
  node_type: memory
  type: project
  originSessionId: 34b8a2c1-a725-49d1-836d-7e26a001dc32
---

지마켓 **복수아이디 서브계정**(rejoice224/235/236 등) 거래내역(GmarketCostHistory) 수집 정답(2026-06-12 검증, rejoice224 6월 AI=12,562·6/1=4,169 실측일치):

**핵심: 옥션 페이지가 아니라 G마켓 페이지를 써야 함.**
- `IacSellBalanceManagement`(옥션)는 드롭다운에 옥션계정만(보통 마스터 1개) → 서브 안보임. 기존 크롤러가 이걸 써서 222만 수집됐음.
- **`https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement?menuCode=TDM134`** 로딩하면 `#sellerId` 드롭다운에 G마켓 서브 전부(222·223·224) + 각 `data-token` 뜸. (gmktAccCnt=3)

**수집 절차(셀레늄, 마스터 로그인 세션 필요):**
1. 마스터로 로그인(서브는 마스터 pw 공유, ESM_TOKEN의 mid=마스터/lid=현재계정)
2. GmktSellBalanceManagement 로딩 → `Select(#sellerId).select_by_value('rejoice224')`
3. `#selPagingSize`=100, `#searchSDT/#searchEDT` JS로 값설정(readonly)
4. **`#btnSearch` 실제 클릭**(MenuCode/__RequestVerificationToken CSRF를 페이지가 처리) — raw fetch는 HTML(LogOn리다이렉트/MenuCode가드)로 실패
5. 결과표 tr 파싱: 컬럼=[SaveTypeNm(적립/차감), TransDate, TransMoney, SdMoney, AdMoney, SdCodeNm, GoodsNo, Comment, GoodsNm, RefNo]. amount=TransMoney, transaction_type=_classify(Comment)

**안 되는 것:** 사용자 브라우저 쿠키 주입 → ESM_REQUEST_AUTH_PC가 PC/IP바인딩이라 타 IP(서버)에선 LogOn 리다이렉트. data-token도 세션없인 무효.
**현황:** 224 복구완료. 235/236(마스터 rejoice234), 기타 서브 동일방식 필요. 크롤러 영구수정 대상(BALANCE_PAGE를 Gmkt로, 드롭다운순회). [[project_gmarket_esm_groups]] [[project_gmarket_cost_delete_on_fail]] [[feedback_crawling_rule]]

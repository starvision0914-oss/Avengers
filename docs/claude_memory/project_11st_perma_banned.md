---
name: project_11st_perma_banned
description: 11번가 영구정지 계정(AD OFFICE 접속불가) — ROAS 판단·AD OFFICE 크롤에서 제외
metadata: 
  node_type: memory
  type: project
  originSessionId: 01fbf4ca-8075-41d1-994d-3cdbad6cd8fe
---

영구정지 11번가 계정은 **AD OFFICE 접속이 안 됨** → 광고비/ROAS 확인 불가. 정지 해제될 때까지 AD OFFICE 크롤·적자(로하스) 판단에서 제외한다.

- 현재 목록: `rejoice43`, `tmxkqlwus12`, `rejoice777` (AD OFFICE만 제외, 셀러오피스/상품/제재는 수집 가능).
- 중앙관리: `apps/cpc/eleven_block_guard.PERMA_BANNED_EIDS` + `exclude_perma_banned(qs)`. **해제되면 이 set에서 빼면 됨.**
- 적용처: `eleven_product_roas`·`eleven_product_daily` run_all_accounts qs, `views._active_eids()`(적자 산출 진입점).
- rejoice43: 2026-06-16 재등록(api_key 3452b294…, 비번 저장, 셀러오피스 로그인·OTP 정상). 번호공백(41·42·44만 있던) = 이전 삭제됐던 계정. 유진코 계정군.

**정지 사유(2026-06-16 셀러오피스 제재내역 전수 직접확인 — SellerNewMainEmergencyAction emerNtceClfNo=11전체/23안전거래/27페널티, seachPagingFn(n) 페이징으로 전 페이지)**: 계정별로 사유가 다름.
- **rejoice777**(제재 378건): 지식재산권 침해신고 5회+ · 전기용품/전파법/환경부 안전기준 부적합 · 발송지연/평점. 판매중1·판매중지4556(거의전체정지) — 최악.
- **tmxkqlwus12**(381건): **저작권 침해 ID 일시정지 예고**(26/02·04) · 가송장(허위송장) 노출제한 · KC미인증 어린이완구 · 탄환용 구슬 · 의약외품회수 · 지재권신고 · 발송지연170. 영업중(판매중5398)+판매금지61.
- **rejoice43**(전체 40건뿐, 경미): **불법 어구(어업도구) 판매금지** + 금어기(수산) 협조 — 수산/어업 규제 위반이 유일. 발송지연/지재권 없음 → 회복가능성 높음(이의신청 우선).
- 직접 트리거(영구정지): 저작권/지재권 침해 + 가송장(부정행위). 만성 발송지연/평점이 바탕.
배지 숫자=미확인(unread)수, 전수는 seachPagingFn 페이징 크롤이라야 정확(목록 기본 ~6건만 렌더). 예방: 전계정 판매중 브랜드위험 12,350개·11번가 판매금지 W코드 12,578개(금지코드/금지어/분류 CSV: /home/rejoice888/PUBLIC/제재조사/). 해결=지재권/저작권·안전기준/KC·불법어구 품목 삭제+소명 후 고객센터 이의신청.

이 제재사유(저작권/지재권/KC미인증/불법품목/성인19금 오등록)를 회피하는 **11번가 상품명 생성 AI 프롬프트**: `/home/rejoice888/PUBLIC/11st_product_name_prompt_v3.txt` + `/ownerclan` 페이지 "🏷 11번가 상품명변경" 버튼(OwnerclanElevenPromptModal, 복사 전용). 글자수 한글25/영숫50byte·홍보문구20자, 오탐방지(멸균우유·당뇨양말·올스텐가위 텐가 등 맥락판단).

관련: [[project_11st_loss_delete]] [[reference_domeggook]]

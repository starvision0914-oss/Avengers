---
name: coupang-seller-name-gmarket-match
description: 쿠팡 계정 seller_name을 지마켓 기준(login_id 매칭)으로 정정·통일(2026-07-10)
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c869bf-5391-4b3b-9a65-c7c70b0cd41d
---

쿠팡 계정 7개 중 다수가 seller_name이 미설정이거나 잘못돼 있었음(예: rejoice999가 '유진스타일'로 잘못 라벨 → 실제 지마켓 기준 rejoice999='아이리스', rejoice666='유진스타일'이 서로 뒤바뀌어 있었음). 지마켓 `CrawlerAccount`를 기준으로 같은 login_id의 seller_name을 그대로 복사해 정정 완료 — 세무페이지(`_tax_group_key`, 셀러명 앞3글자)와 Overview 대시보드 그룹핑이 login_id 매칭 기준이라 이게 맞아야 플랫폼 간 정확히 묶임.

최종 매핑: rejoice234→스타피씨에스, rejoice567→유진쇼핑몰, rejoice678→유진문구닷컴, rejoice999→아이리스, dlrmsgh012→유진컴퍼니, rejoice666→유진스타일, rejoice444→유진코리아.

**Why**: 사용자가 "쿠팡 아이디를 지마켓 기준으로 셋팅+매칭" 요청.
**How to apply**: 새 쿠팡/롯데온 등 계정 추가 시 seller_name을 지마켓의 같은 login_id 값으로 맞춰야 세무/Overview 그룹핑이 정확함 — 수동 입력 시 이 관례를 따를 것.

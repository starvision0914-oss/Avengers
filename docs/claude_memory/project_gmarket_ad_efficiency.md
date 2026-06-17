---
name: project_gmarket_ad_efficiency
description: 지마켓 광고 효율 딥리서치 결과 + 손익분기 ROAS + 상시 진단엔진
metadata: 
  node_type: memory
  type: project
  originSessionId: e76d08ca-b676-492c-8ef3-735797020404
---

2026 지마켓 광고 딥리서치(광고센터 GmarketProductAdCost): 광고비 9,425만/전환 2.22억/ROAS 235%. **극단적 양극화** — 승자(ROAS≥400) 광고비 10%가 전환 92%, 적자(≤100) 광고비 82%가 전환 1%. CTR 0.22%(매우 낮음). CPC 76%(ROAS228·CPC600)/AI 24%(ROAS258·CPC379) → **AI 효율 우위인데 저활용**, 계정별 상이(dlwodb888=CPC, rejoice321=AI).

**진짜 손익분기 ROAS ≈ 450~490%** (11번가 원가 ElevenMyProduct.purchase_cost를 판매자코드로 연결, 평균마진 22%). "ROAS 100"은 적자기준이 한참 낮았음. 원가매칭 광고비의 90%가 손익분기 미달.

**상시 진단엔진**: `gmarket_ad_diagnose`(읽기전용, 실ROAS+원가 손익분기로 승자/회색/적자/무전환낭비/판매불가 분류). 매일 09:30 cron(cron_gmarket_ad_diagnose.sh)으로 텔레그램 발송. 컷후보(적자+무전환)=최근2개월 67%.

대책 우선순위: ①적자·무전환 자동OFF(실ROAS·단계적) ②승자 예산집중 ③CPC↔AI 계정별 최적화 ④CTR개선 ⑤키워드 전체수집→적자키워드컷 ⑥계정 운영표준화. [[project_gmarket_unavailable_detection]] [[project_gmarket_roas_page]]

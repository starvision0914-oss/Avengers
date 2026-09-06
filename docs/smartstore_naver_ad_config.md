# 스마트스토어 — 네이버 광고비 설정 현황 (2026-09-06 업데이트)

## 계정별 네이버 검색광고 API 설정 (SmartStoreAccount)

| id | 스토어 | CPC customer_id | CPC login_id | CPC account_id | AI |
|---|---|---|---|---|---|
| 4 | 유진코리아몰 | 1891217 | rejoice888 | 389851 | 없음 |
| 7 | 아이리스. | 2761225 | rejoice999 | 988184 | 없음(비활성화) |
| 13 | 스타쇼핑몰 | 3790215 | rejoice666 | 1545326 | 없음 |

## 변경 이력 (2026-09-05~06)

### 1. 스타쇼핑몰 AI → 유진코리아몰 CPC 이관
- 9/1~9/2까지는 스타쇼핑몰의 AI광고 계정(customer=1891217, login=rejoice888, account_id=389851)으로
  정상 수집되고 있었는데, 9/2~9/3 사이 스타쇼핑몰 쪽 AI 필드가 전부 비워지고 그 계정번호/로그인ID가
  유진코리아몰 쪽에 일부만(account_id, login_id) 옮겨진 상태로 발견됨(customer_id/license/secret은 미이관).
- 사용자 확인: "8월이전까지는 스타쇼핑몰의 AI 광고센터였고 9월부터는 유진코리아몰 CPC 광고센터" —
  스타쇼핑몰→유진코리아몰로 의도적 이관된 것이 맞음, CPC로 완료 처리.
- `naver_ad_customer_id`/`access_license`/`secret_key`를 유진코리아몰에 마저 채워 이관 완료.
- 검증: 9/1~9/5 재수집 → 7,162개 상품, since_date=2026-09-01 단일 버킷, ad_type=cpc, 누적 67,906원
  (중복/겹침 없음, 스타쇼핑몰 시절 규모와 비교해도 합리적인 페이스).

### 2. 아이리스 AI광고 비활성화
- 아이리스(id=7)는 `naver_ad_ai_customer_id`=2761225가 설정돼 있었지만 `naver_ad_ai_login_id`가 계속
  비어있어 개설 이후 AI광고비가 한 번도 수집된 적 없었음(`crawl_naver_product_adcost` 매일 "AI 스킵" 로그).
- 사용자 지시(2026-09-06): "AI 진행내역 없어 아이리스 AI 중지해줘" → 네이버 쪽 AI 캠페인 on/off
  자동화는 시스템에 없어서(지마켓과 달리 미구축), **DB의 AI 관련 필드 4개(customer_id/login_id/
  access_license/account_id)를 전부 비워 수집 시도 자체를 중단**하는 것으로 처리.

### 3. 아이리스 CPC 쇼핑광고 입찰가 조정
배경: "2.0↑_251120" 캠페인(dailyBudget=20,000원)이 정오(12시)쯤 예산 소진으로 꺼져버려 4시까지
못 버티는 문제. 클릭당 단가를 낮춰 예산 소진 속도를 늦추는 방향으로 대응.

- 캠페인: `cmp-a001-02-000000010030380`("2.0↑_251120"), 광고그룹 8개(001~008), 상품광고(SHOPPING_PRODUCT_AD)
  총 6,158건. 입찰가는 각 광고(`nccAdId`)의 `adAttr.bidAmt` 필드에 개별 설정됨(그룹 기본값은 전부 50원이지만
  거의 모든 상품이 그룹값을 안 쓰고(`useGroupBidAmt=false`) 자체 입찰가를 가짐).
- API: `PUT https://api.naver.com/ncc/ads/{nccAdId}?fields=adAttr`,
  body `{"nccAdId":..., "type":"SHOPPING_PRODUCT_AD", "adAttr":{"bidAmt":N,"useGroupBidAmt":false}}`
  (주의: `type` 필드를 body에 꼭 포함해야 함 — 없으면 400 "Invalid ad type" 에러).
- **1차 조정(-50원, 최저 50원 보장)**: 150→100(5,501건) / 110→60(399건) / 130→80(252건) /
  180→130(3건) / 90,100→50(각1건) / 190→140(1건). 전체 6,158건 성공, 실패 0.
- **2차 조정(+20원, 사용자가 "너무 많이 낮춘 것 같다"고 되돌림)**: 100→120 / 60→80 / 80→100 /
  150→150(130+20) / 70→70(50+20) / 160→160(140+20). 전체 6,158건 성공, 실패 0.
- **현재(2026-09-06 기준) 최종 입찰가 분포**: 120원(5,501건) / 80원(399건) / 100원(252건) /
  150원(3건) / 70원(2건) / 160원(1건) — 원래(150원 기준) 대비 평균 -30원 수준.
- 효과는 하루 지켜본 뒤(예산이 몇 시까지 버티는지) 필요시 추가 조정.

## 참고
- Naver SearchAd API 클라이언트: `apps/smartstore/services/naver_search_ad.py` (`_get`/`_put`, HMAC-SHA256 서명)
- 캠페인/광고그룹/광고 조회: `GET /ncc/campaigns`, `GET /ncc/adgroups?nccCampaignId=`, `GET /ncc/ads?nccAdgroupId=`

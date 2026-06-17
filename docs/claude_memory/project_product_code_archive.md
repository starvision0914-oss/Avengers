---
name: project_product_code_archive
description: 상품번호→판매자코드 영구 보존고(ProductCodeArchive) — 삭제돼도 코드 조회 가능. 자동 스냅샷 크론
metadata: 
  node_type: memory
  type: project
  originSessionId: fad4d127-1168-451f-87db-42bab5a25f72
---

**문제**: 마켓에서 상품 삭제 시 나의상품(ElevenMyProduct/GmarketMyProduct) 카탈로그에서 제거됨 → `상품번호→판매자코드` 다리가 끊겨 키워드/ROAS 리포트에서 판매자코드 빈칸. 광고데이터(St11ProductDaily 등)엔 **상품번호는 영구 누적**되나 판매자코드는 없음. 매출(SalesRecord)엔 상품번호 컬럼 자체가 없어 복구 불가. 사용자 워크플로우=적자엑셀 받아 **사이트에서 직접 삭제**(툴 미경유)라 St11LossDeleted/GmarketLossDeleted에도 기록 안 됨.

**해결(2026-06-13 구축)**: `ProductCodeArchive` 모델 신설(db_table=product_code_archive, unique=(platform,product_no), 필드 platform/login_id/product_no/seller_code/product_name/source/first_seen/last_seen). 적재명령 `archive_product_codes`:
- `--snapshot`: ElevenMyProduct+GmarketMyProduct에서 판매자코드 있는 상품 upsert(빈코드 제외→기존값 보호). **매일 03:00 크론 `cron_archive_product_codes.sh`**(나의상품 수집 01/02시 이후). 삭제 전날 스냅샷에 코드가 남으므로 직접삭제해도 보존됨.
- `--ingest-csv <path> --platform <11st|gmarket>`: 받아둔 적자/ROAS 엑셀(컬럼 상품번호·판매자코드·아이디·상품명) 적재. 과거 복구용. 704파일(Downloads/적자상품_삭제목록_704.csv) 적재 완료.
- ★MySQL은 bulk_create(update_conflicts=True)에 unique_fields 지정 불가 → unique_fields 빼고 update_fields만(유니크키 자동).

초기 적재 결과: 보존고 1,045,811건(11번가 585,729 / 지마켓 460,082). **한계**: 구축 이전 삭제된 상품(지마켓 47개 등)은 스냅샷 부재로 복구 불가, 지마켓 적자엑셀 받으면 ingest로 보충.

**리포트 빈칸 자동채움(2026-06-13 완료)**: `_eleven_product_rows`(11st, code_map 보충)와 `_gmarket_realsales`(gmarket, code_by_pno 보충)에 MyProduct 누락 시 ProductCodeArchive 폴백 연결. 보존고로 채운 건 비고/status='삭제(코드보존)'. 지마켓 키워드 엑셀도 _gmarket_realsales 경유라 함께 적용됨. 단 보존고=현재카탈로그(스냅샷 직후)라 즉시효과 없음, 스냅샷 이후 삭제분부터 채워짐. 구축前 삭제된 지마켓 47개는 보존고에 없어 여전히 빈칸(적자엑셀 ingest로 보충 가능). 관련 [[project_gmarket_keyword_report]] [[project_11st_loss_delete]] [[project_gmarket_roas_page]].

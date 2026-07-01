---
name: project_smartstore_commerce_api_status
description: 스마트스토어 Commerce API 등록 현황 (2026-07-01 재확인 — 전체 등록완료로 갱신)
metadata: 
  node_type: memory
  type: project
  originSessionId: 65854cbc-8aa2-4568-95c3-193c08d99126
---

## 2026-07-01 재확인: 전체 17개 계정 API 등록 완료

이전(2026-06-29) 기록엔 7개 계정 미등록으로 남아있었으나, DB 재조회 결과 **17개 계정 전부 commerce_api_key/commerce_secret_key 등록되어 있음**. 미등록 문제는 그 사이 해결됨 — 이 메모리가 이전 기록을 대체함.

| ID | 스토어명 | 로그인ID | 활성 | 상품등록수(2026-07-01) |
|----|---------|---------|------|------|
| 1 | 유진컴퍼니 스스 | dlrmsgh0123@gmail.com | O | 5 |
| 2 | 스타비젼 | dlrmsgh01234@gmail.com | O | 1,001 |
| 3 | 스타보관소 | dlwodbs000@gmail.com | O | 4,457 |
| 4 | 유진코리아몰 | dlwodbs7942@gmail.com | O | 33,297 |
| 5 | 유진쇼핑몰 | rejoice666@naver.com | O | 8,606 |
| 6 | 유진집 스스 | rejoice999@naver.com | O | 4,356 |
| 7 | 아이리스. | starvis7783@gmail.com | O | 17,188 |
| 8 | 아이리스홈스토어 | starvis7783@gmail.com | O(2026-07-01 활성화) | 26 |
| 9 | 스타라이프 스스 | starvis8942@gmail.com | O | 2 |
| 10 | 스타주노 스스 | starvis9942@gmail.com | O | 9,334 |
| 11 | 스타윈블리 | starvisi0914@gmail.com | O | 233 |
| 12 | 스타컴퍼니 스스 | starvisi7942@gmail.com | O | 9,992 |
| 13 | 스타쇼핑몰 스스 | starvision0914@gmail.com | O | 18,884 |
| 14 | 유진스타일 스스 | starvision7942@gmail.com | O | 8,162 |
| 15 | 주노그노 스스 | tmxkqlwus@gmail.com | O | 2,836 |
| 16 | 유진문구 | tmxkqlwus@naver.com | O | 21 |
| 17 | 유진대기업 | starvisi999@gmail.com | O | 0 (수집 미실행) |

**남은 확인포인트**: 1번(5건)·9번(2건)·16번(21건)·17번(0건)은 상품수가 비정상적으로 적어 실제 수집이 제대로 안 됐을 가능성 있음. 크롤 명령: `python manage.py crawl_smartstore --account {id} --skip-sales`.

**Why:** 정기적으로 재확인 필요(계정 상태·API 등록은 수시로 바뀜). DB 직접조회가 항상 최신 진실.
**How to apply:** 스마트스토어 계정 관련 작업 전 이 표 대신 반드시 DB로 재확인(`SmartStoreAccount.objects.all()`) — 이 메모리도 시간 지나면 stale해짐.

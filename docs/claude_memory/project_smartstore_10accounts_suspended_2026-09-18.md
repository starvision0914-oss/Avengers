---
name: project_smartstore_10accounts_suspended_2026-09-18
description: 스마트스토어 10개 계정 이용정지(제품 블락)로 크롤 보류 — 사용자가 정지해제 후 직접 재크롤 요청 예정
metadata: 
  node_type: memory
  type: project
  originSessionId: 1656b89e-b1e1-4da1-840a-2c88b0232d49
  modified: 2026-09-17T23:39:04.188Z
---

2026-09-18 확인: 스마트스토어 27계정 중 10개 계정이 최근(9/14~9/17) 4일 연속 "merchantNo 추출 실패"
반복 — 로그인은 성공하지만 그 이후 접근이 막힘. 사용자 확인: 이 10개 계정은 **현재 이용정지 중이고
제품이 블락 걸려있는 상태**라서 발생하는 정상적인 현상(버그 아님).

**대상 10계정**: dlrmsgh01231@gmail.com(스타코리아), i92372664@gmail.com(스타고급상점),
ij9602847@gmail.com(스타드림딜), ijaeyun044@gmail.com(스타피씨에스), jinag7460@gmail.com(스타블루오션),
rejoice08217@gmail.com(유진오피스), rejoice7942@gmail.com(스타전문점), sjsiahw@gmail.com(스타그노),
starvis0914@gmail.com(스타웨이브), starvis7942@gmail.com(스타프랜즈).

**조치(2026-09-18)**: 10계정 전부 `SmartStoreAccount.is_active=False` 처리 + memo 기록 —
`crawl_smartstore` 커맨드가 `is_active=True`만 대상으로 하므로 자동으로 야간 크롤 대상에서 제외됨.

**Why:** 사용자 지시: "이용정지 해결되면 크롤요청할테니 지금은 보류해라." 이용정지 상태에서 계속
로그인 시도하는 건 무의미하고(제품 블락이라 merchantNo를 못 가져옴), 로그인 시도 자체도 계정에
안 좋을 수 있음.

**How to apply:** 이 10계정은 **사용자가 직접 "이용정지 해결됐다"고 말하기 전까지 is_active를
다시 켜지 말 것**. 스마트스토어 크롤/집계 관련 작업 시 이 10계정이 안 보이는 건 정상(의도된 제외).
재개 지시가 오면: is_active=True로 되돌리고, 로그인/merchantNo 재시도는 최대 3회로 제한해서
진행할 것(사용자 지시 — 무한 재시도 금지, 계정 상태 안 좋을 수 있어 보수적으로).

---
name: project_gmarket_suspend_success_not_sticking
description: 지마켓 미매칭/적자삭제 판매중지가 로그엔 성공(ok:True)으로 찍히는데 실제 DB에는 거의 반영 안 됨(11번가는 정상)
metadata: 
  node_type: memory
  type: project
  originSessionId: bde93fa4-f2ed-49c3-bbc9-edaf62785b13
  modified: 2026-08-22T22:56:12.862Z
---

지마켓 `GmarketSuspendAllNoMatchView`(apps/cpc/views.py:2132, 필터: seller_product_code W코드+purchase_cost null+status_type='판매중')로 미매칭 일괄 판매중지를 여러 차례 실행했고, `/tmp/delete_loss_gmarket.log`에는 매번 `'ok': True`와 큰 `stopped` 건수(예: dlwodbs666 stopped 2955, rejoice678 stopped 2423)가 찍혀있음.

**Why 중요:** 그런데 실제 DB(GmarketMyProduct)를 직접 세보면 같은 필터 기준 status_type='판매중지'로 실제 바뀐 건 484건뿐이고, '판매중'으로 여전히 남은(미매칭) 건은 34,679건 — 로그의 '성공' 건수와 거의 정확히 일치하는 만큼(dlwodbs666, rejoice678 등 계정별 잔여건수가 로그의 stopped 건수와 거의 같음)이 실제로는 반영이 안 된 것으로 보임. 즉 **버튼 클릭→서버 응답은 성공인데 지마켓 실사이트에 실제로 적용 안 됐거나, 이후 상태동기화 크롤이 실사이트 상태를 다시 읽어와 덮어썼을 가능성.**
비교로 11번가(ElevenSuspendAllNoMatchView, apps/cpc/views.py:2057)는 같은 개념인데 82,428건이 실제로 판매중지 반영되어 있어 정상 작동 이력 확인됨(잔여 22,092건은 최근 select_all 실패([[project_11st_loss_delete_selectall_bug]] 계열 문제)로 추정되는 소수 계정 편중, dlrmsgh014 등).

**How to apply:** 지마켓 판매중지류 기능(미매칭/적자삭제 등, delete_loss_gmarket 관련) 작업 시 로그의 'ok':True/stopped 건수를 성공 증거로 믿지 말 것 — 반드시 DB에서 status_type='판매중지' 실측치로 재검증.

**근본원인 확정(2026-08-23):** `crawlers/gmarket_loss_delete.py`의 `run_delete()` stop_only 모드가 "전체선택→판매상태변경→판매중지" 버튼 클릭이 **예외 없이 성공했다는 것만으로 성공 판정**하고(실제 사이트 반영 여부 재조회 검증 없음 — real 삭제모드는 재조회로 remaining==0 검증하는데 stop_only만 이 검증이 빠져있음), 곧바로 로컬 DB `GmarketMyProduct.status_type='판매중지'`로 낙관적 업데이트함. 가상그리드에서 select-all/버튼 클릭이 UI상 "성공"해도 실제 지마켓 사이트에는 반영 안 되는 경우가 있는데(2026-08-22 코드주석에 이미 기록: 31,593건 지정 중 2,741건만 실제처리 확인된 전례), 이걸 걸러낼 방법이 없음.
그리고 매일 02:00 `crawl_gmarket_products`(`crawlers/gmarket_product_crawler.py:221-225`)가 지마켓 API의 실제 `sellStatus`를 읽어 `status_type`을 **무조건 덮어쓰기**(bulk_create update_conflicts) — 실제 사이트가 안 바뀌었으면 다음날 새벽에 '판매중'으로 자동 원복됨. 그래서 로그엔 "성공"이 찍히고 당일엔 DB도 잠깐 '판매중지'였다가, 다음날 새벽 크롤로 조용히 '판매중'으로 되돌아가는 패턴 — 484건만 남은 건 실제로 사이트에서 처리된 진짜 성공분.
**수정방향(미적용):** stop_only 모드에도 real 모드처럼 재조회 후 잔여검증(또는 API로 실제 상태 확인) 단계를 추가해야 함.

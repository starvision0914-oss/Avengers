---
name: project_11st_cost_partial_loss
description: 11번가 광고비 저장 부분유실 함정 + 다운로드 재시도 (2026-06-11 수정)
metadata: 
  node_type: memory
  type: project
  originSessionId: b822c371-0117-4ceb-8494-a5dc15123c58
---

11번가 광고비 수집(eleven_crawler.run_all_accounts)에서:

**부분유실 함정**: ElevenCostHistory 테이블엔 cost_type 컬럼이 없다. _save_cost_rows는 새 items의 [min,max] transaction_datetime 범위를 통째 delete 후 재삽입한다. 따라서 셀러포인트·셀러캐시 중 한쪽만 다운로드 성공하면, 그 한쪽 범위에 들어가는 반대편 결제수단 행이 삭제되고 미복원되어 유실된다.
**How to apply:** got_types로 양쪽 모두 성공했을 때만 저장, 한쪽이라도 실패하면 raise→다음 회차 재수집(부분저장 금지). 2026-06-11 적용.

**다운로드 재시도**: _download_cost_xls는 재시도가 없어 일시적 iframe대기/클릭 실패 1회로 해당 계정 데이터가 풀런까지 유실됐다(2026-06-10 18시 크론서 474회 실패). COST_DL_RETRIES=2로 결제수단별 2회 시도(2~4초 백오프). 단 다운로드 TimeoutException은 is_block_signal=False라 circuit breaker가 안 잡으므로 재시도는 2회로 제한(IP부하 증폭 방지).

**정상 케이스 주의**: 광고비 0건이어도 파일은 다운로드됨("광고비 파일 비어있음(데이터없음)")→fp truthy→성공 처리. 따라서 양쪽성공 요구가 무지출 계정을 깨지 않는다.

last_crawled_at은 성공(if got_types 양쪽)일 때만 갱신 → 실패계정은 신선도스킵(6h) 안 됨, 다음 회차 재시도됨. 관련 [[project_11st_transient_fails]] [[feedback_crawling_rule]]

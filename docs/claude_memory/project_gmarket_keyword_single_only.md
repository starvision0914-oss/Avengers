---
name: project_gmarket_keyword_single_only
description: "지마켓 키워드 백필은 단일 실행만(동시2개 캡차확산), 쿠키우선+계정간90초, 캡차트리거=풀로그인빈도"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4b81a2de-3c94-48d2-a767-9d7a7a3fd4ae
---

지마켓 키워드 백필(crawl_gmarket_keywords)은 **반드시 단일 실행**. 2026-06-14 새벽 2개조 동시크롤(락분리 gmarket/gmarket_b로 우회) 실증 실패.

**왜 동시가 실패하나 (단일 IP/단일 PC 인과사슬):**
1. CPU 경합 → 각 크롬 2~3배 느려짐(5.7초→9~19초). 합산 처리량 6.0초 ≈ 단일 5.7초 → **속도 이득 0**
2. 페이지 렌더 지연 → **stale element 오류 23~32%** → 그 상품 키워드 누락
3. 오류로 계정 빨리 넘김 → **신선계정 풀로그인 연속** → 지마켓 봇탐지 → **캡차 확산**(rejoice321·444·567·678)

**핵심 교훈:** 캡차의 진짜 트리거는 "동시"가 아니라 **짧은 시간 다중 풀로그인**. [[project_gmarket_captcha_login]]

**해결책(현재 적용):**
- 단일 실행만. eleven_block_guard 동시크롤 락이 원래 옳았음 — 락분리(gmarket_b)는 봉인. [[project_platform_lock_split]]
- **쿠키 우선 로그인**(풀로그인 최소화) + **계정 간 90초 간격**(풀로그인 분산) → /tmp/kw_backfill_single.sh
- 속도는 **Tier A(상품당 sleep 0.5/2.5초, 페이싱1.2초 유지)=5.7초/상품**면 충분. 그 이상 단축은 캡차/stale 위험. stale element는 단일에선 경합없어 거의 0.

**Why:** 동시크롤은 단일호스트에선 이득 없이 캡차·데이터누락·IP위험만 키움. **How to apply:** 지마켓 키워드/광고비 크롤은 항상 단일. 빨리 끝내려 동시 돌리지 말 것. 데이터는 멱등이라 누락분 재크롤로 복구. 관련 [[project_gmarket_keyword_lock_gotcha]] [[feedback_crawling_rule]] [[project_11st_ip_block_prevention]]

---
name: smartstore-api-setup
description: 스마트스토어 계정별 네이버 커머스 API 키 설정 현황 및 이슈
metadata: 
  node_type: memory
  type: project
  originSessionId: 60e3911b-54d5-4cdb-a29b-c366d7cee782
---

2026-06-29 기준 스마트스토어 Commerce API 설정 완료 현황.

**Why:** 상품 수집·판매통계·광고비 자동 크롤을 위해 계정별 API 키 등록.

**How to apply:** API 오류 계정은 네이버 커머스 API 콘솔에서 앱 승인/스토어 연동 확인 필요.

## 정상 계정 (✅ 토큰 발급 성공)
- id=1  유진컴퍼니 (dlrmsgh0123@gmail.com)
- id=2  스타비젼 (dlrmsgh01234@gmail.com)
- id=3  스타보관소 (dlwodbs000@gmail.com)
- id=4  유진코리아몰 (dlwodbs7942@gmail.com)
- id=5  유진쇼핑몰 (rejoice666@naver.com)
- id=6  유진집 (rejoice999@naver.com)
- id=7  아이리스. (starvis7783@gmail.com)
- id=8  아이리스홈 (starvis7783@gmail.com[아이리스홈스토어]) — 복수아이디, 완전 별개 API
- id=9  스타라이프 (starvis8942@gmail.com)
- id=10 스타주노 (starvis9942@gmail.com)
- id=11 스타윈블리 (starvisi0914@gmail.com) — 구 스타쇼핑몰
- id=12 스타컴퍼니 (starvisi7942@gmail.com)
- id=13 스타쇼핑몰 (starvision0914@gmail.com) — 구 스타쇼핑(v)
- id=15 주노그노 (tmxkqlwus@gmail.com)
- id=16 유진문구 (tmxkqlwus@naver.com)
- id=17 장난감동산 (dlrmsgh0123@gmail.com[장난감동산]) — 유진컴퍼니 복수아이디

## API 오류 계정 (❌ 403 Forbidden)
- id=14 유진스타일 (starvision7942@gmail.com) — 앱 미승인 또는 스토어 연동 안 됨
- id=18 정성스런스토어 (starvisi999@gmail.com) — 계정 이용정지 중(판매정지)

## 크롤링 방식
- login_pw 있으면 Selenium 크롤 → 0건 시 API 폴백
- login_pw 없으면 Commerce API 직접 수집
- 락: 계정별 /tmp/smartstore_{id}.lock (동시 실행 가능)
- 엑셀: /home/rejoice888/PUBLIC/엑셀공유/쇼핑몰 계정 관리(20260629).xlsx

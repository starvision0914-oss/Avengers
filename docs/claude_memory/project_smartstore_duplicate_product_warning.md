---
name: smartstore-duplicate-product-warning
description: 스마트스토어 복수 스토어 간 중복 상품 등록 시 네이버 제재 위험
metadata: 
  node_type: memory
  type: project
  originSessionId: 60e3911b-54d5-4cdb-a29b-c366d7cee782
---

스마트스토어 계정 간 동일 상품 중복 등록 시 네이버 제재(판매정지 등) 위험.

**Why:** 아이리스.(id=7)과 아이리스홈스토어(id=8)는 같은 login_id(starvis7783@gmail.com)지만 완전히 별개 API를 사용하고, 두 스토어에 동일 상품을 올리면 제재 대상.

**How to apply:** 상품 수집/등록/추천 자동화 시 스마트스토어 계정 간 seller_management_code 또는 상품명 중복 체크 필수. 복수아이디 스토어(아이리스./아이리스홈) 간 상품 공유 금지.

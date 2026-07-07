---
name: project_smartstore_dual_login_dashboard_bug
description: "스마트스토어 대시보드가 같은 로그인 공유하는 두 계정(아이리스./아이리스홈스토어) 매출을 한쪽에만 몰아서 표시하던 버그, 수정완료(2026-07-07)"
metadata: 
  node_type: memory
  type: project
  originSessionId: c8272f73-4610-4a02-b107-7e70ef950e0e
---

아이리스.(SmartStoreAccount id=7)와 아이리스홈스토어(id=8)는 **같은 네이버 로그인(starvis7783@gmail.com)을 공유**하는 서로 다른 스토어 채널([[project_smartstore_duplicate_product_warning]] 참조). 대시보드(`apps/smartstore/views.py` DashboardView)가 `login_to_acc = {a.login_id: a for a in accounts_qs}`로 딕셔너리를 만들면서 **같은 로그인끼리 서로 덮어써서**, id 순서상 나중 것(아이리스홈스토어)이 이겨 아이리스.의 실제 매출(661건, 2,371만원)이 전부 아이리스홈스토어 행 아래로 잘못 합산되고, 아이리스.는 0으로 표시됨.

**Why**: `SalesRecord`는 로그인ID로만 SellerAccount를 매칭·생성(쇼핑몰명 기준 생성은 의도적으로 폐기됨, "쓰레기 셀러 자동생성 차단" 목적 — `apps/sales/views.py` 주석 참조). 이 설계 자체는 유지하되, 다행히 `SalesRecord.shop_name`에 원본 쇼핑몰명이 남아있어(654/661건이 정확히 "아이리스."), 대시보드 집계 시에만 (로그인, shop_name) 조합으로 재매칭하도록 수정.

**How to apply**: 같은 패턴(한 로그인에 여러 스토어/채널)이 다른 플랫폼(스마트스토어 복수채널 다른 계정)에도 있을 수 있음 — 특정 계정 매출이 0으로 보이는데 실제 SalesRecord엔 데이터가 있다면 이 버그를 의심. 수정은 `apps/smartstore/views.py` DashboardView에 반영 완료, PM2 재시작함. 아이리스홈스토어 자체는 매출 엑셀이 실제로 업로드된 적이 없어 진짜 0인 게 맞음(별도 건, 엑셀 업로드 필요).

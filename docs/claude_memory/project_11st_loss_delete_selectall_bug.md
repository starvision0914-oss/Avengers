---
name: project_11st_loss_delete_selectall_bug
description: 11번가 적자삭제 crawler가 검색결과 pre-checked 가정으로 select_all 생략 → real 실행 0건 삭제(무위)
metadata: 
  node_type: memory
  type: project
  originSessionId: e6d44da8-ed92-4870-82a7-b8f14310a58c
---

`crawlers/eleven_loss_delete.py`의 `run_delete`(real)는 "검색결과 그리드는 전체 체크된 상태로 표시됨 → select_all 누르면 해제됨"이라 가정하고(`_process_group` 256–257행) **select_all을 생략한 채 바로 판매중지/삭제를 클릭**한다.

실제로는 검색결과가 pre-checked가 아니어서, rejoice345 **real 실행(2026-06-11 23:22)에서 0건 삭제**:
- 판매중지 클릭 → alert `상품을 선택해주세요.`
- 삭제 클릭 → alert `선택된 항목이 없습니다.`
- 잔여검증 → `잔여 20행`(상품 그대로), 최종 `나머지삭제 0 / 실패 0`

추가 의심: 상품번호 9건 검색했는데 `그리드 20행` → `_paste_and_search`의 JS value-set+input/change 이벤트가 11st 검색을 실제 트리거 못 해 **검색 필터 미적용**(기본 20개 목록) 가능성.

안전: `res['deleted'] = (remaining==0)` 가드 덕분에 거짓 '삭제완료' 비고/St11LossDeleted 기록은 없었음(무위로 끝남, 데이터 손상 0).

**DOM 진단 확정(2026-06-12, crawlers/diag_loss_select.py 읽기전용)**: 상품조회 그리드가 **jQWidgets(jqx-grid)** 다.
- 6건 검색해도 grid_rowcount=20(기본 페이지) → `_paste_and_search`(XP_PRDNO JS value-set+검색클릭)가 **필터 미적용**.
- 검색 후 체크된 행 0개("이미 전체체크" 가정 거짓). 보이는 input 체크박스 4개는 행선택이 아니라 상태필터 `chkSelStatCd1~4`(판매중/중지/품절/금지).
- `XP_SELECTALL`이 잡는 전체선택은 `<input>`이 아니라 `<div class="jqx-checkbox-default…">` → JS `.click()`으로 jqx 내부 선택상태 안 바뀜.

**심층 진단(2026-06-12, diag_loss_select.py 4회 라이브)**:
- 검색칸 = `<textarea id="prdNo" name="prdNo">`(onkeypress=goNumCheck), 검색버튼 = `#btnSearch`(매칭은 자식 span/span).
- 진짜 데이터그리드 = jqx **`#dvdataGrid`**. jQuery/jqxGrid API 사용가능.
- **단일 근본원인: 검색이 그리드를 0행으로 둠.** textarea#prdNo에 상품번호 6개 세팅 + 진짜 `#btnSearch`.click() 해도 `jqxGrid('getdatainformation').rowscount=0`. 검색이 실행조차 안 됨(또는 검색조건 셀렉터/날짜범위 등 선행설정 필요). `_grid_rowcount=20`은 데이터행 아닌 딴 요소 카운트(거짓값).
- 버튼 핸들러: **삭제=`javascript:fnListDelete('U')`**(+doCommonStat NPOF017), **판매중지=`searchSumData('CLOSE')`**(+NPPS004).

**재확인(2026-06-12, tmxkql22 real)**: 판매금지10+품절3 real 실행 여전히 **0건 삭제**(banned 0/rest 0), "선택된 항목이 없습니다" 반복. 버그 지속. 단 **핵심 우회로**: 상품번호 검색(고장) 대신 **상태필터 체크박스 `chkSelStatCd1~4`(판매중/중지/품절/금지)로 검색**하면 그리드에 상태별 전체가 로드됨 → 상태기반 일괄삭제 경로가 product_no 검색보다 유망.

**다음 수정 단계**: ① 검색폼 reverse-engineer — 검색조건(상품번호 vs 판매자코드) 셀렉터·날짜범위 디폴트·`searchSumData()` JS 확인해 prdNo 리스트 검색이 grid에 데이터 들어오게. ② grid rowscount==대상수 검증 후 jqx 행선택(또는 페이지 자체 check-all). ③ 삭제는 `fnListDelete('U')` 직접 호출 가능성 검토. 인터랙티브 점검 권장. 동시크롤 금지([[feedback_crawling_rule]]). [[project_11st_loss_delete]] 보완. 진단스크립트: backend/crawlers/diag_loss_select.py(읽기전용).

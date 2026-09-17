"""지마켓 신규광고센터(adcenter.esmplus.com) 일자별 상세리포트 → 계정별 구글시트 업로드
(2026-09-17 사용자 요청). 9월부터는 구광고센터(ad.esmplus.com) AI(Remarketing) 리포트 대신
이 신규광고센터 데이터를 AI_KEY 스프레드시트의 계정별 워크시트('{login_id}', 기존과 동일한
이름)에 그대로 채운다 — 매일 자동 크론(gmarket_daily_gsheet.py)이 이 함수로 대체됨.

⚠️ '종합' 워크시트(CPC_KEY 스프레드시트)가 이 워크시트의 D열(광고비)/J열(판매자 전환 금액)을
IMPORTRANGE로 그대로 참조하고 있어서(2026-09-17 확인), fetch_daily_report_xlsx()가 그 두
컬럼 위치를 보존하도록 이미 재배치해서 반환한다 — 여기서 컬럼 순서를 다시 바꾸면 안 됨.

⚠️ 현재는 '이번달 1일~어제'만 채운다(신규광고센터 캘린더가 표시월 밖 선택을 지원 안 해서 —
월 경계를 넘는 범위는 아직 미구현). 10월로 넘어가면 9월 데이터를 덮어쓰지 않도록 누적
저장 로직이 추가로 필요함(다음 확장 과제)."""
from datetime import date, timedelta

from crawlers import gsheet_upload
from crawlers.gmarket_new_adcenter_control import fetch_daily_report_xlsx, NEWAD_DL

AI_KEY = '1vqer9yv5h0wGvH7a1hyT9f3WSaVVmhyx2wUltfkSOQc'   # AI매출업(일자별) — 9월부터 신규광고센터로 대체


def upload_gmarket_tab(driver, login_id, password, log_fn=None, spreadsheet=None):
    """신규광고센터 일자별 상세리포트를 '{login_id}' 워크시트(AI_KEY)에 업로드."""
    def log(m):
        if log_fn:
            log_fn(m)

    since = date.today().replace(day=1)
    until = date.today() - timedelta(days=1)
    if since > until:
        log(f'[신규광고센터gsheet:{login_id}] 이번달 1일 실행 — 조회 가능한 날짜 없음, 스킵')
        return False

    rows = fetch_daily_report_xlsx(driver, login_id, password, since, until, log_fn=log_fn)
    if not rows:
        log(f'[신규광고센터gsheet:{login_id}] 데이터 없음 — 업로드 스킵')
        return False

    ss = spreadsheet or gsheet_upload.open_spreadsheet(AI_KEY)
    return gsheet_upload.upload_rows(rows, login_id, ss, log=log)

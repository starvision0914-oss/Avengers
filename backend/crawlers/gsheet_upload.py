"""구글시트 업로드(선택) — 11번가 adoffice 보고서 CSV를 계정별 워크시트에 올린다.

기존 Windows GUI 스크립트(adoffice UI 클릭 → CSV 다운 → 구글시트)의 '구글시트 업로드' 부분을
서버 API 크롤(eleven_product_roas)에 통합한 것. 데이터 수집은 이미 API로 하므로 결과만 시트에 반영.

설정(환경변수):
  GSHEET_CREDENTIALS  서비스계정 json 경로 (기본: backend/credentials.json)
  GSHEET_11ST_KEY     대상 스프레드시트 key

전제: 스프레드시트가 서비스계정 이메일과 '편집자'로 공유돼 있어야 함.
실패해도 예외를 던지지 않음 → 크롤 본작업을 막지 않음.
"""
import csv as _csv
import io
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_CREDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
# 기존 Windows 스크립트가 쓰던 11번가 실적 스프레드시트(비밀 아님, 공유 권한으로 보호). env로 덮어쓰기 가능.
DEFAULT_KEY = '1Yo9jGwJDFwToeBKb5TX3_ilZPsQmtnvUme7LDh_7_-A'
_SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']


def _creds_path(p=None):
    return p or os.environ.get('GSHEET_CREDENTIALS', DEFAULT_CREDS)


def _key(k=None):
    return k or os.environ.get('GSHEET_11ST_KEY', DEFAULT_KEY)


def is_configured(creds_path=None, spreadsheet_key=None):
    """credentials 파일 + 스프레드시트 key 둘 다 있으면 True."""
    return bool(_key(spreadsheet_key)) and os.path.exists(_creds_path(creds_path))


def open_spreadsheet(spreadsheet_key=None, creds_path=None):
    """서비스계정으로 스프레드시트 1회 오픈(계정 루프 전 1회만 호출 권장)."""
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(_creds_path(creds_path), scopes=_SCOPES)
    return gspread.authorize(creds).open_by_key(_key(spreadsheet_key))


_MONTH_MARKER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.gsheet_month_marker.json')


def _marker_key(spreadsheet, title):
    return f'{getattr(spreadsheet, "id", "ss")}:{title}'


def _read_marker():
    import json
    try:
        with open(_MONTH_MARKER, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _write_marker(m):
    import json
    tmp = _MONTH_MARKER + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=0)
    os.replace(tmp, _MONTH_MARKER)


def archive_if_new_month(spreadsheet, title, year, month, log=print):
    """월별 시트를 clear 후 덮어쓰는 업로더용 보호장치(2026-09-30).
    upload_rows()는 워크시트를 clear()하고 새로 쓰므로, 달이 바뀐 첫 업로드에서 지난달 자료가 사라진다.
    '마지막으로 올린 달'을 마커 파일에 기록해 두었다가, 다른 달 데이터를 올리려 할 때 기존 시트를
    '{title}_{YYYYMM}' 탭으로 먼저 복제해 보관한다(셀 내용/날짜 형식에 의존하지 않음).
    반환: True=업로드 진행해도 됨 / False=보관 실패 → 덮어쓰지 말 것.
    마커가 없는 시트는 이번 달로 간주해 기록만 하고 통과(첫 등록)."""
    if spreadsheet is None:
        return True
    cur = f'{int(year):04d}{int(month):02d}'
    key = _marker_key(spreadsheet, title)
    marker = _read_marker()
    last = marker.get(key)
    if last is None:
        marker[key] = cur
        _write_marker(marker)
        return True
    if last == cur:
        return True
    try:
        import gspread
        arch = f'{title}_{last}'
        try:
            spreadsheet.worksheet(arch)
            log(f'[gsheet] {title}: 보관 탭 {arch} 이미 있음')
        except gspread.exceptions.WorksheetNotFound:
            try:
                ws = spreadsheet.worksheet(title)
            except gspread.exceptions.WorksheetNotFound:
                ws = None
            if ws is not None:
                ws.duplicate(new_sheet_name=arch)
                log(f'[gsheet] {title}: 지난달({last}) 시트를 {arch} 탭으로 보관')
        marker[key] = cur
        _write_marker(marker)
        return True
    except Exception as e:
        log(f'[gsheet] {title}: 지난달 시트 보관 실패 — 덮어쓰기 중단: {str(e)[:140]}')
        return False


def upload_rows(rows, worksheet_title, spreadsheet, log=print):
    """행 리스트(list of list)를 계정 워크시트(이름=login_id)에 clear 후 A1부터 raw 업로드.
    실패해도 False 반환(예외 안 던짐 → 본수집 비차단)."""
    if spreadsheet is None:
        return False
    try:
        import gspread
        if not rows:
            log(f'[gsheet] {worksheet_title}: 빈 데이터 — 스킵')
            return False
        rows = [[('' if c is None else c) for c in r] for r in rows]
        try:
            ws = spreadsheet.worksheet(worksheet_title)
            ws.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=worksheet_title,
                                           rows=max(1000, len(rows) + 10),
                                           cols=max(12, len(rows[0]) + 2))
        ws.update(rows, 'A1', raw=True)
        log(f'[gsheet] {worksheet_title}: {len(rows)}행 업로드')
        return True
    except Exception as e:
        log(f'[gsheet] {worksheet_title} 업로드 실패: {str(e)[:140]}')
        return False


def upload_csv(csv_text, worksheet_title, spreadsheet, log=print):
    """adoffice CSV 텍스트(콤마구분) → 계정 워크시트(이름=login_id). clear 후 A1부터 raw 업로드.
    spreadsheet: open_spreadsheet()로 받은 객체. 실패해도 False 반환(예외 안 던짐)."""
    if spreadsheet is None:
        return False
    try:
        import gspread
        rows = [r for r in _csv.reader(io.StringIO(csv_text or ''))]
        if not rows:
            log(f'[gsheet] {worksheet_title}: 빈 CSV — 스킵')
            return False
        try:
            ws = spreadsheet.worksheet(worksheet_title)
            ws.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=worksheet_title,
                                           rows=max(1000, len(rows) + 10),
                                           cols=max(26, len(rows[0]) + 2))
        ws.update(rows, 'A1', raw=True)
        log(f'[gsheet] {worksheet_title}: {len(rows)}행 업로드')
        return True
    except Exception as e:
        log(f'[gsheet] {worksheet_title} 업로드 실패: {str(e)[:140]}')
        return False

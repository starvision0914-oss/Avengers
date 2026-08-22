"""스마트스토어 '일자별' 광고비(SmartStoreAdCost, CPC만) → 구글시트 업로드.
지마켓 gmarket_daily_gsheet.py와 동일 패턴(날짜별 행 + 누락일 빈행 + 합계행) — 이미 수집된
DB 데이터를 올린다(재수집 없음). 새 스프레드시트 없이 지마켓이 쓰는 CPC 스프레드시트를 그대로
재사용해 계정별(store_name) 워크시트로 추가한다(사용자 요청 2026-08-22).

⚠️ 서버 서비스계정(credentials.json 이메일)이 대상 스프레드시트에 '편집자'로
   공유돼 있어야 업로드된다. 미공유 시 upload_rows가 False 반환(본수집 비차단).
"""
import calendar
import logging
from datetime import date

from crawlers import gsheet_upload
from crawlers.gmarket_adcost_gsheet import CPC_KEY  # 지마켓과 같은 CPC 스프레드시트 재사용

logger = logging.getLogger(__name__)

HEADER = ['날짜', '노출수', '클릭수', '광고비', '전환수', '전환금액']


def _log(fn, m):
    logger.info(m)
    if fn:
        fn(m)


def target_period(today=None):
    """1일=전월 / 그 외=당월 → (year, month). 지마켓 일자별과 동일 규칙."""
    today = today or date.today()
    if today.day == 1:
        return (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    return today.year, today.month


def _rows_for_account(account, year, month):
    """한 계정의 CPC 일자별 행(누락일=빈행) + 합계행. 데이터 전무하면 None."""
    from apps.smartstore.models import SmartStoreAdCost

    last_day = calendar.monthrange(year, month)[1]
    by_date = {
        r['date']: r for r in
        SmartStoreAdCost.objects.filter(
            account=account, ad_type='cpc', date__year=year, date__month=month,
        ).values('date', 'impression', 'click', 'cost', 'conversion_count', 'conversion_amount')
    }
    if not by_date:
        return None

    data = [HEADER]
    t_imp = t_clk = t_cost = t_conv = t_amt = 0
    for d in range(1, last_day + 1):
        cur = date(year, month, d)
        r = by_date.get(cur)
        if r:
            row = [cur.strftime('%Y-%m-%d'), r['impression'], r['click'], r['cost'],
                   r['conversion_count'], r['conversion_amount']]
            t_imp += r['impression']; t_clk += r['click']; t_cost += r['cost']
            t_conv += r['conversion_count']; t_amt += r['conversion_amount']
        else:
            row = [cur.strftime('%Y-%m-%d'), '', '', '', '', '']
        data.append(row)
    data.append(['합계', t_imp, t_clk, t_cost, t_conv, t_amt])
    return data


def run_all_accounts(log_fn=None, account_filter=None, gsheet=True, year=None, month=None):
    """대상 월 SmartStoreAdCost(CPC)를 지마켓 CPC 스프레드시트에 계정별(store_name) 워크시트로 업로드."""
    from apps.smartstore.models import SmartStoreAccount

    if year is None or month is None:
        year, month = target_period()

    accounts = list(SmartStoreAccount.objects.filter(is_active=True))
    if account_filter:
        accounts = [a for a in accounts if a.login_id in account_filter or a.store_name in account_filter]

    _log(log_fn, f'[naver-daily-gsheet] {year}-{month:02d} 대상 계정 {len(accounts)}개 / gsheet={gsheet}')

    ss = gsheet_upload.open_spreadsheet(CPC_KEY) if gsheet else None

    result = {'year': year, 'month': month, 'accounts': len(accounts), 'uploaded': 0, 'skipped': 0}
    for acc in accounts:
        rows = _rows_for_account(acc, year, month)
        if not rows:
            result['skipped'] += 1
            continue
        title = acc.store_name or acc.login_id
        if gsheet:
            ok = gsheet_upload.upload_rows(rows, title, ss, log=lambda m: _log(log_fn, m))
            if ok:
                result['uploaded'] += 1
        else:
            _log(log_fn, f'  [{title}] {len(rows) - 2}일 (업로드 생략)')
    _log(log_fn, f'[naver-daily-gsheet] 완료 {result}')
    return result

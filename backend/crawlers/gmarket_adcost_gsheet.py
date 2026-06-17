"""지마켓 상품별 광고비(GmarketProductAdCost) → 계정별 구글시트 업로드.

11번가 기간별 gsheet와 동일 패턴 — Selenium 재다운로드 없이, 이미 수집된 DB 데이터를 올린다.
- AI / CPC 를 서로 다른 스프레드시트에 분리 (워크시트명 = 계정 login_id)
- 기간: 매월 1일 = 전월, 그 외 = 당월
- crawl_gmarket_ad_report(매일 08:00) 직후 호출 → 수집되면 곧바로 시트 반영

⚠️ 서버 서비스계정(credentials.json 이메일)이 아래 두 스프레드시트에 '편집자'로
   공유돼 있어야 업로드된다. 미공유 시 upload_rows가 False 반환(본수집 비차단).
"""
import logging
from datetime import date

from crawlers import gsheet_upload

logger = logging.getLogger(__name__)

# 사용자 제공 스프레드시트 (스탠드얼론 스크립트와 동일)
AI_KEY = '1vqer9yv5h0wGvH7a1hyT9f3WSaVVmhyx2wUltfkSOQc'    # AI매출업 저장
CPC_KEY = '10YWiqQcDdzij_eTmoTFPN9hGe2h3xsWlkIaKG4p4m80'   # CPC 저장

CPC_HEADER = ['상품번호', '그룹명', '사이트', '노출수', '클릭수', '평균클릭비용',
              '광고비', '구매수', '구매금액', '전환율(%)', 'ROAS(%)']
AI_HEADER = ['상품번호', '그룹명', '노출수', '클릭수', '평균클릭비용',
             '광고비', '구매수', '구매금액', '전환율(%)', 'ROAS(%)']


def _log(fn, m):
    logger.info(m)
    if fn:
        fn(m)


def target_period(today=None):
    """1일=전월 / 그 외=당월 → (year, month)."""
    today = today or date.today()
    if today.day == 1:
        return (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    return today.year, today.month


def _rows_for(ad_type, login_id, year, month):
    """한 계정·한 광고유형의 상품별 행 + 합계행. 데이터 없으면 None."""
    from apps.cpc.models import GmarketProductAdCost
    qs = (GmarketProductAdCost.objects
          .filter(login_id=login_id, ad_type=ad_type, year=year, month=month)
          .order_by('-cost'))
    is_cpc = (ad_type == 'cpc')
    data = [CPC_HEADER if is_cpc else AI_HEADER]
    t_imp = t_clk = t_cost = t_ord = t_amt = 0
    for o in qs:
        if is_cpc:
            data.append([o.product_no, o.group_name, o.site, o.impressions, o.clicks,
                         o.avg_click_cost, o.cost, o.orders, o.conv_amount,
                         str(o.conv_rate), str(o.roas)])
        else:
            data.append([o.product_no, o.group_name, o.impressions, o.clicks,
                         o.avg_click_cost, o.cost, o.orders, o.conv_amount,
                         str(o.conv_rate), str(o.roas)])
        t_imp += o.impressions; t_clk += o.clicks; t_cost += o.cost
        t_ord += o.orders; t_amt += o.conv_amount
    if len(data) == 1:
        return None
    if is_cpc:
        data.append(['합계', '', '', t_imp, t_clk, '', t_cost, t_ord, t_amt, '', ''])
    else:
        data.append(['합계', '', t_imp, t_clk, '', t_cost, t_ord, t_amt, '', ''])
    return data


def run_all_accounts(log_fn=None, account_filter=None, gsheet=True, year=None, month=None):
    """대상 (year,month) GmarketProductAdCost 를 계정별 구글시트(AI/CPC 분리)에 업로드."""
    from apps.cpc.models import GmarketProductAdCost
    if year is None or month is None:
        year, month = target_period()

    base = GmarketProductAdCost.objects.filter(year=year, month=month)
    if account_filter:
        base = base.filter(login_id__in=account_filter)
    login_ids = sorted(set(base.values_list('login_id', flat=True)))
    _log(log_fn, f'[gmkt-adcost-gsheet] {year}-{month:02d} 대상 계정 {len(login_ids)}개 / gsheet={gsheet}')

    ss_cpc = ss_ai = None
    if gsheet:
        ss_cpc = gsheet_upload.open_spreadsheet(CPC_KEY)
        ss_ai = gsheet_upload.open_spreadsheet(AI_KEY)

    result = {'year': year, 'month': month, 'accounts': len(login_ids),
              'cpc_uploaded': 0, 'ai_uploaded': 0, 'skipped': 0}
    for lid in login_ids:
        for ad_type, ss, key in (('cpc', ss_cpc, 'cpc_uploaded'), ('ai', ss_ai, 'ai_uploaded')):
            rows = _rows_for(ad_type, lid, year, month)
            if not rows:
                result['skipped'] += 1
                continue
            if gsheet:
                ok = gsheet_upload.upload_rows(rows, lid, ss, log=lambda m: _log(log_fn, m))
                if ok:
                    result[key] += 1
            else:
                _log(log_fn, f'  [{lid}/{ad_type}] {len(rows) - 2}개 상품 (업로드 생략)')
    _log(log_fn, f'[gmkt-adcost-gsheet] 완료 {result}')
    return result

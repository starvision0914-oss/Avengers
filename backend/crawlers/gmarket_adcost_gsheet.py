"""지마켓 CPC/AI 구글시트 재구성 (2026-09-10, 사용자 지시).

기존엔 두 스프레드시트(CPC_KEY/AI_KEY)에 '일자별 계정합계'(gmarket_daily_gsheet.py)를
올렸는데, 신규광고센터(adcenter.esmplus.com) 이관 이후에도 AI/CPC가 제대로 안 잡혀서
사용자가 아래처럼 용도를 재정의했다 — 새 탭을 만들지 않고 기존 두 스프레드시트의
계정별 워크시트(이름=login_id) 내용을 통째로 교체한다:

- CPC_KEY 스프레드시트 = 지마켓 "신규광고센터" 캠페인별 리포트(오늘자) — 광고비/매출액/수익율.
  신규광고센터는 캠페인 단위로만 잡혀 상품번호가 없어(product_no 필드 자체가 없음)
  상품별로 쪼갤 수 없다 — 그래서 이 시트는 계정 단위 캠페인 목록으로 유지.
- AI_KEY 스프레드시트 = "옥션(Auction)" 광고비(AI+CPC 합산) 상품별 리포트.
  옥션은 신규광고센터로 안 옮겨가서(지마켓 전용) 계속 구광고센터 상품별 리포트
  (GmarketProductAdCost)만으로 집계 가능 — ai_type='ai'(사실상 옥션 AI, 지마켓 AI는
  이관후 0원 고정이라 안 섞임)과 ad_type='cpc' & site='A'(옥션 CPC)를 합쳐서 보여준다.

crawl_gmarket_ad_report(--with-gsheet)가 계정별 상품광고비(GmarketProductAdCost)를
막 저장한 직후 호출한다 — 신규광고센터 쪽은 별도로 cron_gmarket_cost_hourly.sh가
매시간 갱신해두는 GmarketNewAdCost를 그대로 읽기만 한다(여기서 재수집 안 함).

⚠️ 서버 서비스계정(credentials.json 이메일)이 아래 두 스프레드시트에 '편집자'로
   공유돼 있어야 업로드된다. 미공유 시 upload_rows가 False 반환(본수집 비차단).
"""
import logging
from datetime import date

from django.db.models import Q

from crawlers import gsheet_upload

logger = logging.getLogger(__name__)

AI_KEY = '1vqer9yv5h0wGvH7a1hyT9f3WSaVVmhyx2wUltfkSOQc'    # 옥션 AI+CPC 상품별
CPC_KEY = '10YWiqQcDdzij_eTmoTFPN9hGe2h3xsWlkIaKG4p4m80'   # 지마켓 신규광고센터 캠페인별

NEWAD_HEADER = ['캠페인명', '유형', '광고비', '매출액', '수익율(%)']
AUCTION_HEADER = ['상품번호', '그룹명', '유형', '노출수', '클릭수', '평균클릭비용',
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


def _newad_rows(login_id):
    """지마켓 신규광고센터 오늘자 캠페인별 행 + 합계. 데이터 없으면 None."""
    from apps.cpc.models import GmarketNewAdCost
    from django.utils import timezone

    today = timezone.localdate()
    qs = (GmarketNewAdCost.objects
          .filter(login_id=login_id, use_date=today)
          .order_by('-cost'))
    data = [NEWAD_HEADER]
    t_cost = t_conv = 0
    for o in qs:
        data.append([o.campaign_name, 'AI' if o.is_ai else 'CPC', o.cost, o.conv_amount, str(o.roas)])
        t_cost += o.cost
        t_conv += o.conv_amount
    if len(data) == 1:
        return None
    roas_total = round(t_conv * 100.0 / t_cost, 2) if t_cost else 0
    data.append(['합계', '', t_cost, t_conv, str(roas_total)])
    return data


def _auction_rows(login_id, year, month):
    """옥션 AI+CPC 상품별 행 + 합계. 데이터 없으면 None."""
    from apps.cpc.models import GmarketProductAdCost

    qs = (GmarketProductAdCost.objects
          .filter(Q(ad_type='ai') | Q(ad_type='cpc', site='A'),
                  login_id=login_id, year=year, month=month)
          .order_by('-cost'))
    data = [AUCTION_HEADER]
    t_imp = t_clk = t_cost = t_ord = t_amt = 0
    for o in qs:
        data.append([o.product_no, o.group_name, 'AI' if o.ad_type == 'ai' else 'CPC',
                     o.impressions, o.clicks, o.avg_click_cost, o.cost, o.orders,
                     o.conv_amount, str(o.conv_rate), str(o.roas)])
        t_imp += o.impressions; t_clk += o.clicks; t_cost += o.cost
        t_ord += o.orders; t_amt += o.conv_amount
    if len(data) == 1:
        return None
    data.append(['합계', '', '', t_imp, t_clk, '', t_cost, t_ord, t_amt, '', ''])
    return data


def run_all_accounts(log_fn=None, account_filter=None, gsheet=True, year=None, month=None):
    """전 계정 대상으로 CPC_KEY(신규센터 캠페인별)·AI_KEY(옥션 AI+CPC 상품별) 갱신."""
    from apps.cpc.models import GmarketProductAdCost, GmarketNewAdCost
    if year is None or month is None:
        year, month = target_period()

    auction_base = GmarketProductAdCost.objects.filter(
        Q(ad_type='ai') | Q(ad_type='cpc', site='A'), year=year, month=month)
    if account_filter:
        auction_base = auction_base.filter(login_id__in=account_filter)
    newad_base = GmarketNewAdCost.objects.all()
    if account_filter:
        newad_base = newad_base.filter(login_id__in=account_filter)

    login_ids = sorted(set(auction_base.values_list('login_id', flat=True))
                        | set(newad_base.values_list('login_id', flat=True)))
    _log(log_fn, f'[gmkt-adcost-gsheet] {year}-{month:02d} 대상 계정 {len(login_ids)}개 / gsheet={gsheet}')

    ss_cpc = ss_ai = None
    if gsheet:
        ss_cpc = gsheet_upload.open_spreadsheet(CPC_KEY)
        ss_ai = gsheet_upload.open_spreadsheet(AI_KEY)

    result = {'year': year, 'month': month, 'accounts': len(login_ids),
              'newad_uploaded': 0, 'auction_uploaded': 0, 'skipped': 0}
    for lid in login_ids:
        newad = _newad_rows(lid)
        if newad:
            if gsheet:
                if gsheet_upload.upload_rows(newad, lid, ss_cpc, log=lambda m: _log(log_fn, m)):
                    result['newad_uploaded'] += 1
            else:
                _log(log_fn, f'  [{lid}/신규센터] {len(newad) - 2}개 캠페인 (업로드 생략)')
        else:
            result['skipped'] += 1

        auction = _auction_rows(lid, year, month)
        if auction:
            if gsheet:
                if gsheet_upload.upload_rows(auction, lid, ss_ai, log=lambda m: _log(log_fn, m)):
                    result['auction_uploaded'] += 1
            else:
                _log(log_fn, f'  [{lid}/옥션] {len(auction) - 2}개 상품 (업로드 생략)')
        else:
            result['skipped'] += 1
    _log(log_fn, f'[gmkt-adcost-gsheet] 완료 {result}')
    return result


def run_for_account(login_id, log_fn=None, gsheet=True, year=None, month=None,
                     ss_cpc=None, ss_ai=None, **_ignored):
    """계정 1개 갱신 — crawl_gmarket_ad_report(--with-gsheet)의 계정 루프에서 호출.
    **_ignored로 예전 daily_gsheet 호출부가 넘기던 driver 등 불필요 인자를 무시한다."""
    from apps.cpc.models import GmarketProductAdCost
    if year is None or month is None:
        year, month = target_period()

    result = {}
    newad = _newad_rows(login_id)
    if newad:
        if gsheet and ss_cpc is not None:
            ok = gsheet_upload.upload_rows(newad, login_id, ss_cpc, log=lambda m: _log(log_fn, m))
            result['newad_uploaded'] = ok
        else:
            result['newad_uploaded'] = False
    auction = _auction_rows(login_id, year, month)
    if auction:
        if gsheet and ss_ai is not None:
            ok = gsheet_upload.upload_rows(auction, login_id, ss_ai, log=lambda m: _log(log_fn, m))
            result['auction_uploaded'] = ok
        else:
            result['auction_uploaded'] = False
    return result

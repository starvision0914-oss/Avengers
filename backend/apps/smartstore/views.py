import calendar
import csv
import datetime
import io
from datetime import date

from django.db.models import Sum, Count, Q, Max, F
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import (SmartStoreAccount, SmartStoreSales, SmartStoreAdCost,
                     SmartStoreProduct, SmartStoreCrawlLog, NaverAdProductReport,
                     SmartStoreCleanViolation, NaverSearchTermReport)
from apps.sales.models import SalesRecord

_NAVER_STATUS_LABEL = {
    'SALE': '판매중', 'SUSPENSION': '판매중지',
    'OUTOFSTOCK': '품절', 'WAIT': '승인대기', 'PROHIBITION': '판매금지',
}


def _account_serial(a):
    return {
        'id': a.id,
        'login_id': a.login_id,
        'store_name': a.store_name,
        'store_slug': a.store_slug,
        'display_name': a.display_name or a.store_name,
        'memo': a.memo,
        'has_pw': bool(a.login_pw),
        'has_api_key': bool(a.commerce_api_key and a.commerce_secret_key),
        'has_naver_ad': bool(a.naver_ad_customer_id and a.naver_ad_access_license and a.naver_ad_secret_key),
        'has_naver_ai': bool(a.naver_ad_ai_customer_id and a.naver_ad_ai_access_license and a.naver_ad_ai_secret_key),
        'naver_ad_customer_id': a.naver_ad_customer_id,
        'naver_ad_ai_customer_id': a.naver_ad_ai_customer_id,
        'naver_ad_account_id': a.naver_ad_account_id,
        'naver_ad_login_id': a.naver_ad_login_id,
        'purchase_rate': a.purchase_rate,
        'is_active': a.is_active,
        'display_order': a.display_order,
    }


# ──── 계정 ────

class AccountListView(APIView):
    def get(self, request):
        accounts = SmartStoreAccount.objects.filter(is_active=True).order_by('display_order')
        return Response([_account_serial(a) for a in accounts])

    def post(self, request):
        d = request.data
        obj = SmartStoreAccount.objects.create(
            login_id=d['login_id'],
            login_pw=d.get('login_pw', ''),
            store_name=d['store_name'],
            store_slug=d.get('store_slug', ''),
            display_name=d.get('display_name', ''),
            memo=d.get('memo', ''),
            commerce_api_key=d.get('commerce_api_key', ''),
            commerce_secret_key=d.get('commerce_secret_key', ''),
            display_order=d.get('display_order', 99),
        )
        return Response({'id': obj.id, 'store_name': obj.store_name}, status=201)


class AccountDetailView(APIView):
    def patch(self, request, pk):
        try:
            obj = SmartStoreAccount.objects.get(pk=pk)
        except SmartStoreAccount.DoesNotExist:
            return Response({'error': 'not found'}, status=404)

        for field in ('login_id', 'login_pw', 'store_name', 'store_slug',
                      'display_name', 'memo', 'commerce_api_key', 'commerce_secret_key',
                      'naver_ad_customer_id', 'naver_ad_access_license', 'naver_ad_secret_key',
                      'naver_ad_ai_customer_id', 'naver_ad_ai_access_license', 'naver_ad_ai_secret_key',
                      'naver_ad_account_id', 'naver_ad_login_id',
                      'purchase_rate', 'is_active', 'display_order'):
            if field in request.data:
                setattr(obj, field, request.data[field])
        obj.save()
        return Response({'ok': True})

    def delete(self, request, pk):
        SmartStoreAccount.objects.filter(pk=pk).update(is_active=False)
        return Response({'ok': True})


# ──── 대시보드 통계 ────

class DashboardView(APIView):
    def get(self, request):
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        account_ids = request.query_params.getlist('account_id')

        if not start or not end:
            today = datetime.date.today()
            end = today - datetime.timedelta(days=1)
            start = end.replace(day=1)  # end 기준 월 1일 (월초=오늘이면 전월 마지막날 기준)
        else:
            start = datetime.date.fromisoformat(start)
            end = datetime.date.fromisoformat(end)

        # SalesRecord를 주 매출 소스로 사용 (11번가/지마켓 대시보드와 동일)
        accounts_qs = SmartStoreAccount.objects.filter(is_active=True)
        acc_info = {a.id: (a.display_name or a.store_name, a.login_id) for a in accounts_qs}

        # 로그인 하나를 여러 스토어(채널)가 공유하는 경우(예: 아이리스./아이리스홈스토어가
        # 둘 다 starvis7783@gmail.com) 대비 — (로그인, 스토어명) 조합으로 우선 매칭하고,
        # 그 로그인에 계정이 1개뿐이면 로그인만으로도 매칭(과거처럼 동작).
        # ※ 예전엔 login_id만으로 dict를 만들어 같은 로그인끼리 서로 덮어써서
        #    한쪽 계정 매출이 다른 계정 아래로 잘못 합산되는 버그가 있었음(2026-07-06 수정).
        login_store_to_acc = {}
        login_counts = {}
        for a in accounts_qs:
            login_counts[a.login_id] = login_counts.get(a.login_id, 0) + 1
        login_single_acc = {}
        for a in accounts_qs:
            login_store_to_acc[(a.login_id, (a.store_name or '').strip())] = a
            if login_counts[a.login_id] == 1:
                login_single_acc[a.login_id] = a

        sr_qs = SalesRecord.objects.filter(
            platform='smartstore',
            order_date__gte=start,
            order_date__lte=end,
        )

        by_account = {}
        for r in sr_qs.values('seller__seller_id', 'shop_name').annotate(
            sales=Sum('total_price'),
            commission=Sum('commission'),
            cogs=Sum('cost'),
            orders=Count('id'),
        ):
            sid = r['seller__seller_id']
            shop = (r['shop_name'] or '').strip()
            acc = login_store_to_acc.get((sid, shop)) or login_single_acc.get(sid)
            if not acc:
                continue
            if account_ids and str(acc.id) not in account_ids:
                continue
            sales = r['sales'] or 0
            commission = r['commission'] or 0
            cogs = r['cogs'] or 0
            orders = r['orders'] or 0
            if acc.id in by_account:
                prev = by_account[acc.id]
                prev['sales'] += sales
                prev['settlement'] += sales - commission
                prev['orders'] += orders
                prev['commission'] += commission
                prev['cogs'] += cogs
            else:
                by_account[acc.id] = {
                    'sales': sales,
                    'settlement': sales - commission,
                    'orders': orders,
                    'commission': commission,
                    'cogs': cogs,
                    'ad_cost': 0, 'ad_cpc': 0, 'ad_ai': 0,
                }

        ad_qs = SmartStoreAdCost.objects.filter(date__gte=start, date__lte=end)
        if account_ids:
            ad_qs = ad_qs.filter(account_id__in=account_ids)

        for row in ad_qs.values('account_id', 'ad_type').annotate(cost=Sum('cost')):
            aid = row['account_id']
            if aid not in by_account:
                by_account[aid] = {'sales': 0, 'settlement': 0, 'orders': 0, 'commission': 0, 'cogs': 0, 'ad_cost': 0, 'ad_cpc': 0, 'ad_ai': 0}
            c = row['cost'] or 0
            by_account[aid]['ad_cost'] += c
            if row['ad_type'] == 'cpc':
                by_account[aid]['ad_cpc'] += c
            elif row['ad_type'] == 'ai':
                by_account[aid]['ad_ai'] += c

        # 매출/광고비 없는 계정도 전부 포함
        for acc in accounts_qs:
            if account_ids and str(acc.id) not in account_ids:
                continue
            if acc.id not in by_account:
                by_account[acc.id] = {'sales': 0, 'settlement': 0, 'orders': 0, 'commission': 0, 'cogs': 0, 'ad_cost': 0, 'ad_cpc': 0, 'ad_ai': 0}

        acc_naver_ad = {a.id: a.naver_ad_account_id for a in accounts_qs}

        account_list = []
        for aid, row in by_account.items():
            name, login_id = acc_info.get(aid, (str(aid), ''))
            sales = row['sales']
            ad = row['ad_cost']
            account_list.append({
                'account_id': aid,
                'account_name': name,
                'naver_ad_account_id': acc_naver_ad.get(aid),
                **row,
                'excel_revenue': sales,
                'roas': round(sales / ad * 100, 1) if ad > 0 else None,
            })
        account_list.sort(key=lambda x: x['sales'], reverse=True)

        total_sales = sum(r['sales'] for r in by_account.values())
        total_settlement = sum(r['settlement'] for r in by_account.values())
        total_orders = sum(r['orders'] for r in by_account.values())
        total_cogs = sum(r['cogs'] for r in by_account.values())

        ad_by_type = {}
        for row in ad_qs.values('ad_type').annotate(
            cost=Sum('cost'), clicks=Sum('click'), impressions=Sum('impression'), conversion=Sum('conversion_amount')
        ):
            ad_by_type[row['ad_type']] = row
        total_cpc = ad_by_type.get('cpc', {}).get('cost') or 0
        total_ai  = ad_by_type.get('ai',  {}).get('cost') or 0
        total_ad  = total_cpc + total_ai + (ad_by_type.get('brand', {}).get('cost') or 0)
        total_clicks = sum(v.get('clicks') or 0 for v in ad_by_type.values())
        total_conversion = sum(v.get('conversion') or 0 for v in ad_by_type.values())
        roas = round(total_sales / total_ad * 100, 1) if total_ad > 0 else None

        return Response({
            'period': {'start': str(start), 'end': str(end)},
            'summary': {
                'total_sales': total_sales,
                'total_cancel': 0,
                'total_return': 0,
                'total_settlement': total_settlement,
                'total_orders': total_orders,
                'total_ad_cost': total_ad,
                'total_ad_cpc': total_cpc,
                'total_ad_ai': total_ai,
                'total_cogs': total_cogs,
                'total_excel_revenue': total_sales,
                'total_clicks': total_clicks,
                'total_conversion': total_conversion,
                'roas': roas,
            },
            'by_account': account_list,
            'daily': [],
        })


# ──── 상품 목록 ────

class ProductListView(APIView):
    def get(self, request):
        from django.core.cache import cache
        from django.db.models import F

        account_id = request.query_params.get('account_id', '0')
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 50))
        status = request.query_params.get('status', '')
        search = request.query_params.get('search', '')
        ownerclan_soldout = request.query_params.get('ownerclan_soldout')
        needs_check = request.query_params.get('needs_check') in ('1', 'true', 'True')
        no_match = request.query_params.get('no_match') in ('1', 'true', 'True')
        high_margin = request.query_params.get('high_margin') in ('1', 'true', 'True')
        needs_check_pct_raw = request.query_params.get('needs_check_pct')
        needs_check_pct = int(needs_check_pct_raw) if needs_check_pct_raw not in (None, '') else 10
        needs_check_mult = (100 - min(max(needs_check_pct, 1), 99)) / 100.0

        qs = SmartStoreProduct.objects.select_related('account')
        if account_id and account_id != '0':
            qs = qs.filter(account_id=account_id)
        if status:
            qs = qs.filter(status_type=status)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(seller_management_code__icontains=search))
        if ownerclan_soldout is not None:
            qs = qs.filter(ownerclan_soldout=ownerclan_soldout == '1')

        # 확인필요/미매칭/고단가 — 11번가/지마켓과 동일 패턴(W코드+구매원가 매칭, status_type=SALE만).
        # (2026-08-21 재정의: 확인필요=마켓가 대비 10%+ 낮음, 미매칭=카탈로그에 코드 자체가 없음(라이브상태 무관),
        #  고단가=60만원 이상 또는 마켓가 대비 50%+ 비쌈)
        nc_key = f"ss_needs:{account_id}:{status}:{search}:{needs_check_pct}"
        needs_total = cache.get(nc_key)
        if needs_total is None:
            needs_total = qs.filter(purchase_cost__gt=0, sale_price__lte=F('purchase_cost') * needs_check_mult).count()
            cache.set(nc_key, needs_total, 120)
        nm_key = f"ss_nomatch:{account_id}:{status}:{search}"
        no_match_total = cache.get(nm_key)
        if no_match_total is None:
            no_match_total = (
                qs.filter(seller_management_code__iregex=r'^(WDM_|AUTO_)?W', purchase_cost__isnull=True, status_type='SALE')
                  .exclude(seller_management_code__regex=r'[가-힣]')
            ).count()
            cache.set(nm_key, no_match_total, 120)
        hm_key = f"ss_highmargin:{account_id}:{status}:{search}"
        high_margin_total = cache.get(hm_key)
        if high_margin_total is None:
            high_margin_total = qs.filter(
                Q(sale_price__gte=600000) | Q(purchase_cost__gt=0, sale_price__gte=F('purchase_cost') * 1.5)
            ).count()
            cache.set(hm_key, high_margin_total, 120)

        if needs_check:
            qs = qs.filter(purchase_cost__gt=0, sale_price__lte=F('purchase_cost') * needs_check_mult)
        elif no_match:
            qs = (
                qs.filter(seller_management_code__iregex=r'^(WDM_|AUTO_)?W', purchase_cost__isnull=True, status_type='SALE')
                  .exclude(seller_management_code__regex=r'[가-힣]')
            )
        elif high_margin:
            qs = qs.filter(Q(sale_price__gte=600000) | Q(purchase_cost__gt=0, sale_price__gte=F('purchase_cost') * 1.5))

        if needs_check and not no_match and not high_margin:
            total = needs_total
        elif no_match:
            total = no_match_total
        elif high_margin:
            total = high_margin_total
        else:
            total = qs.count()
        offset = (page - 1) * per_page
        items = qs.order_by('-id')[offset:offset + per_page]

        data = []
        for p in items:
            data.append({
                'id': p.id,
                'account_id': p.account_id,
                'store_name': p.account.display_name or p.account.store_name,
                'product_no': p.product_no,
                'channel_product_no': p.channel_product_no,
                'name': p.name,
                'sale_price': p.sale_price,
                'stock_quantity': p.stock_quantity,
                'status_type': p.status_type,
                'seller_management_code': p.seller_management_code,
                'category_id': p.category_id,
                'product_image_url': p.product_image_url,
                'ownerclan_soldout': p.ownerclan_soldout,
                'synced_at': p.synced_at.isoformat(),
                'purchase_cost': p.purchase_cost,
                'cost_diff': p.cost_diff,
                'cost_pct': round(p.sale_price / p.purchase_cost * 100, 1) if p.purchase_cost else None,
            })
        from apps.cpc.eleven_my_product_service import _attach_l_status
        _attach_l_status(data, code_field='seller_management_code')

        return Response({
            'items': data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total else 0,
            'needs_check_total': needs_total,
            'no_match_total': no_match_total,
            'high_margin_total': high_margin_total,
        })


class PriceMatchPreviewView(APIView):
    """확인필요(역마진)+고단가 상품의 판매가를 예비상품 마켓가(purchase_cost, 이미 오너클랜 마켓가로
    동기화돼 있음)로 맞추면 몇 개가 얼마→얼마로 바뀌는지 미리보기(실제 변경 없음, 2026-08-22)."""
    def get(self, request):
        pct_raw = request.query_params.get('pct')
        pct = int(pct_raw) if pct_raw not in (None, '') else 10
        mult = (100 - min(max(pct, 1), 99)) / 100.0

        qs = (SmartStoreProduct.objects.select_related('account')
              .filter(status_type='SALE', purchase_cost__gt=0)
              .filter(Q(sale_price__lte=F('purchase_cost') * mult) |
                      Q(sale_price__gte=F('purchase_cost') * 1.5) |
                      Q(sale_price__gte=600000))
              .order_by('-id'))

        total = qs.count()
        rows = []
        for p in qs[:500]:
            rows.append({
                'id': p.id,
                'account_name': p.account.display_name or p.account.store_name,
                'product_no': p.product_no,
                'name': p.name,
                'current_price': p.sale_price,
                'target_price': p.purchase_cost,
                'diff': p.purchase_cost - p.sale_price,
            })
        return Response({'total': total, 'rows': rows, 'preview_limit': 500})


# ──── 상품 동기화 (네이버 커머스 API) ────

class ProductSyncView(APIView):
    def post(self, request):
        account_id = request.data.get('account_id')
        if not account_id:
            return Response({'error': 'account_id 필수'}, status=400)

        try:
            account = SmartStoreAccount.objects.get(pk=account_id, is_active=True)
        except SmartStoreAccount.DoesNotExist:
            return Response({'error': '계정 없음'}, status=404)

        from .services.naver_api import sync_products_api
        result = sync_products_api(account)

        if 'error' in result:
            return Response(result, status=400)
        return Response(result)


# ──── 상품 통계 ────

class ProductStatsView(APIView):
    def get(self, request):
        account_id = request.query_params.get('account_id', '0')

        # 전체 또는 단일 계정 (DELETED=크롤 3일+ 누락 추정삭제 — 대시보드엔 안 보이게 제외.
        # 상품번호→판매자코드 매핑은 ProductCodeArchive 보존고에 영구보관되므로 데이터 유실 아님)
        if account_id and account_id != '0':
            qs = SmartStoreProduct.objects.filter(account_id=account_id).exclude(status_type='DELETED')
            stats = qs.values('status_type').annotate(cnt=Count('id'))
            total = qs.filter(status_type='SALE').count()   # 등록상품(헤드라인)=판매중만
            last_synced = qs.aggregate(ls=Max('synced_at'))['ls']
            by_status = {r['status_type']: r['cnt'] for r in stats}
            return Response({
                'total': total,
                'by_status': by_status,
                'last_synced_at': last_synced.isoformat() if last_synced else None,
            })

        # 전체 계정 합산
        qs = SmartStoreProduct.objects.exclude(status_type='DELETED')
        stats = qs.values('status_type').annotate(cnt=Count('id'))
        by_status = {r['status_type']: r['cnt'] for r in stats}
        total = by_status.get('SALE', 0)   # 등록상품(헤드라인)=판매중만

        # 계정별 상세 (등록상품=판매중만)
        account_map = {a.id: a.display_name or a.store_name
                       for a in SmartStoreAccount.objects.filter(is_active=True)}
        by_account_raw = qs.filter(status_type='SALE').values('account_id').annotate(
            cnt=Count('id'), last_synced=Max('synced_at')
        )
        by_account = []
        for row in by_account_raw:
            aid = row['account_id']
            ls = row['last_synced']
            by_account.append({
                'account_id': aid,
                'account_name': account_map.get(aid, str(aid)),
                'count': row['cnt'],
                'last_synced_at': ls.isoformat() if ls else None,
            })
        by_account.sort(key=lambda x: -x['count'])

        last_synced_all = qs.aggregate(ls=Max('synced_at'))['ls']
        return Response({
            'total': total,
            'by_status': by_status,
            'by_account': by_account,
            'last_synced_at': last_synced_all.isoformat() if last_synced_all else None,
        })


# ──── 품절처리 (W코드 기반) ────

def _get_suspend_targets(product_ids, select_all=False, filters=None):
    """선택된 상품의 seller_management_code(W*)로 전 계정에서 SALE+ownerclan_soldout=True 대상 조회"""
    filters = filters or {}
    qs = SmartStoreProduct.objects.all()

    if select_all:
        if filters.get('account_id') and filters['account_id'] != 0:
            qs = qs.filter(account_id=filters['account_id'])
        if filters.get('status'):
            qs = qs.filter(status_type=filters['status'])
        if filters.get('search'):
            q = filters['search']
            qs = qs.filter(Q(name__icontains=q) | Q(seller_management_code__icontains=q))
        if filters.get('ownerclan_soldout') is not None:
            qs = qs.filter(ownerclan_soldout=filters['ownerclan_soldout'])
        w_codes = list(qs.filter(seller_management_code__startswith='W')
                       .values_list('seller_management_code', flat=True).distinct())
    else:
        if not product_ids:
            return [], []
        w_codes = list(SmartStoreProduct.objects.filter(
            id__in=product_ids, seller_management_code__startswith='W'
        ).values_list('seller_management_code', flat=True).distinct())

    if not w_codes:
        return [], w_codes

    targets = SmartStoreProduct.objects.select_related('account').filter(
        seller_management_code__in=w_codes,
        status_type='SALE',
        ownerclan_soldout=True,
    )
    return list(targets), w_codes


class SuspendPreviewView(APIView):
    def post(self, request):
        product_ids = request.data.get('product_ids', [])
        select_all = request.data.get('select_all', False)
        filters = request.data.get('filters', {})

        targets, w_codes = _get_suspend_targets(product_ids, select_all, filters)
        by_store = {}
        for t in targets:
            name = t.account.display_name or t.account.store_name
            by_store[name] = by_store.get(name, 0) + 1

        return Response({
            'total_count': len(targets),
            'by_store': [{'store_name': k, 'count': v} for k, v in by_store.items()],
            'w_codes': w_codes,
        })


class SuspendAllNoMatchView(APIView):
    """미매칭/확인필요(역마진) 전체(SALE만) 판매중지 — 지마켓/11번가 SuspendAllNoMatchView와 동일 개념.
    선택 없이 서버가 현재 조건(kind='no_match': W코드+카탈로그에 코드자체 없음 / kind='needs_check': 마켓가
    대비 10%+ 저가)에 해당하는 SALE 상품 전체를 계산해 처리. 셀레니움이 아니라 네이버 API 직접호출이라
    백그라운드 스레드로 실행(계정별 순차, 락 불필요 — 지마켓/11번가 크롤과 독립적으로 동시 실행 가능)."""
    LOG_FILE = '/tmp/suspend_smartstore_nomatch.log'

    def post(self, request):
        import threading, time
        from django.db.models import F

        kind = request.data.get('kind') or 'no_match'
        account_id = request.data.get('account_id')
        search = request.data.get('search')
        pct_raw = request.data.get('pct')
        pct = int(pct_raw) if pct_raw not in (None, '') else 10
        mult = (100 - min(max(pct, 1), 99)) / 100.0

        if kind == 'lcode_soldout':
            from apps.cpc.eleven_my_product_service import get_lcode_soldout_rows
            targets = get_lcode_soldout_rows(
                SmartStoreProduct, 'seller_management_code', 'product_no', 'status_type', 'SALE',
                account_id=account_id, search=search, search_fields=['name', 'seller_management_code'],
                return_objects=True,
            )
            label = 'L코드 품절/미확인'
        else:
            if kind == 'needs_check':
                qs = SmartStoreProduct.objects.select_related('account').filter(
                    purchase_cost__gt=0, sale_price__lte=F('purchase_cost') * mult, status_type='SALE',
                )
                label = f'확인필요(역마진 {pct}%+)'
            else:
                qs = SmartStoreProduct.objects.select_related('account').filter(
                    seller_management_code__iregex=r'^(WDM_|AUTO_)?W', purchase_cost__isnull=True, status_type='SALE',
                ).exclude(seller_management_code__regex=r'[가-힣]')
                label = '미매칭'
            if account_id:
                qs = qs.filter(account_id=int(account_id))
            if search:
                qs = qs.filter(Q(name__icontains=search) | Q(seller_management_code__icontains=search))
            targets = list(qs)

        if not targets:
            return Response({'status': 'blocked', 'message': f'⛔ {label}(SALE) 대상이 없습니다.'}, status=400)

        store_groups = {}
        for t in targets:
            store_groups.setdefault(t.account_id, {'account': t.account, 'items': []})['items'].append(t)

        def _run():
            from .services.naver_api import _get_access_token, suspend_product_api
            with open(self.LOG_FILE, 'a') as log:
                log.write(f'\n{time.strftime("%F %T")} {label} 전체 판매중지 시작 — {len(targets)}건 / {len(store_groups)}스토어\n')
                success = fail = 0
                for sid, group in store_groups.items():
                    acc = group['account']
                    if not acc.commerce_api_key or not acc.commerce_secret_key:
                        fail += len(group['items'])
                        log.write(f'  [{acc.store_name}] API키 미등록 — {len(group["items"])}건 스킵\n')
                        continue
                    try:
                        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                    except Exception as e:
                        fail += len(group['items'])
                        log.write(f'  [{acc.store_name}] 토큰 발급 실패: {e}\n')
                        continue
                    for item in group['items']:
                        try:
                            suspend_product_api(item.channel_product_no, token)
                            SmartStoreProduct.objects.filter(pk=item.pk).update(status_type='SUSPENSION')
                            success += 1
                        except Exception as e:
                            fail += 1
                            log.write(f'  [{acc.store_name}] {item.product_no} 실패: {e}\n')
                        time.sleep(1)
                    log.flush()
                log.write(f'{time.strftime("%F %T")} 완료 — 성공 {success} / 실패 {fail}\n')

        threading.Thread(target=_run, daemon=True).start()

        by_store = {}
        for t in targets:
            name = t.account.display_name or t.account.store_name
            by_store[name] = by_store.get(name, 0) + 1
        msg = (f'🛑 {label} 전체 판매중지 시작 — {len(store_groups)}스토어 총 {len(targets)}개(SALE만 대상). '
               f'네이버 API 특성상 1건당 약 1초 소요, 진행상황은 {self.LOG_FILE} 확인.')
        return Response({'status': 'started', 'message': msg, 'accounts': len(store_groups), 'total': len(targets)})


class PriceMatchApplyView(APIView):
    """확인필요(역마진, 마켓가 대비 pct%+ 저가) 상품의 판매가를 예비상품 마켓가(purchase_cost)로 실제 변경.
    SuspendAllNoMatchView와 동일한 백그라운드 스레드·계정순차·1건당1초 패턴(2026-08-22, 사용자 요청)."""
    LOG_FILE = '/tmp/price_match_smartstore.log'

    def post(self, request):
        import threading, time
        from django.db.models import F

        account_id = request.data.get('account_id')
        search = request.data.get('search')
        pct_raw = request.data.get('pct')
        pct = int(pct_raw) if pct_raw not in (None, '') else 20
        mult = (100 - min(max(pct, 1), 99)) / 100.0

        qs = SmartStoreProduct.objects.select_related('account').filter(
            purchase_cost__gt=0, sale_price__lte=F('purchase_cost') * mult, status_type='SALE',
        )
        if account_id:
            qs = qs.filter(account_id=int(account_id))
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(seller_management_code__icontains=search))
        targets = list(qs)

        if not targets:
            return Response({'status': 'blocked', 'message': f'⛔ 확인필요(역마진 {pct}%+, SALE) 대상이 없습니다.'}, status=400)

        store_groups = {}
        for t in targets:
            store_groups.setdefault(t.account_id, {'account': t.account, 'items': []})['items'].append(t)

        def _run():
            from .services.naver_api import _get_access_token, update_price_api
            with open(self.LOG_FILE, 'a') as log:
                log.write(f'\n{time.strftime("%F %T")} 단가 마켓가 맞춤 시작(역마진 {pct}%+) — {len(targets)}건 / {len(store_groups)}스토어\n')
                success = fail = 0
                for sid, group in store_groups.items():
                    acc = group['account']
                    if not acc.commerce_api_key or not acc.commerce_secret_key:
                        fail += len(group['items'])
                        log.write(f'  [{acc.store_name}] API키 미등록 — {len(group["items"])}건 스킵\n')
                        continue
                    try:
                        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                    except Exception as e:
                        fail += len(group['items'])
                        log.write(f'  [{acc.store_name}] 토큰 발급 실패: {e}\n')
                        continue
                    for item in group['items']:
                        try:
                            update_price_api(item.channel_product_no, item.purchase_cost, token)
                            SmartStoreProduct.objects.filter(pk=item.pk).update(sale_price=item.purchase_cost)
                            success += 1
                        except Exception as e:
                            fail += 1
                            log.write(f'  [{acc.store_name}] {item.product_no} 실패: {e}\n')
                        time.sleep(1)
                    log.flush()
                log.write(f'{time.strftime("%F %T")} 완료 — 성공 {success} / 실패 {fail}\n')

        threading.Thread(target=_run, daemon=True).start()

        by_store = {}
        for t in targets:
            name = t.account.display_name or t.account.store_name
            by_store[name] = by_store.get(name, 0) + 1
        msg = (f'💰 단가 마켓가 맞춤 시작(역마진 {pct}%+) — {len(store_groups)}스토어 총 {len(targets)}개(SALE만 대상). '
               f'네이버 API 특성상 1건당 약 1초 소요, 진행상황은 {self.LOG_FILE} 확인.')
        return Response({'status': 'started', 'message': msg, 'accounts': len(store_groups), 'total': len(targets)})


class SuspendProductsView(APIView):
    def post(self, request):
        product_ids = request.data.get('product_ids', [])
        select_all = request.data.get('select_all', False)
        filters = request.data.get('filters', {})

        targets, _ = _get_suspend_targets(product_ids, select_all, filters)
        if not targets:
            return Response({'success_count': 0, 'fail_count': 0, 'errors': []})

        from .services.naver_api import _get_access_token, suspend_product_api
        import time

        # 계정별 그룹핑
        store_groups = {}
        for t in targets:
            sid = t.account_id
            if sid not in store_groups:
                store_groups[sid] = {
                    'account': t.account,
                    'items': [],
                }
            store_groups[sid]['items'].append(t)

        success_count = 0
        errors = []

        for sid, group in store_groups.items():
            acc = group['account']
            if not acc.commerce_api_key or not acc.commerce_secret_key:
                for item in group['items']:
                    errors.append({'product_no': item.product_no, 'error': 'API 키 미등록'})
                continue

            try:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
            except Exception as e:
                for item in group['items']:
                    errors.append({'product_no': item.product_no, 'error': f'토큰 발급 실패: {e}'})
                continue

            for item in group['items']:
                try:
                    suspend_product_api(item.product_no, token)
                    SmartStoreProduct.objects.filter(pk=item.pk).update(status_type='SUSPENSION')
                    success_count += 1
                except Exception as e:
                    errors.append({'product_no': item.product_no, 'error': str(e)})
                time.sleep(1)

        return Response({
            'success_count': success_count,
            'fail_count': len(errors),
            'errors': errors,
        })


# ──── 엑셀 다운로드 ────

class ProductExcelView(APIView):
    def get(self, request):
        try:
            import openpyxl
        except ImportError:
            return Response({'error': 'openpyxl 설치 필요'}, status=500)

        from django.db.models import F

        account_ids = request.query_params.getlist('account_ids')
        statuses = request.query_params.getlist('statuses')
        w_only = request.query_params.get('w_only') == '1'
        no_match = request.query_params.get('no_match') in ('1', 'true', 'True')
        needs_check = request.query_params.get('needs_check') in ('1', 'true', 'True')
        needs_check_pct_raw = request.query_params.get('needs_check_pct')
        needs_check_pct = int(needs_check_pct_raw) if needs_check_pct_raw not in (None, '') else 10
        needs_check_mult = (100 - min(max(needs_check_pct, 1), 99)) / 100.0

        qs = SmartStoreProduct.objects.select_related('account').order_by('account__store_name', '-id')
        if account_ids:
            qs = qs.filter(account_id__in=account_ids)
        if statuses:
            qs = qs.filter(status_type__in=statuses)
        if no_match:
            qs = (qs.filter(seller_management_code__iregex=r'^(WDM_|AUTO_)?W', purchase_cost__isnull=True, status_type='SALE')
                    .exclude(seller_management_code__regex=r'[가-힣]'))
        elif needs_check:
            qs = qs.filter(purchase_cost__gt=0, sale_price__lte=F('purchase_cost') * needs_check_mult, status_type='SALE')
        elif w_only:
            qs = qs.filter(seller_management_code__iregex=r'^(WDM_|AUTO_)?W')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '상품목록'
        headers = ['스토어', '상품번호', '채널상품번호', '상품명', '판매가', '재고', '상태',
                   '판매자관리코드', '카테고리ID', '오너클랜품절', '동기화일시']
        ws.append(headers)

        for p in qs:
            ws.append([
                p.account.display_name or p.account.store_name,
                p.product_no,
                p.channel_product_no,
                p.name,
                p.sale_price,
                p.stock_quantity,
                p.status_type,
                p.seller_management_code,
                p.category_id,
                '예' if p.ownerclan_soldout else '아니오',
                p.synced_at.strftime('%Y-%m-%d %H:%M') if p.synced_at else '',
            ])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        from urllib.parse import quote
        filename = quote('스마트스토어_상품목록.xlsx')
        resp = HttpResponse(
            buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}"
        return resp


# ──── 네이버 상품별 ROAS ────

class NaverProductRoasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        ym_from = request.query_params.get('ym_from') or f'{today.year}-{today.month:02d}'
        ym_to = request.query_params.get('ym_to') or ym_from
        account_id = request.query_params.get('account_id') or ''
        ad_type_filter = request.query_params.get('ad_type') or ''

        y0, m0 = map(int, ym_from.split('-'))
        y1, m1 = map(int, ym_to.split('-'))
        d0 = date(y0, m0, 1)
        d1 = date(y1, m1, calendar.monthrange(y1, m1)[1])

        qs = NaverAdProductReport.objects.filter(since_date__gte=d0, since_date__lte=d1)
        if account_id:
            qs = qs.filter(account_id=account_id)
        if ad_type_filter in ('cpc', 'ai'):
            qs = qs.filter(ad_type=ad_type_filter)

        agg = list(qs.values('account_id', 'product_no', 'product_name').annotate(
            total_cost=Sum('cost'),
            total_click=Sum('click'),
            total_impression=Sum('impression'),
            total_conv_cnt=Sum('conversion_count'),
            total_conv_amt=Sum('conversion_amount'),
        ))

        pnos = {r['product_no'] for r in agg}
        status_raw = {p.product_no: p.status_type
                      for p in SmartStoreProduct.objects.filter(product_no__in=pnos)}
        acc_map = {a.id: (a.display_name or a.store_name)
                   for a in SmartStoreAccount.objects.all()}

        cost_min = int(request.query_params.get('cost_min') or 0)
        roas_max_s = request.query_params.get('roas_max')
        roas_min_s = request.query_params.get('roas_min')
        clicks_min = int(request.query_params.get('clicks_min') or 0)

        rows = []
        for r in agg:
            cost = r['total_cost'] or 0
            conv_amt = r['total_conv_amt'] or 0
            roas = round(conv_amt * 100.0 / cost, 1) if cost else 0
            if cost_min and cost < cost_min:
                continue
            if roas_max_s is not None and roas > float(roas_max_s):
                continue
            if roas_min_s is not None and roas < float(roas_min_s):
                continue
            if clicks_min and (r['total_click'] or 0) < clicks_min:
                continue
            st_raw = status_raw.get(r['product_no'], '')
            rows.append({
                'account_id': r['account_id'],
                'account_name': acc_map.get(r['account_id'], ''),
                'product_no': r['product_no'],
                'product_name': r['product_name'],
                'cost': cost,
                'click': r['total_click'] or 0,
                'impression': r['total_impression'] or 0,
                'conv_cnt': r['total_conv_cnt'] or 0,
                'conv_amt': conv_amt,
                'roas': roas,
                'status': _NAVER_STATUS_LABEL.get(st_raw, st_raw or '-'),
            })

        if request.query_params.get('export'):
            fname = f'naver_product_roas_{ym_from}_{ym_to}.csv'
            resp = HttpResponse(content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="{fname}"'
            resp.write('﻿')
            w = csv.writer(resp)
            w.writerow(['계정', '상품번호', '상품명', '노출수', '클릭수', '광고비', '구매수', '구매금액', 'ROAS(%)', '비고(상품상태)'])
            for r in sorted(rows, key=lambda x: -x['cost']):
                w.writerow([r['account_name'], r['product_no'], r['product_name'],
                            r['impression'], r['click'], r['cost'],
                            r['conv_cnt'], r['conv_amt'], r['roas'], r['status']])
            return resp

        total_cost = sum(r['cost'] for r in rows)
        total_conv = sum(r['conv_amt'] for r in rows)
        totals = {
            'cost': total_cost,
            'click': sum(r['click'] for r in rows),
            'impression': sum(r['impression'] for r in rows),
            'conv_cnt': sum(r['conv_cnt'] for r in rows),
            'conv_amt': total_conv,
            'roas': round(total_conv * 100.0 / total_cost, 1) if total_cost else 0,
            'products': len(rows),
        }
        return Response({'rows': rows, 'totals': totals})


class NaverSearchTermView(APIView):
    """네이버 검색어(expKeyword) 리포트 — 계정 단위 월 집계 조회.
    상품별 매칭은 네이버 API 제약(expKeyword가 소재/상품 차원과 상호배타)상 불가 — 계정 단위만 제공."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ym = request.query_params.get('ym') or ''
        account_id = request.query_params.get('account_id') or ''
        sort = request.query_params.get('sort', 'conv_amt')

        qs = NaverSearchTermReport.objects.select_related('account')
        if ym:
            qs = qs.filter(ym=ym)
        if account_id:
            qs = qs.filter(account_id=account_id)

        order_field = {'conv_amt': '-conv_amt', 'cost': '-cost', 'click': '-click'}.get(sort, '-conv_amt')
        qs = qs.order_by(order_field)[:500]

        rows = [{
            'account_id': r.account_id,
            'account_name': r.account.display_name or r.account.store_name,
            'keyword': r.keyword,
            'impression': r.impression,
            'click': r.click,
            'cost': r.cost,
            'conv_cnt': r.conv_cnt,
            'conv_amt': r.conv_amt,
            'roas': round(r.conv_amt * 100.0 / r.cost, 1) if r.cost else 0,
        } for r in qs]

        avail_yms = list(NaverSearchTermReport.objects.values_list('ym', flat=True).distinct().order_by('-ym'))
        return Response({'rows': rows, 'available_yms': avail_yms})


class NaverSearchTermCrawlView(APIView):
    """네이버 검색어 리포트 '수집' 버튼 — 백그라운드로 실행."""
    def get(self, request):
        from apps.cpc import eleven_block_guard as guard
        lock_path = guard._lock_path('naver_search_term')
        busy = False
        if lock_path.exists():
            try:
                pid = int(lock_path.read_text(encoding='utf-8').split('|')[0])
                busy = guard._pid_alive(pid)
            except Exception:
                busy = False
        return Response({'busy': busy})

    def post(self, request):
        import subprocess
        from datetime import date
        from apps.cpc import eleven_block_guard as guard

        ym = request.data.get('ym') or f'{date.today().year}-{date.today().month:02d}'
        lock_path = guard._lock_path('naver_search_term')
        if lock_path.exists():
            try:
                pid = int(lock_path.read_text(encoding='utf-8').split('|')[0])
                if guard._pid_alive(pid):
                    return Response({'status': 'busy', 'error': '이미 실행 중입니다.'}, status=409)
            except Exception:
                pass

        cmd = (f'cd /home/rejoice888/Avengers/backend && '
               f'python3 -c "from apps.cpc import eleven_block_guard as guard; '
               f'guard.acquire_global_lock(\'네이버검색어수집\', platform=\'naver_search_term\')" && '
               f'python3 manage.py crawl_naver_search_term --ym {ym} '
               f'>> /tmp/naver_search_term_crawl.log 2>&1; '
               f'python3 -c "from apps.cpc import eleven_block_guard as guard; '
               f'guard.release_global_lock(platform=\'naver_search_term\')"')
        try:
            subprocess.Popen(['bash', '-c', cmd], start_new_session=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=500)
        return Response({'status': 'started', 'ym': ym})


# ──── 크롤 상태 ────

class CrawlStatusView(APIView):
    def get(self, request):
        logs = SmartStoreCrawlLog.objects.select_related('account').order_by('-started_at')[:30]
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'account': log.account.display_name if log.account else '-',
                'status': log.status,
                'message': log.message,
                'started_at': log.started_at.isoformat(),
                'ended_at': log.ended_at.isoformat() if log.ended_at else None,
            })
        return Response(data)


# ──── 클린위반 ────

_CLEAN_ADVICE = {
    '판매행위 위반 > 중복상품': {
        'problem': '오너클랜 동일 상품(nv_mid 동일)을 복수 스토어에 중복 등록. 상품명만 달리해도 nv_mid가 같으면 중복 위반 처리됨.',
        'solution': '스토어별 상품 분리: 한 스토어에만 등록하거나, 대표상품 삭제 후 한 스토어 유지. 오너클랜 신규 등록 시 스토어간 중복 사전 체크 필수.',
    },
    '상품정보 기재 위반 > KC인증 위반': {
        'problem': '어린이·생활용품 KC인증 번호 미기재 또는 면제대상 미표기. 인증 없이 판매 시 적발.',
        'solution': '해당 상품 상세페이지에 KC인증 번호 기재 또는 KC 면제 대상 표기. 어린이용 완구·생활용품은 KC 확인 후 등록.',
    },
}

_CLEAN_DEFAULT_ADVICE = {
    'problem': '네이버 쇼핑 클린 기준 위반으로 판매 활동 제한 위험.',
    'solution': '네이버 쇼핑 클린 정책 확인 후 위반 상품 수정·삭제 처리.',
}


class CleanViolationListView(APIView):
    """계정별 클린위반 요약 목록"""
    def get(self, request):
        by_acc = (SmartStoreCleanViolation.objects
                  .values('account_id', 'violation_type')
                  .annotate(cnt=Count('id')))

        acc_map = {a.id: (a.display_name or a.store_name)
                   for a in SmartStoreAccount.objects.filter(is_active=True)}

        result = {}
        for row in by_acc:
            aid = row['account_id']
            if aid not in result:
                result[aid] = {'account_id': aid, 'account_name': acc_map.get(aid, str(aid)),
                               'total': 0, 'types': {}}
            result[aid]['types'][row['violation_type']] = row['cnt']
            result[aid]['total'] += row['cnt']

        return Response(list(result.values()))


class CleanViolationDetailView(APIView):
    """계정 클린위반 상세 목록"""
    def get(self, request, account_id):
        qs = (SmartStoreCleanViolation.objects
              .filter(account_id=account_id)
              .order_by('-violation_date', 'violation_type'))

        rows = []
        for v in qs:
            rows.append({
                'id': v.id,
                'violation_date': str(v.violation_date),
                'violation_type': v.violation_type,
                'product_name': v.product_name,
                'product_id': v.product_id,
                'nv_mid': v.nv_mid,
                'note': v.note,
            })

        # 위반 유형별 통계 + 대책
        type_summary = {}
        for r in rows:
            vt = r['violation_type']
            if vt not in type_summary:
                advice = _CLEAN_ADVICE.get(vt, _CLEAN_DEFAULT_ADVICE)
                type_summary[vt] = {'count': 0, **advice}
            type_summary[vt]['count'] += 1

        return Response({
            'account_id': account_id,
            'total': len(rows),
            'violations': rows,
            'type_summary': [
                {'violation_type': k, **v}
                for k, v in type_summary.items()
            ],
        })


# ──── 예상 클린위반 (실제 위반이력 패턴 기반 상품명 휴리스틱 스캔) ────
# 실제 위반이력 102건 분석 결과 반영 (2026-07-02): 중복상품 85%, 나머지는 원산지/KC인증/생활화학 등

_PRED_CATEGORIES = {
    'duplicate': {
        'label': '중복상품(계정내)',
        'confidence': 'high',
        'problem': '동일 상품명이 같은 계정 내에서 상품번호만 다르게 중복 등록됨. 실제 위반이력의 85%(87/102건)가 이 유형.',
        'solution': '중복 등록분 중 판매실적 낮은 쪽을 삭제하고 하나로 통합.',
    },
    'danger': {
        'label': '위험물품/판매제한 의심',
        'confidence': 'high',
        'problem': '삼단봉·쌍절곤·정글도·서바이벌칼 등 호신·전투용품은 온라인 판매제한 대상일 수 있음. 실제 위반이력에도 서바이벌칼 판매금지 사례 있음.',
        'solution': '해당 상품이 실제 위험물품 규제 대상인지 확인 후 판매중지/카테고리 재분류.',
    },
    'origin': {
        'label': '원산지 표기 과장 의심',
        'confidence': 'medium',
        'problem': '농산물/축산물 상품명에 "산지직송", "프리미엄", "고당도" 등 과장 수식어 포함. 원산지 실제값은 DB에 없어 상품명만으로 추정.',
        'solution': '상품명에서 과장 수식어 제거 + 원산지 표기가 실제와 일치하는지 확인.',
    },
    'kc': {
        'label': 'KC인증 대상 추정',
        'confidence': 'low',
        'problem': '유아/아동/완구 키워드 포함 상품 — 어린이제품은 KC 인증번호 기재 필요. 카테고리 데이터가 없어 키워드 매칭만으로는 오탐이 많음.',
        'solution': 'KC 인증 완료/면제 여부를 실제 확인 후 상세페이지에 인증번호 기재.',
    },
    'chem': {
        'label': '생활화학제품 미인증 추정',
        'confidence': 'low',
        'problem': '세제/경화제/접착제 등 생활화학제품 키워드 포함 — 안전확인대상생활화학제품은 신고번호 필요. 키워드 매칭만으로는 오탐이 많음.',
        'solution': '안전확인신고 여부 확인 후 상세페이지에 신고번호 기재.',
    },
}

_TACTICAL_KW = ['서바이벌', '생존칼', '호신용', '전술나이프', '전술칼', '폴딩나이프', '접이식칼', '사냥칼', '전투용', '총모양',
                '삼단봉', '쌍절곤', '진압봉', '호신봉', '너클', '정글도', '정글낫', '정글칼']
_KITCHEN_KW = ['주방', '식도', '요리', '부엌', '정육', '식칼', '디너', '레스토랑', '업소', '셰프', '쉐프', '스테이크',
               '생선', '과일칼', '채칼', '회칼', '빵칼', '피자칼']
_DANGER_FALSE_KW = ['경첩', '악력', '클램프']
_KC_KW = ['유아', '아동', '어린이', '레고', '블록', '완구', '장난감', '키즈']
_CHEM_KW = ['세제', '방향제', '살균', '경화제', '접착제', '탈취제', '제거제', '스프레이', '섬유유연제', '곰팡이제거', '왁스', '코팅제']
_ORIGIN_KW = ['산지직송', '국내산', '프리미엄', '달콤한', '새콤달콤', '고당도', '로얄', '특가', '당일수확', '제철']
_FRUIT_KW = ['사과', '감귤', '배', '포도', '딸기', '감자', '고구마', '쌀', '한우', '흑돼지', '귤', '토마토']


def _or_q(field, keywords):
    q = Q()
    for k in keywords:
        q |= Q(**{f'{field}__icontains': k})
    return q


def _pred_queryset(category):
    base = SmartStoreProduct.objects.filter(status_type='SALE')

    if category == 'duplicate':
        dup_names = (base.values('account_id', 'name')
                     .annotate(c=Count('id')).filter(c__gt=1)
                     .values_list('account_id', 'name'))
        q = Q()
        for account_id, name in dup_names:
            q |= (Q(account_id=account_id) & Q(name=name))
        return base.filter(q) if dup_names else base.none()

    if category == 'danger':
        return (base.filter(_or_q('name', _TACTICAL_KW))
                .exclude(_or_q('name', _KITCHEN_KW))
                .exclude(_or_q('name', _DANGER_FALSE_KW)))

    if category == 'origin':
        return base.filter(_or_q('name', _ORIGIN_KW)).filter(_or_q('name', _FRUIT_KW))

    if category == 'kc':
        return base.filter(_or_q('name', _KC_KW))

    if category == 'chem':
        return base.filter(_or_q('name', _CHEM_KW))

    return base.none()


class PredictedViolationListView(APIView):
    """실제 위반이력 패턴 기반 예상 클린위반 — 카테고리별 건수 요약 (전계정)"""
    def get(self, request):
        result = []
        for key, meta in _PRED_CATEGORIES.items():
            total = _pred_queryset(key).count()
            by_acc = list(_pred_queryset(key).values('account_id').annotate(c=Count('id')))
            result.append({
                'key': key, **meta, 'total': total,
                'by_account': {r['account_id']: r['c'] for r in by_acc},
            })
        return Response(result)


class PredictedViolationDetailView(APIView):
    """예상 클린위반 카테고리별 상세 상품 목록"""
    def get(self, request, category):
        if category not in _PRED_CATEGORIES:
            return Response({'detail': 'unknown category'}, status=404)

        qs = _pred_queryset(category).select_related('account').order_by('account_id', 'name')
        items = [{
            'account_id': p.account_id,
            'account_name': p.account.display_name or p.account.store_name,
            'name': p.name,
            'sale_price': p.sale_price,
            'product_no': p.product_no,
            'channel_product_no': p.channel_product_no,
            'category_id': p.category_id,
        } for p in qs]

        return Response({
            'category': category,
            **_PRED_CATEGORIES[category],
            'total': len(items),
            'items': items,
        })

import datetime
import io

from django.db.models import Sum, Count, Q, Max
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import SmartStoreAccount, SmartStoreSales, SmartStoreAdCost, SmartStoreProduct, SmartStoreCrawlLog
from apps.sales.models import SalesRecord


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
            start = today.replace(day=1)
        else:
            start = datetime.date.fromisoformat(start)
            end = datetime.date.fromisoformat(end)

        # SalesRecord를 주 매출 소스로 사용 (11번가/지마켓 대시보드와 동일)
        accounts_qs = SmartStoreAccount.objects.filter(is_active=True)
        login_to_acc = {a.login_id: a for a in accounts_qs}
        acc_info = {a.id: (a.display_name or a.store_name, a.login_id) for a in accounts_qs}

        sr_qs = SalesRecord.objects.filter(
            platform='smartstore',
            order_date__gte=start,
            order_date__lte=end,
        )

        by_account = {}
        for r in sr_qs.values('seller__seller_id').annotate(
            sales=Sum('total_price'),
            commission=Sum('commission'),
            cogs=Sum('cost'),
            orders=Count('id'),
        ):
            sid = r['seller__seller_id']
            acc = login_to_acc.get(sid)
            if not acc:
                continue
            if account_ids and str(acc.id) not in account_ids:
                continue
            settle = (r['sales'] or 0) - (r['commission'] or 0)
            by_account[acc.id] = {
                'sales': r['sales'] or 0,
                'settlement': settle,
                'orders': r['orders'] or 0,
                'commission': r['commission'] or 0,
                'cogs': r['cogs'] or 0,
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

        account_list = []
        for aid, row in by_account.items():
            name, login_id = acc_info.get(aid, (str(aid), ''))
            sales = row['sales']
            ad = row['ad_cost']
            account_list.append({
                'account_id': aid,
                'account_name': name,
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
        account_id = request.query_params.get('account_id', '0')
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 50))
        status = request.query_params.get('status', '')
        search = request.query_params.get('search', '')
        ownerclan_soldout = request.query_params.get('ownerclan_soldout')

        qs = SmartStoreProduct.objects.select_related('account')
        if account_id and account_id != '0':
            qs = qs.filter(account_id=account_id)
        if status:
            qs = qs.filter(status_type=status)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(seller_management_code__icontains=search))
        if ownerclan_soldout is not None:
            qs = qs.filter(ownerclan_soldout=ownerclan_soldout == '1')

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
            })

        return Response({
            'items': data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total else 0,
        })


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

        # 전체 또는 단일 계정
        if account_id and account_id != '0':
            qs = SmartStoreProduct.objects.filter(account_id=account_id)
            stats = qs.values('status_type').annotate(cnt=Count('id'))
            total = qs.count()
            last_synced = qs.aggregate(ls=Max('synced_at'))['ls']
            by_status = {r['status_type']: r['cnt'] for r in stats}
            return Response({
                'total': total,
                'by_status': by_status,
                'last_synced_at': last_synced.isoformat() if last_synced else None,
            })

        # 전체 계정 합산
        qs = SmartStoreProduct.objects.all()
        stats = qs.values('status_type').annotate(cnt=Count('id'))
        total = qs.count()
        by_status = {r['status_type']: r['cnt'] for r in stats}

        # 계정별 상세
        account_map = {a.id: a.display_name or a.store_name
                       for a in SmartStoreAccount.objects.filter(is_active=True)}
        by_account_raw = SmartStoreProduct.objects.values('account_id').annotate(
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

        account_ids = request.query_params.getlist('account_ids')
        statuses = request.query_params.getlist('statuses')
        w_only = request.query_params.get('w_only') == '1'

        qs = SmartStoreProduct.objects.select_related('account').order_by('account__store_name', '-id')
        if account_ids:
            qs = qs.filter(account_id__in=account_ids)
        if statuses:
            qs = qs.filter(status_type__in=statuses)
        if w_only:
            qs = qs.filter(seller_management_code__startswith='W')

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

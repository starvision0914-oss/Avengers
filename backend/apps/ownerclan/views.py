import io
import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse

from . import services
from .models import OwnerclanTask


class _WorkspaceMixin:
    """요청의 ?workspace= 값으로 대상 테이블(예비상품/상품가공)을 전환. 기본 reserve."""
    def initial(self, request, *args, **kwargs):
        services.set_workspace(request.query_params.get('workspace') or 'reserve')
        super().initial(request, *args, **kwargs)


def _zip_to_single_xlsx(zip_path, zip_filename):
    """zip 안의 .xlsx 파일(들)을 꺼내 엑셀 1개로 합친다.
    1개면 그대로, 2개 이상이면 시트를 나눠 하나의 워크북으로 병합.
    반환: (BytesIO, 파일명) — 엑셀이 없으면 (None, None)."""
    import re
    import zipfile
    import openpyxl

    with zipfile.ZipFile(zip_path) as zf:
        xlsx_members = [n for n in zf.namelist() if n.lower().endswith('.xlsx')]
        if not xlsx_members:
            return None, None
        xlsx_members.sort(reverse=True)  # 최신연도(2026) 먼저

        base_name = os.path.splitext(zip_filename)[0]  # best_prod_2026-08-30

        if len(xlsx_members) == 1:
            data = zf.read(xlsx_members[0])
            return io.BytesIO(data), f'{base_name}.xlsx'

        merged = openpyxl.Workbook()
        merged.remove(merged.active)
        for member in xlsx_members:
            data = zf.read(member)
            src = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
            m = re.search(r'\((\d{4})\)', member)
            sheet_title = m.group(1) if m else os.path.splitext(os.path.basename(member))[0]
            sheet_title = sheet_title[:31]  # 엑셀 시트명 31자 제한
            for src_ws in src.worksheets:
                dst_ws = merged.create_sheet(title=sheet_title if len(src.worksheets) == 1 else f'{sheet_title}_{src_ws.title}'[:31])
                for row in src_ws.iter_rows(values_only=True):
                    dst_ws.append(row)

        buf = io.BytesIO()
        merged.save(buf)
        buf.seek(0)
        return buf, f'{base_name}.xlsx'


def _zip_extract_year_xlsx(zip_path, zip_filename, year):
    """zip 안에서 파일명의 (YYYY) 표기로 특정 연도 하나만 골라 그대로 꺼낸다(병합 안 함).
    2026-09-11 사용자 요청 — 연도별로 따로 받고 싶을 때. 해당 연도 파일이 없으면 (None, None)."""
    import re
    import zipfile

    with zipfile.ZipFile(zip_path) as zf:
        xlsx_members = [n for n in zf.namelist() if n.lower().endswith('.xlsx')]
        for member in xlsx_members:
            m = re.search(r'\((\d{4})\)', member)
            if m and m.group(1) == str(year):
                base_name = os.path.splitext(zip_filename)[0]
                data = zf.read(member)
                return io.BytesIO(data), f'{base_name}_{year}.xlsx'
    return None, None


def _zip_years(zip_path):
    """zip 안 엑셀 파일명의 (YYYY) 표기를 전부 모아 정렬 리스트로(최신 먼저). 2026-09-11 신설
    — 프론트가 연도별 다운로드 버튼을 몇 개 보여줄지 판단하는 용도."""
    import re
    import zipfile
    try:
        with zipfile.ZipFile(zip_path) as zf:
            years = {m.group(1) for n in zf.namelist()
                     if (m := re.search(r'\((\d{4})\)', n))}
    except Exception:
        return []
    return sorted(years, reverse=True)


def _parse_weekly_period(zip_path):
    """zip 안의 엑셀 파일명(best_prod_MMDD_MMDD(YYYY).xlsx)에서 실제 집계기간을 뽑는다.
    2개(올해/작년) 있으면 최신연도 쪽 기준. 이름이 패턴과 안 맞으면 None(호출쪽에서 저장일로 폴백)."""
    import re
    import zipfile
    from datetime import date

    try:
        with zipfile.ZipFile(zip_path) as zf:
            xlsx_members = sorted(
                (n for n in zf.namelist() if n.lower().endswith('.xlsx')), reverse=True)
    except Exception:
        return None, None
    for member in xlsx_members:
        m = re.search(r'(\d{2})(\d{2})_(\d{2})(\d{2})\((\d{4})\)', os.path.basename(member))
        if not m:
            continue
        sm, sd, em, ed, year = (int(g) for g in m.groups())
        try:
            start = date(year, sm, sd)
            end = date(year, em, ed)
        except ValueError:
            continue
        return start.isoformat(), end.isoformat()
    return None, None


def _pid_alive(pid):
    """pid 생존 확인. 종료됐지만 부모(Django)가 wait()하지 않아 좀비(Z)로 남은 경우는
    os.kill(pid, 0)이 예외 없이 성공해버리므로 반드시 죽은 것으로 취급해야 함."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    try:
        with open(f'/proc/{pid}/stat') as f:
            state = f.read().rsplit(')', 1)[1].split()[0]
        if state == 'Z':
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
            return False
    except (FileNotFoundError, IndexError, OSError):
        pass
    return True


class OwnerClanProductUploadView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        f = request.FILES.get('file')
        if not f:
            return Response({'error': 'file required'}, status=400)

        running = OwnerclanTask.objects.filter(
            task_type='ownerclan_upload', status__in=('pending', 'running')
        ).first()
        if running:
            # 워커 프로세스가 죽었는데 DB에는 running으로 남는 좀비 케이스 자동 해제
            # (2026-08-21 task 43 — pid 사망 확인했지만 status는 running으로 남아 새 업로드를 영구 차단했던 사고 재발방지)
            if not _pid_alive(running.pid):
                running.status = 'error'
                rd = running.result_data or {}
                rd['error'] = f'stuck(running) → 좀비 자동감지·해제 (pid {running.pid} 사망)'
                running.result_data = rd
                running.save(update_fields=['status', 'result_data'])
            else:
                return Response({
                    'error': '이미 업로드 처리 중입니다.',
                    'task_id': running.id,
                }, status=409)

        try:
            result = services.upload_excel_async(f, workspace=request.query_params.get('workspace') or 'reserve')
            return Response(result, status=202)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    def get(self, request):
        task_id = request.query_params.get('task_id')
        if not task_id:
            # task_id 없이 조회 시 — 현재 실행 중인 업로드가 있으면 알려줌(페이지 진입 즉시 진행률 표시용)
            running = OwnerclanTask.objects.filter(
                task_type='ownerclan_upload', status__in=('pending', 'running')
            ).order_by('-id').first()
            if running and not _pid_alive(running.pid):
                running.status = 'error'
                rd = running.result_data or {}
                rd['error'] = f'stuck(running) → 좀비 자동감지·해제 (pid {running.pid} 사망)'
                running.result_data = rd
                running.save(update_fields=['status', 'result_data'])
                running = None
            if not running:
                return Response({'task_id': None})
            return Response({
                'task_id': running.id,
                'status': running.status,
                'result_data': running.result_data,
            })
        try:
            task = OwnerclanTask.objects.get(pk=int(task_id))
        except OwnerclanTask.DoesNotExist:
            return Response({'error': 'not found'}, status=404)
        return Response({
            'task_id': task.id,
            'status': task.status,
            'result_data': task.result_data,
        })


class OwnerClanProductCsvUploadView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        f = request.FILES.get('file')
        if not f:
            return Response({'error': 'file required'}, status=400)
        try:
            result = services.upload_csv_status(f)
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class OwnerClanSoldoutTxtUploadView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        f = request.FILES.get('file')
        if not f:
            return Response({'error': 'file required'}, status=400)
        try:
            result = services.upload_soldout_txt(f)
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class OwnerClanProductListView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 50))
        sale_status = request.query_params.get('sale_status')
        is_synced = request.query_params.get('is_synced')
        search = request.query_params.get('search') or None
        changed_field = request.query_params.get('changed_field') or None
        sort = request.query_params.get('sort') or None
        order = request.query_params.get('order') or 'asc'
        filter_col = request.query_params.get('filter_col') or None
        filter_vals_raw = request.query_params.get('filter_vals') or ''
        filter_vals = [v for v in filter_vals_raw.split('|') if v != ''] if filter_vals_raw else None
        codes_raw = request.query_params.get('codes') or ''
        codes = [c.strip() for c in codes_raw.split(',') if c.strip()] if codes_raw else None
        result = services.get_products(
            page, per_page,
            sale_status=int(sale_status) if sale_status else None,
            is_synced=int(is_synced) if is_synced is not None and is_synced != '' else None,
            search=search,
            changed_field=changed_field,
            sort=sort,
            order=order,
            filter_col=filter_col,
            filter_vals=filter_vals,
            codes=codes,
        )
        return Response(result)


class OwnerClanProductDetailView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        result = services.get_product_detail(pk)
        if not result:
            return Response({'error': '상품을 찾을 수 없습니다.'}, status=404)
        return Response(result)


class OwnerClanProductSyncView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_ids = request.data.get('product_ids')
        if product_ids and isinstance(product_ids, list):
            product_ids = [int(i) for i in product_ids]
        else:
            product_ids = None
        result = services.sync_products(product_ids)
        return Response(result)


class OwnerClanProductStatsView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.get_stats())


class OwnerClanProductChangedFieldsView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.get_changed_field_counts())


class OwnerClanProductExcelExportView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        sale_status = request.query_params.get('sale_status')
        is_synced = request.query_params.get('is_synced')
        search = request.query_params.get('search') or None
        changed_field = request.query_params.get('changed_field') or None

        rows = services.get_products_for_export(
            sale_status=int(sale_status) if sale_status else None,
            is_synced=int(is_synced) if is_synced is not None and is_synced != '' else None,
            search=search,
            changed_field=changed_field,
        )

        STATUS_LABELS = {1: '판매중', 2: '품절', 3: '단종'}

        wb = Workbook()
        ws = wb.active
        ws.title = '오너클랜 상품대장'

        headers = ['W코드', '상태', '동기화', '상품명', '원본상품명',
                    '마켓상품명', '원본마켓상품명', '오너클랜가', '원본오너클랜가',
                    '마켓가', '원본마켓가', '배송비', '원본배송비',
                    '반품비', '원본반품비', '카테고리', '제조사', '원산지']
        col_widths = [12, 8, 8, 35, 35, 35, 35, 12, 12, 12, 12, 8, 8, 8, 8, 20, 15, 10]

        header_font = Font(bold=True, size=10)
        header_fill = PatternFill('solid', fgColor='F0F0F0')
        changed_fill = PatternFill('solid', fgColor='FFF3E0')
        thin_border = Border(bottom=Side(style='thin', color='DDDDDD'))
        money_fmt = '#,##0'

        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        for col, w in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = w

        for i, r in enumerate(rows, 2):
            is_changed = r.get('is_synced') == 0
            fill = changed_fill if is_changed else None

            def _cell(col, val, fmt=None):
                c = ws.cell(row=i, column=col, value=val)
                c.border = thin_border
                if fmt:
                    c.number_format = fmt
                if fill:
                    c.fill = fill
                return c

            _cell(1, r.get('product_code'))
            _cell(2, STATUS_LABELS.get(r.get('sale_status'), '?'))
            _cell(3, '변경됨' if is_changed else '일치')
            _cell(4, r.get('product_name'))
            _cell(5, r.get('orig_product_name'))
            _cell(6, r.get('market_product_name'))
            _cell(7, r.get('orig_market_product_name'))
            _cell(8, r.get('ownerclan_price', 0), money_fmt)
            _cell(9, r.get('orig_ownerclan_price', 0), money_fmt)
            _cell(10, r.get('market_price', 0), money_fmt)
            _cell(11, r.get('orig_market_price', 0), money_fmt)
            _cell(12, r.get('shipping_fee', 0), money_fmt)
            _cell(13, r.get('orig_shipping_fee', 0), money_fmt)
            _cell(14, r.get('return_fee', 0), money_fmt)
            _cell(15, r.get('orig_return_fee', 0), money_fmt)
            _cell(16, r.get('category_name'))
            _cell(17, r.get('manufacturer'))
            _cell(18, r.get('origin'))

        ws.auto_filter.ref = ws.dimensions

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="ownerclan_products.xlsx"'
        return response


class OwnerClanProductDbExportView(_WorkspaceMixin, APIView):
    """오너클랜 상품 DB 전체 다운로드(CSV) — 필터 없이 전 건수.
    orig_*(원본대조용 내부컬럼)와 거대 HTML/공지 텍스트 필드는 파일이 열기 힘들 정도로 커져서 제외."""
    permission_classes = [IsAuthenticated]

    FIELDS = [
        'product_code', 'sale_status', 'is_synced',
        'seller_code1', 'seller_code2', 'category_code', 'category_name', 'market_category',
        'product_name', 'market_product_name',
        'ownerclan_price', 'consumer_price', 'market_price', 'shipping_fee', 'shipping_type',
        'min_qty', 'max_qty', 'return_fee', 'return_possible',
        'option1_name', 'option1_values', 'option2_name', 'option2_values',
        'combined_option', 'combined_option_detail', 'independent_option',
        'product_attribute', 'product_grade', 'tax_type', 'compliance', 'age_restriction',
        'manufacturer', 'brand', 'model_name', 'origin', 'keywords',
        'image_large', 'notice_code', 'notice_category',
        'market_gmarket', 'market_auction', 'market_11st', 'market_coupang',
        'market_smartstore', 'market_promo', 'market_gift',
        'certification_type', 'certification_info',
        'registered_at', 'modified_at', 'uploaded_at', 'synced_at',
    ]
    HEADERS = [
        'W코드', '판매상태', '동기화',
        '판매자코드1', '판매자코드2', '카테고리코드', '카테고리명', '마켓카테고리',
        '상품명', '마켓상품명',
        '오너클랜가', '소비자가', '마켓가', '배송비', '배송타입',
        '최소수량', '최대수량', '반품비', '반품가능',
        '옵션1명', '옵션1값', '옵션2명', '옵션2값',
        '조합옵션', '조합옵션상세', '독립옵션',
        '속성', '등급', '과세유형', '준수사항', '연령제한',
        '제조사', '브랜드', '모델명', '원산지', '키워드',
        '대표이미지', '고시코드', '고시분류',
        '지마켓', '옥션', '11번가', '쿠팡', '스마트스토어', '프로모션', '사은품',
        '인증유형', '인증정보',
        '등록일', '수정일', '업로드일', '동기화일',
    ]

    def get(self, request):
        import csv
        from django.http import StreamingHttpResponse
        from .models import OwnerclanProduct, ProcessingProduct

        is_processing = services._t() == 'processing_product'
        model = ProcessingProduct if is_processing else OwnerclanProduct

        def _stream():
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(self.HEADERS)
            yield ('﻿' + buf.getvalue()).encode('utf-8')
            qs = model.objects.order_by('id').values_list(*self.FIELDS).iterator(chunk_size=2000)
            for row in qs:
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(['' if v is None else v for v in row])
                yield buf.getvalue().encode('utf-8')

        fname = f'ownerclan_db_{"processing" if is_processing else "reserve"}.csv'
        response = StreamingHttpResponse(_stream(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response


class OwnerclanApiCrawlView(APIView):
    """오너클랜 정식 API 신규상품 수집 — 백그라운드 실행 + 상태 폴링. /blog(오너클랜크롤러 메뉴) 페이지에서 사용."""
    permission_classes = [IsAuthenticated]
    LOG_FILE = '/tmp/ownerclan_api_crawl.log'

    def get(self, request):
        import os
        from .models import OwnerclanApiAccount
        task = OwnerclanTask.objects.filter(task_type='api_crawl').order_by('-created_at').first()
        busy = False
        if task and task.status == 'running' and task.pid:
            if _pid_alive(task.pid):
                busy = True
            else:
                task.status = 'done'
                task.save(update_fields=['status'])

        log_tail = ''
        try:
            with open(self.LOG_FILE, encoding='utf-8', errors='ignore') as f:
                log_tail = ''.join(f.readlines()[-40:])
        except FileNotFoundError:
            pass

        accounts = [{'login_id': a.login_id, 'last_synced_at': a.last_synced_at,
                     'last_new_count': a.last_new_count,
                     'balance': a.balance, 'order_stats': a.order_stats,
                     'subscription_info': a.subscription_info,
                     'lowest_price_quota': a.lowest_price_quota,
                     'info_synced_at': a.info_synced_at}
                    for a in OwnerclanApiAccount.objects.filter(is_active=True)]
        return Response({'busy': busy, 'log': log_tail, 'accounts': accounts})

    def post(self, request):
        import subprocess
        running = OwnerclanTask.objects.filter(task_type='api_crawl', status='running').first()
        if running and running.pid and _pid_alive(running.pid):
            return Response({'error': '이미 수집 중입니다.'}, status=409)

        task = OwnerclanTask.objects.create(task_type='api_crawl', status='running')
        cmd = (f'cd /home/rejoice888/Avengers/backend && '
               f'python3 manage.py crawl_ownerclan_api > {self.LOG_FILE} 2>&1')
        proc = subprocess.Popen(['bash', '-c', cmd], start_new_session=True)
        task.pid = proc.pid
        task.save(update_fields=['pid'])
        return Response({'status': 'started', 'task_id': task.id})


class OwnerclanWeeklyPopularView(APIView):
    """오너클랜 '주간 인기 상품' 다운로드(db저장창고) — 파일 목록 조회/수동 실행.
    매일 09:00 크론(cron_ownerclan_weekly_popular.sh)으로도 자동 저장됨."""
    permission_classes = [IsAuthenticated]
    LOG_FILE = '/tmp/cron_ownerclan_weekly.log'

    def get(self, request):
        import os
        from django.conf import settings
        storage_dir = os.path.join(settings.BASE_DIR, 'media', 'ownerclan_weekly_popular')
        files = []
        if os.path.isdir(storage_dir):
            for name in os.listdir(storage_dir):
                path = os.path.join(storage_dir, name)
                if os.path.isfile(path):
                    stat = os.stat(path)
                    is_zip = name.lower().endswith('.zip')
                    period_start, period_end = (_parse_weekly_period(path) if is_zip else (None, None))
                    files.append({
                        'filename': name,
                        'size': stat.st_size,
                        'saved_at': stat.st_mtime,
                        # 실제 집계기간 — zip 내 엑셀명에서 파싱, 실패 시 None(프론트가 저장일로 표시)
                        'period_start': period_start,
                        'period_end': period_end,
                        'years': _zip_years(path) if is_zip else [],
                    })
        files.sort(key=lambda f: f['saved_at'], reverse=True)

        task = OwnerclanTask.objects.filter(task_type='weekly_popular').order_by('-created_at').first()
        busy = False
        if task and task.status == 'running' and task.pid:
            if _pid_alive(task.pid):
                busy = True
            else:
                task.status = 'done'
                task.save(update_fields=['status'])

        return Response({'files': files, 'storage_dir': storage_dir, 'busy': busy})

    def post(self, request):
        import os
        import subprocess
        running = OwnerclanTask.objects.filter(task_type='weekly_popular', status='running').first()
        if running and running.pid and _pid_alive(running.pid):
            return Response({'error': '이미 수집 중입니다.'}, status=409)

        task = OwnerclanTask.objects.create(task_type='weekly_popular', status='running')
        cmd = (f'cd /home/rejoice888/Avengers/backend && '
               f'python3 manage.py crawl_ownerclan_weekly_popular > {self.LOG_FILE} 2>&1; '
               f'echo DONE >> {self.LOG_FILE}')
        proc = subprocess.Popen(['bash', '-c', cmd], start_new_session=True)
        task.pid = proc.pid
        task.status = 'running'
        task.save(update_fields=['pid', 'status'])
        return Response({'status': 'started', 'task_id': task.id})


class OwnerclanWeeklyPopularDownloadView(APIView):
    """날짜별 원본(.zip) 다운로드. ?as=xlsx 를 붙이면 zip 안의 엑셀만 꺼내서(2개면 시트 2장으로 합쳐서)
    바로 내려줌. ?year=2025 또는 2026 을 추가로 붙이면 그 연도(zip 내부 파일명 (YYYY) 표기 기준)
    파일 하나만 병합 없이 내려줌(2026-09-11 사용자 요청 — 연도별로 따로 받기)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import os
        from django.conf import settings
        from django.http import FileResponse, Http404

        filename = request.query_params.get('filename', '')
        # 경로 조작 방지 — 순수 파일명만 허용
        if not filename or os.path.basename(filename) != filename:
            raise Http404()
        storage_dir = os.path.join(settings.BASE_DIR, 'media', 'ownerclan_weekly_popular')
        path = os.path.join(storage_dir, filename)
        if not os.path.isfile(path):
            raise Http404()

        year = request.query_params.get('year')
        if year and filename.lower().endswith('.zip'):
            xlsx_buf, xlsx_name = _zip_extract_year_xlsx(path, filename, year)
            if xlsx_buf is not None:
                return FileResponse(xlsx_buf, as_attachment=True, filename=xlsx_name)
            raise Http404()

        if request.query_params.get('as') == 'xlsx' and filename.lower().endswith('.zip'):
            xlsx_buf, xlsx_name = _zip_to_single_xlsx(path, filename)
            if xlsx_buf is not None:
                return FileResponse(xlsx_buf, as_attachment=True, filename=xlsx_name)
            # zip 안에 엑셀이 없으면 원본 그대로 폴백

        return FileResponse(open(path, 'rb'), as_attachment=True, filename=filename)


class OwnerclanWeeklyPopularDownloadAllView(APIView):
    """주간 인기 상품(db저장창고)에 저장된 날짜별 파일 전체를, 지정한 연도(?year=) 기준으로
    모아 중복(전략상품코드) 제거 후 엑셀 1개로 한번에 다운로드(2026-09-11 사용자 요청 —
    "알집으로 다운되지 않고 중복제거해서 엑셀로 한번에 받을수있도록"). year 필수.
    filenames 쿼리파라미터(콤마구분)로 특정 날짜만 지정도 가능 — 생략 시 전체 날짜."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import os
        import re
        import zipfile
        import io
        import openpyxl
        from datetime import date
        from django.conf import settings
        from django.http import FileResponse, Http404

        year = request.query_params.get('year', '').strip()
        if not year:
            return Response({'error': 'year 파라미터가 필요합니다(예: 2026)'}, status=400)

        storage_dir = os.path.join(settings.BASE_DIR, 'media', 'ownerclan_weekly_popular')
        if not os.path.isdir(storage_dir):
            raise Http404()

        requested = request.query_params.get('filenames', '')
        if requested:
            # 경로 조작 방지 — 순수 파일명만 허용, 중복 제거(순서 유지)
            seen = set()
            names = []
            for n in requested.split(','):
                n = n.strip()
                if n and os.path.basename(n) == n and n not in seen:
                    seen.add(n)
                    names.append(n)
        else:
            names = sorted(n for n in os.listdir(storage_dir)
                            if os.path.isfile(os.path.join(storage_dir, n)))

        names = [n for n in names if os.path.isfile(os.path.join(storage_dir, n))
                 and n.lower().endswith('.zip')]
        if not names:
            raise Http404()

        codes = []
        seen_codes = set()
        used_files = 0
        for n in names:
            path = os.path.join(storage_dir, n)
            try:
                with zipfile.ZipFile(path) as zf:
                    member = next((m for m in zf.namelist()
                                   if m.lower().endswith('.xlsx')
                                   and (mm := re.search(r'\((\d{4})\)', m)) and mm.group(1) == year), None)
                    if not member:
                        continue
                    used_files += 1
                    wb = openpyxl.load_workbook(io.BytesIO(zf.read(member)), data_only=True)
                    ws = wb.worksheets[0]
                    for row in ws.iter_rows(min_row=2, values_only=True):
                        code = row[0] if row else None
                        if code and code not in seen_codes:
                            seen_codes.add(code)
                            codes.append(code)
            except Exception:
                continue

        if not codes:
            raise Http404()

        wb_out = openpyxl.Workbook()
        ws_out = wb_out.active
        ws_out.title = f'{year}인기상품'
        ws_out.append(['전략상품코드'])
        for c in codes:
            ws_out.append([c])

        buf = io.BytesIO()
        wb_out.save(buf)
        buf.seek(0)

        bundle_name = f'오너클랜_주간인기상품_{year}년_{len(codes)}개_{date.today():%Y%m%d}.xlsx'
        return FileResponse(buf, as_attachment=True, filename=bundle_name)


class OwnerclanAccountInfoCrawlView(APIView):
    """오너클랜 마이페이지 계정정보(예치금/주문현황/구독서비스/최저가선점권) 새로고침 — 백그라운드 실행."""
    permission_classes = [IsAuthenticated]
    LOG_FILE = '/tmp/ownerclan_account_info_crawl.log'

    def post(self, request):
        import subprocess
        running = OwnerclanTask.objects.filter(task_type='account_info', status='running').first()
        if running and running.pid and _pid_alive(running.pid):
            return Response({'error': '이미 수집 중입니다.'}, status=409)

        task = OwnerclanTask.objects.create(task_type='account_info', status='running')
        cmd = (f'cd /home/rejoice888/Avengers/backend && '
               f'python3 manage.py crawl_ownerclan_account_info > {self.LOG_FILE} 2>&1')
        proc = subprocess.Popen(['bash', '-c', cmd], start_new_session=True)
        task.pid = proc.pid
        task.save(update_fields=['pid'])
        return Response({'status': 'started', 'task_id': task.id})


class OwnerclanOrderFileCollectView(APIView):
    """오너클랜 주문/배송조회(orderList.php) 엑셀다운로드/플레이오토 송장 정보 — 전 계정 순차 수집(백그라운드).
    file_type('excel'/'invoice')을 골라서 시작. /owner 대시보드 버튼에서 사용."""
    permission_classes = [IsAuthenticated]
    LOG_FILE = '/tmp/ownerclan_order_collect.log'

    def get(self, request):
        task = OwnerclanTask.objects.filter(task_type='order_collect').order_by('-created_at').first()
        busy = False
        if task and task.status == 'running' and task.pid:
            if _pid_alive(task.pid):
                busy = True
            else:
                task.status = 'done'
                task.save(update_fields=['status'])

        log_tail = ''
        try:
            with open(self.LOG_FILE, encoding='utf-8', errors='ignore') as f:
                log_tail = ''.join(f.readlines()[-60:])
        except FileNotFoundError:
            pass

        return Response({'busy': busy, 'log': log_tail,
                          'file_type': (task.input_data or {}).get('file_type') if task else None})

    def post(self, request):
        import subprocess
        running = OwnerclanTask.objects.filter(task_type='order_collect', status='running').first()
        if running and running.pid and _pid_alive(running.pid):
            return Response({'error': '이미 수집 중입니다.'}, status=409)

        file_type = request.data.get('file_type', 'invoice')
        if file_type not in ('invoice', 'excel'):
            return Response({'error': "file_type은 'invoice' 또는 'excel'이어야 합니다."}, status=400)

        task = OwnerclanTask.objects.create(task_type='order_collect', status='running',
                                             input_data={'file_type': file_type})
        cmd = (f'cd /home/rejoice888/Avengers/backend && '
               f'python3 manage.py crawl_ownerclan_orders --type {file_type} > {self.LOG_FILE} 2>&1; '
               f'echo DONE >> {self.LOG_FILE}')
        proc = subprocess.Popen(['bash', '-c', cmd], start_new_session=True)
        task.pid = proc.pid
        task.save(update_fields=['pid'])
        return Response({'status': 'started', 'task_id': task.id})


class OwnerclanOrderFileListView(APIView):
    """저장된 주문/배송조회 파일 목록. ?file_type= 필터, ?date=YYYY-MM-DD&hour=0~23 로 특정 회차(하루
    5회 자동수집 09/11/15/16/18시 중 하나)만 조회 가능. batches에 현재 file_type 기준으로 존재하는
    회차(날짜+시간) 목록도 같이 내려줘 프론트 선택박스를 채운다."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone as dj_tz
        from .models import OwnerclanOrderFile

        file_type = request.query_params.get('file_type')
        date_param = request.query_params.get('date')
        hour_param = request.query_params.get('hour')

        base_qs = OwnerclanOrderFile.objects.all()
        if file_type:
            base_qs = base_qs.filter(file_type=file_type)
        all_records = list(base_qs.order_by('-downloaded_at'))

        batches = sorted({
            (dj_tz.localtime(r.downloaded_at).strftime('%Y-%m-%d'), dj_tz.localtime(r.downloaded_at).hour)
            for r in all_records
        }, reverse=True)

        records = all_records
        if date_param:
            records = [r for r in records if dj_tz.localtime(r.downloaded_at).strftime('%Y-%m-%d') == date_param]
        if hour_param not in (None, ''):
            h = int(hour_param)
            records = [r for r in records if dj_tz.localtime(r.downloaded_at).hour == h]

        files = [{'id': f.id, 'login_id': f.login_id, 'file_type': f.file_type,
                  'filename': f.filename, 'file_size': f.file_size,
                  'downloaded_at': f.downloaded_at} for f in records]
        return Response({'files': files, 'batches': [{'date': d, 'hour': h} for d, h in batches]})


class OwnerclanOrderFileDownloadView(APIView):
    """개별 주문파일 다운로드."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404
        from .models import OwnerclanOrderFile
        try:
            rec = OwnerclanOrderFile.objects.get(pk=pk)
        except OwnerclanOrderFile.DoesNotExist:
            raise Http404()
        if not os.path.isfile(rec.file_path):
            raise Http404()
        return FileResponse(open(rec.file_path, 'rb'), as_attachment=True, filename=rec.filename)


class OwnerclanOrderFileDeleteView(APIView):
    """개별 주문파일 삭제(디스크+DB 레코드 둘 다)."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        from .models import OwnerclanOrderFile
        try:
            rec = OwnerclanOrderFile.objects.get(pk=pk)
        except OwnerclanOrderFile.DoesNotExist:
            return Response(status=204)
        try:
            if os.path.isfile(rec.file_path):
                os.remove(rec.file_path)
        except OSError:
            pass
        rec.delete()
        return Response(status=204)


class OwnerclanOrderFileDownloadAllView(APIView):
    """저장된 주문파일들을 계정별로 합쳐 엑셀 1개로 다운로드(2026-09-11: 계정별로 따로 zip 압축되던 것을
    "모든계정 하나의 엑셀 파일로" 요청받아 병합 방식으로 변경).
    - invoice(플레이오토 송장 정보): 원본에 이미 '오너클랜 아이디' 컬럼이 있어 그대로 이어붙임
      (플레이오토 재업로드 포맷을 그대로 유지하기 위해 컬럼을 추가하지 않음).
    - excel(엑셀다운로드): 계정 식별 컬럼이 없어 맨 앞에 '계정' 컬럼을 넣어 이어붙임.
    file_type만 지정 시 계정별 최신 1건(중복 방지), date+hour 지정 시 그 회차(하루 5회 자동수집
    09/11/15/16/18시 중 하나) 파일만, ids 지정 시 그 파일들 그대로 사용."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import io
        from datetime import date as _date
        import pandas as pd
        from django.http import FileResponse, Http404
        from django.utils import timezone as dj_tz
        from .models import OwnerclanOrderFile

        file_type = request.query_params.get('file_type')
        ids_param = request.query_params.get('ids')
        date_param = request.query_params.get('date')
        hour_param = request.query_params.get('hour')

        qs = OwnerclanOrderFile.objects.all().order_by('-downloaded_at')
        if file_type:
            qs = qs.filter(file_type=file_type)

        if ids_param:
            ids = [int(i) for i in ids_param.split(',') if i.strip().isdigit()]
            recs = list(qs.filter(id__in=ids))
        else:
            recs = list(qs)
            if date_param:
                recs = [r for r in recs if dj_tz.localtime(r.downloaded_at).strftime('%Y-%m-%d') == date_param]
            if hour_param not in (None, ''):
                h = int(hour_param)
                recs = [r for r in recs if dj_tz.localtime(r.downloaded_at).hour == h]
            # 계정별 최신 1건만(이미 -downloaded_at 정렬이라 먼저 만난 게 최신) — 중복/재시도 방지
            seen = set()
            dedup = []
            for r in recs:
                if r.login_id in seen:
                    continue
                seen.add(r.login_id)
                dedup.append(r)
            recs = dedup

        recs = [r for r in recs if os.path.isfile(r.file_path)]
        if not recs:
            raise Http404()
        recs.sort(key=lambda r: r.login_id)

        dfs = []
        for r in recs:
            try:
                if r.file_path.lower().endswith('.xls'):
                    # 오너클랜 orderList.php가 내려주는 구형 .xls는 xlrd가 정상 파일도 스트림
                    # 순서 휴리스틱으로 "손상"이라 오판하는 경우가 있어(2026-09-11 실측,
                    # dlwodb111) ignore_workbook_corruption으로 우회.
                    df = pd.read_excel(r.file_path, header=0, dtype=str, engine='xlrd',
                                        engine_kwargs={'ignore_workbook_corruption': True})
                else:
                    df = pd.read_excel(r.file_path, header=0, dtype=str)
            except Exception as e:
                df = pd.DataFrame([[f'읽기 실패: {e}']], columns=['오류'])
            if r.file_type != 'invoice':
                df.insert(0, '계정', r.login_id)
            dfs.append(df)
        combined = pd.concat(dfs, ignore_index=True, sort=False) if dfs else pd.DataFrame()

        # 중복주문의심 체크(2026-09-11, 사용자 요청) — 엑셀다운로드(전체 합친 파일)에서만.
        # 같은 상품(상품명)을 같은 받는사람 앞으로 두 번 이상 주문한 행 = 실수로 두 번 주문했을
        # 위험이 있어 표시. 상품코드가 아니라 상품명으로 묶는 이유: 판매처(01.지마켓/03.11번가 등)가
        # 달라도 같은 상품일 수 있어(주문관리 메모 참고) 상품명 기준이 더 넓게 잡아준다.
        dup_col = '중복주문확인'
        if file_type == 'excel' and not combined.empty and '상품명' in combined.columns and '받는사람' in combined.columns:
            key_name = combined['상품명'].fillna('').str.strip()
            key_recv = combined['받는사람'].fillna('').str.strip()
            group_key = key_name + '||' + key_recv
            dup_count = group_key.map(group_key.value_counts())
            is_dup = (dup_count > 1) & (key_name != '') & (key_recv != '')
            combined[dup_col] = is_dup.map({True: '중복주문의심상품', False: ''})
            # 의심상품을 맨 위로, 그 안에서는 상품명·받는사람으로 묶어서 나란히 보이게 정렬
            combined['_dup_sort'] = (~is_dup).astype(int)   # False(의심)=0이 먼저
            combined = combined.sort_values(
                ['_dup_sort', '상품명', '받는사람'], kind='stable').drop(columns=['_dup_sort'])
            combined = combined.reset_index(drop=True)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            combined.to_excel(writer, sheet_name='전체', index=False)
            if file_type == 'excel' and dup_col in combined.columns:
                from openpyxl.styles import PatternFill
                red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
                ws = writer.sheets['전체']
                n_cols = len(combined.columns)
                for row_i, flagged in enumerate(combined[dup_col] == '중복주문의심상품', start=2):
                    if flagged:
                        for c in range(1, n_cols + 1):
                            ws.cell(row=row_i, column=c).fill = red_fill
        buf.seek(0)

        label = {'invoice': '송장정보', 'excel': '엑셀다운로드'}.get(file_type, '전체')
        batch_label = f'_{date_param}_{hour_param}시' if (date_param or hour_param not in (None, '')) else ''
        filename = f'오너클랜_주문{label}{batch_label}_{len(recs)}계정_{_date.today():%Y%m%d}.xlsx'
        return FileResponse(buf, as_attachment=True, filename=filename)


class OwnerClanProductWCodesView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sale_status = request.query_params.get('sale_status')
        is_synced = request.query_params.get('is_synced')
        search = request.query_params.get('search') or None
        changed_field = request.query_params.get('changed_field') or None

        codes = services.get_w_codes(
            sale_status=int(sale_status) if sale_status else None,
            is_synced=int(is_synced) if is_synced is not None and is_synced != '' else None,
            search=search,
            changed_field=changed_field,
        )
        return Response({'codes': codes, 'count': len(codes)})


class OwnerClanProductDeleteAllView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        confirm = request.data.get('confirm')
        if confirm != 'DELETE_ALL':
            return Response({'error': "확인 토큰 누락 (confirm='DELETE_ALL' 필요)"}, status=400)
        result = services.delete_all_products()
        return Response(result)


class OwnerClanProductDeleteByIdsView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return Response({'error': '삭제할 id 리스트 필요'}, status=400)
        result = services.delete_products_by_ids(ids)
        return Response(result)


class OwnerClanProductDedupeView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = services.dedupe_by_product_name()
        return Response(result)


class OwnerClanApplyElevenNameView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        items = request.data.get('items') or []
        if not isinstance(items, list) or not items:
            return Response({'error': 'items 배열 필요 ([{code,name}])'}, status=400)
        return Response(services.apply_eleven_names(items))


class OwnerClanDistinctValuesView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        column = request.query_params.get('column')
        if not column:
            return Response({'error': 'column 파라미터 필요'}, status=400)
        try:
            values = services.get_distinct_values(column)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        return Response({'column': column, 'values': values})


class MyProductCopyView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        codes = request.data.get('source_product_codes') or []
        if not isinstance(codes, list) or not codes:
            return Response({'error': 'source_product_codes 배열 필요'}, status=400)
        result = services.copy_to_my_product(codes)
        return Response(result)


class MyProductListView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 50))
        search = request.query_params.get('search') or None
        is_modified = request.query_params.get('is_modified')
        sort = request.query_params.get('sort') or None
        order = request.query_params.get('order') or 'asc'
        filter_col = request.query_params.get('filter_col') or None
        filter_vals_raw = request.query_params.get('filter_vals') or ''
        filter_vals = [v for v in filter_vals_raw.split('|') if v != ''] if filter_vals_raw else None
        codes_raw = request.query_params.get('codes') or ''
        codes = [c.strip() for c in codes_raw.split(',') if c.strip()] if codes_raw else None
        result = services.get_my_products(
            page, per_page, search=search,
            is_modified=int(is_modified) if is_modified is not None and is_modified != '' else None,
            sort=sort, order=order,
            filter_col=filter_col, filter_vals=filter_vals, codes=codes,
        )
        return Response(result)


class MyProductDetailView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        result = services.get_my_product_detail(pk)
        if not result:
            return Response({'error': '나의 상품을 찾을 수 없습니다.'}, status=404)
        return Response(result)

    def patch(self, request, pk):
        fields_dict = request.data or {}
        result = services.update_my_product(pk, fields_dict)
        return Response(result)

    def delete(self, request, pk):
        result = services.delete_my_products_by_ids([pk])
        return Response(result)


class MyProductDeleteAllView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        confirm = request.data.get('confirm')
        if confirm != 'DELETE_ALL':
            return Response({'error': "확인 토큰 누락 (confirm='DELETE_ALL' 필요)"}, status=400)
        result = services.delete_all_my_products()
        return Response(result)


class MyProductDeleteByIdsView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return Response({'error': '삭제할 id 리스트 필요'}, status=400)
        result = services.delete_my_products_by_ids(ids)
        return Response(result)


class MyProductDedupeView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = services.dedupe_my_by_product_name()
        return Response(result)


class MyProductDistinctValuesView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        column = request.query_params.get('column')
        if not column:
            return Response({'error': 'column 파라미터 필요'}, status=400)
        try:
            values = services.get_my_distinct_values(column)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        return Response({'column': column, 'values': values})


class MyProductWCodesView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get('search') or None
        is_modified = request.query_params.get('is_modified')
        filter_col = request.query_params.get('filter_col') or None
        filter_vals_raw = request.query_params.get('filter_vals') or ''
        filter_vals = [v for v in filter_vals_raw.split('|') if v != ''] if filter_vals_raw else None
        codes = services.get_my_w_codes(
            search=search,
            is_modified=int(is_modified) if is_modified is not None and is_modified != '' else None,
            filter_col=filter_col, filter_vals=filter_vals,
        )
        return Response({'codes': codes, 'count': len(codes)})


class MyProductExcelExportView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        search = request.query_params.get('search') or None
        is_modified = request.query_params.get('is_modified')
        filter_col = request.query_params.get('filter_col') or None
        filter_vals_raw = request.query_params.get('filter_vals') or ''
        filter_vals = [v for v in filter_vals_raw.split('|') if v != ''] if filter_vals_raw else None

        rows = services.get_my_products_for_export(
            search=search,
            is_modified=int(is_modified) if is_modified is not None and is_modified != '' else None,
            filter_col=filter_col, filter_vals=filter_vals,
        )

        wb = Workbook()
        ws = wb.active
        ws.title = '나의 상품'

        headers = ['나의W코드', '원본W코드', '수정', '상품명', '마켓상품명',
                    '오너클랜가', '마켓가', '배송비', '반품비', '카테고리', '제조사', '원산지', '복사일']
        col_widths = [16, 14, 8, 35, 35, 12, 12, 8, 8, 20, 15, 10, 18]

        header_font = Font(bold=True, size=10)
        header_fill = PatternFill('solid', fgColor='F0F0F0')
        modified_fill = PatternFill('solid', fgColor='E8F5E9')
        thin_border = Border(bottom=Side(style='thin', color='DDDDDD'))
        money_fmt = '#,##0'

        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
        for col, w in enumerate(col_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = w

        for i, r in enumerate(rows, 2):
            mod = bool(r.get('is_modified'))
            fill = modified_fill if mod else None

            def _cell(col, val, fmt=None):
                c = ws.cell(row=i, column=col, value=val)
                c.border = thin_border
                if fmt:
                    c.number_format = fmt
                if fill:
                    c.fill = fill
                return c

            _cell(1, r.get('my_product_code'))
            _cell(2, r.get('source_product_code'))
            _cell(3, '수정됨' if mod else '원본')
            _cell(4, r.get('product_name'))
            _cell(5, r.get('market_product_name'))
            _cell(6, r.get('ownerclan_price', 0), money_fmt)
            _cell(7, r.get('market_price', 0), money_fmt)
            _cell(8, r.get('shipping_fee', 0), money_fmt)
            _cell(9, r.get('return_fee', 0), money_fmt)
            _cell(10, r.get('category_name'))
            _cell(11, r.get('manufacturer'))
            _cell(12, r.get('origin'))
            cd = r.get('copied_at')
            _cell(13, cd.strftime('%Y-%m-%d %H:%M') if cd else '')

        ws.auto_filter.ref = ws.dimensions

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="my_products.xlsx"'
        return response


class MyProductUploadView(_WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        f = request.FILES.get('file')
        if not f:
            return Response({'error': 'file required'}, status=400)
        running = OwnerclanTask.objects.filter(
            task_type='my_product_upload', status__in=('pending', 'running')
        ).first()
        if running:
            return Response({'error': '이미 업로드 처리 중입니다.', 'task_id': running.id}, status=409)
        try:
            result = services.upload_my_excel_async(f)
            return Response(result, status=202)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    def get(self, request):
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id required'}, status=400)
        try:
            task = OwnerclanTask.objects.get(pk=int(task_id))
        except OwnerclanTask.DoesNotExist:
            return Response({'error': 'not found'}, status=404)
        return Response({
            'task_id': task.id,
            'status': task.status,
            'result_data': task.result_data,
        })

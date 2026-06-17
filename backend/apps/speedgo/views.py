from rest_framework import views, status as drf_status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from . import services
from .models import SpeedgoItem, SpeedgoLog


class StatsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.get_stats())


class ItemListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 50))
        status_q = request.query_params.get('status') or None
        search = request.query_params.get('search') or None
        only_unmatched = request.query_params.get('only_unmatched') in ('1', 'true', 'True')
        return Response(services.list_items(
            page=page, per_page=per_page,
            status=status_q, search=search, only_unmatched=only_unmatched,
        ))


class MatchCategoriesView(views.APIView):
    """일괄 카테고리 매칭 — body: {item_ids?: [int], only_unmatched?: bool}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_ids = request.data.get('item_ids')
        only_unmatched = request.data.get('only_unmatched', True)
        log_lines = []
        result = services.match_categories_batch(
            item_ids=item_ids,
            only_unmatched=only_unmatched,
            log_fn=log_lines.append,
        )
        result['log'] = log_lines
        return Response(result)


class CollectMyboxView(views.APIView):
    """도매매 마이박스 동기화 — body: {login_id, password}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        login_id = request.data.get('login_id') or ''
        password = request.data.get('password') or ''
        if not login_id or not password:
            return Response({'error': '도매매 login_id, password 필요'},
                            status=drf_status.HTTP_400_BAD_REQUEST)
        log_lines = []
        result = services.collect_from_domemea(login_id, password, log_fn=log_lines.append)
        result['log'] = log_lines
        return Response(result)


class ItemDeleteView(views.APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        n, _ = SpeedgoItem.objects.filter(id=pk).delete()
        return Response({'deleted': n})


class AddManualItemView(views.APIView):
    """수동으로 상품 추가 (도매매 로그인 전 테스트용).
    body: {original_name, domemea_no?, wholesale_price?, main_image_url?}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get('original_name', '').strip()
        if not name:
            return Response({'error': 'original_name 필수'}, status=400)
        domemea_no = request.data.get('domemea_no') or f'MANUAL-{name[:20]}'
        obj, created = SpeedgoItem.objects.update_or_create(
            domemea_no=domemea_no,
            defaults={
                'original_name': name,
                'wholesale_price': int(request.data.get('wholesale_price') or 0),
                'main_image_url': request.data.get('main_image_url') or '',
                'supplier': request.data.get('supplier') or '수동',
            },
        )
        return Response({
            'id': obj.id,
            'created': created,
            'item': services._serialize(obj),
        })


class SpeedgoRunView(views.APIView):
    """스피드고 7단계 자동화 실행 (수동/자동)
    POST body: {steps?: [str]} — 미지정 시 전체 7단계"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import threading
        steps = request.data.get('steps')

        def _run():
            from .crawler import run_all_steps, send_telegram_report
            result = run_all_steps(steps=steps, log_fn=lambda m: SpeedgoLog.objects.create(
                stage='speedgo_auto', level='info', message=m))
            if result.get('results'):
                try:
                    send_telegram_report(result['results'])
                except Exception:
                    pass

        threading.Thread(target=_run, daemon=True).start()
        return Response({'status': 'started', 'steps': steps or '전체 7단계'})


class SpeedgoRunStatusView(views.APIView):
    """스피드고 세션 상태 + 최근 실행 로그"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .crawler import get_session_status
        logs = SpeedgoLog.objects.filter(stage='speedgo_auto').order_by('-created_at')[:30]
        return Response({
            **get_session_status(),
            'logs': [{'message': l.message, 'level': l.level, 'created_at': l.created_at.isoformat()} for l in logs]
        })


class SpeedgoSessionCloseView(views.APIView):
    """스피드고 세션 종료"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .crawler import close_session
        return Response(close_session())

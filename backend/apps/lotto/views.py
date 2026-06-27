import csv
import io
from datetime import datetime
from urllib.parse import quote

from django.http import HttpResponse
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from .models import LottoHistory
from . import services


class StatsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.db_stats())


class HistoryView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 50))
        order = request.query_params.get('order', 'desc')
        qs = LottoHistory.objects.all()
        qs = qs.order_by('-drw_no' if order == 'desc' else 'drw_no')[:limit]
        items = [{
            'drwNo': h.drw_no, 'drwNoDate': h.drw_date,
            'numbers': h.numbers(), 'bonus': h.bonus,
        } for h in qs]
        return Response({'items': items, **services.db_stats()})


class SyncView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        max_to_fetch = request.data.get('max_to_fetch')
        try:
            max_to_fetch = int(max_to_fetch) if max_to_fetch else None
        except (TypeError, ValueError):
            max_to_fetch = None
        result = services.sync(max_to_fetch=max_to_fetch)
        return Response(result)


class ImportCsvView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        f = request.FILES.get('file')
        if not f:
            return Response({'error': '파일이 필요합니다 (multipart key=file).'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            data = f.read()
            result = services.import_csv_bytes(data)
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class PredictView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            count = int(request.query_params.get('count', 5))
        except (TypeError, ValueError):
            count = 5
        return Response(services.predict(count=max(1, min(count, 20))))


class PredictMirrorPrevView(views.APIView):
    """전회차 패턴 학습 예측."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            count = int(request.query_params.get('count', 5))
        except (TypeError, ValueError):
            count = 5
        return Response(services.predict_mirror_prev_round(count=max(1, min(count, 20))))


class PredictFollowNextView(views.APIView):
    """전회차 각 포지션 번호 이후 회차 빈출 기반 예측."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            count = int(request.query_params.get('count', 10))
        except (TypeError, ValueError):
            count = 10
        return Response(services.predict_follow_next(count=max(1, min(count, 10))))


class PredictBruteView(views.APIView):
    """전수조사 예측 — target_score 이상 조합 검색."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            target = int(request.query_params.get('target', 100))
        except (TypeError, ValueError):
            target = 100
        try:
            count = int(request.query_params.get('count', 5))
        except (TypeError, ValueError):
            count = 5
        target = max(0, min(target, 100))
        count = max(1, min(count, 20))
        return Response(services.predict_brute(target_score=target, count=count))


class PredictionListView(views.APIView):
    """저장된 AI 예측 폴더 목록 + 신규 저장."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'items': services.list_predictions()})

    def post(self, request):
        combos = request.data.get('combinations') or []
        score = int(request.data.get('score_threshold') or 0)
        note = request.data.get('note', '')
        r = services.save_prediction(combos, score_threshold=score, note=note)
        if 'error' in r:
            return Response(r, status=400)
        return Response(r)


class PredictionCheckView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        r = services.check_prediction(pk)
        if 'error' in r:
            return Response(r, status=404)
        return Response(r)


class PredictionDeleteView(views.APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        return Response(services.delete_prediction(pk))


class ExportCsvView(views.APIView):
    """전체 회차 CSV 다운로드."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = LottoHistory.objects.order_by('drw_no')
        buf = io.StringIO()
        # BOM 추가 — 엑셀에서 한글 깨짐 방지
        buf.write('﻿')
        w = csv.writer(buf)
        w.writerow(['drwNo', 'drwNoDate', 'num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'bnusNo'])
        for h in qs:
            w.writerow([h.drw_no, h.drw_date, h.num1, h.num2, h.num3,
                        h.num4, h.num5, h.num6, h.bonus])

        resp = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'lotto_history_{qs.count()}회_{ts}.csv'
        # RFC 5987 — filename* 은 ASCII-only, 한글은 percent-encoded 로
        filename_quoted = quote(filename, safe='')
        resp['Content-Disposition'] = (
            f'attachment; filename="lotto_history.csv"; '
            f"filename*=UTF-8''{filename_quoted}"
        )
        return resp

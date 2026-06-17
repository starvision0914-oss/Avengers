"""API endpoints for the Lohas Selenium jobs."""
from __future__ import annotations

from rest_framework import views, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import runner


def _job_payload(job: runner.Job, since: int = 0) -> dict:
    data = job.to_dict()
    data['logs'] = job.snapshot_logs(since=since)
    return data


class RestockStartView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = (request.data.get('user') or '').strip()
        password = (request.data.get('password') or '').strip()
        codes = (request.data.get('codes') or '').strip()
        if not user or not password or not codes:
            return Response(
                {'detail': 'user, password, codes are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        args = ['--user', user, '--password', password, '--codes', codes]
        job = runner.start_job('restock', 'restock.py', args)
        return Response(_job_payload(job), status=status.HTTP_201_CREATED)


class BulkEditListCategoriesView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = (request.data.get('user') or '').strip()
        password = (request.data.get('password') or '').strip()
        if not user or not password:
            return Response(
                {'detail': 'user, password required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        args = ['list-categories', '--user', user, '--password', password]
        job = runner.start_job('bulk_edit_list', 'bulk_edit.py', args)
        return Response(_job_payload(job), status=status.HTTP_201_CREATED)


class BulkEditRunView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = (request.data.get('user') or '').strip()
        password = (request.data.get('password') or '').strip()
        mode = (request.data.get('mode') or '1.0').strip()
        categories = request.data.get('categories') or []
        if isinstance(categories, list):
            categories_str = ','.join(categories)
        else:
            categories_str = str(categories)
        if not user or not password or not categories_str or mode not in ('1.0', '2.0'):
            return Response(
                {'detail': 'user, password, categories, mode(1.0|2.0) required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        args = [
            'run',
            '--user', user,
            '--password', password,
            '--mode', mode,
            '--categories', categories_str,
        ]
        job = runner.start_job('bulk_edit_run', 'bulk_edit.py', args)
        return Response(_job_payload(job), status=status.HTTP_201_CREATED)


class JobDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: str):
        try:
            since = int(request.query_params.get('since', '0'))
        except ValueError:
            since = 0
        job = runner.get_job(job_id)
        if not job:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_job_payload(job, since=since))


class JobStopView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id: str):
        ok = runner.stop_job(job_id)
        if not ok:
            return Response(
                {'detail': 'cannot stop job'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job = runner.get_job(job_id)
        return Response(_job_payload(job) if job else {})


class JobListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jobs = [j.to_dict() for j in runner.list_jobs()[:30]]
        return Response(jobs)

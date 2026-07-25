from rest_framework.views import APIView
from rest_framework.response import Response
from .models import TistoryAccount, TistoryPost


class AccountListView(APIView):
    def get(self, request):
        accounts = TistoryAccount.objects.all()
        return Response([{
            'id': a.id, 'login_id': a.login_id, 'blog_name': a.blog_name,
            'display_name': a.display_name, 'is_active': a.is_active,
            'cookie_saved_at': a.cookie_saved_at.isoformat() if a.cookie_saved_at else None,
        } for a in accounts])

    def post(self, request):
        d = request.data
        a = TistoryAccount.objects.create(
            login_id=d.get('login_id', ''), login_pw=d.get('login_pw', ''),
            blog_name=d.get('blog_name', ''), display_name=d.get('display_name', ''),
            memo=d.get('memo', ''),
        )
        return Response({'id': a.id})


class AccountDetailView(APIView):
    def get(self, request, pk):
        a = TistoryAccount.objects.get(pk=pk)
        return Response({
            'id': a.id, 'login_id': a.login_id, 'blog_name': a.blog_name,
            'display_name': a.display_name, 'is_active': a.is_active, 'memo': a.memo,
        })

    def patch(self, request, pk):
        a = TistoryAccount.objects.get(pk=pk)
        for f in ('login_id', 'login_pw', 'blog_name', 'display_name', 'memo', 'is_active'):
            if f in request.data:
                setattr(a, f, request.data[f])
        a.save()
        return Response({'ok': True})

    def delete(self, request, pk):
        TistoryAccount.objects.filter(pk=pk).delete()
        return Response({'ok': True})


class PostListView(APIView):
    def get(self, request):
        posts = TistoryPost.objects.select_related('account').all()[:200]
        return Response([{
            'id': p.id, 'title': p.title, 'status': p.status,
            'account_id': p.account_id,
            'account_name': p.account.display_name if p.account else '',
            'published_url': p.published_url,
            'created_at': p.created_at.isoformat(),
        } for p in posts])

    def post(self, request):
        d = request.data
        p = TistoryPost.objects.create(
            account_id=d.get('account_id'), title=d.get('title', ''),
            content=d.get('content', ''), tags=d.get('tags', ''),
            category=d.get('category', ''), status='draft',
        )
        return Response({'id': p.id})


class PostDetailView(APIView):
    def get(self, request, pk):
        p = TistoryPost.objects.select_related('account').get(pk=pk)
        return Response({
            'id': p.id, 'title': p.title, 'content': p.content, 'tags': p.tags,
            'category': p.category, 'status': p.status, 'error_message': p.error_message,
            'published_url': p.published_url,
            'account_id': p.account_id,
        })


class PostPublishView(APIView):
    """항상 티스토리 '임시저장'까지만 (안전 기본값). 실제 공개발행은 명시적으로
    mode='publish'를 body에 넣어 호출한 경우만 허용."""
    def post(self, request, pk):
        from crawlers.tistory_crawler import run_publish

        p = TistoryPost.objects.select_related('account').get(pk=pk)
        if not p.account:
            return Response({'error': '계정이 지정되지 않음'}, status=400)

        mode = 'draft'
        if request.data.get('mode') == 'publish':
            mode = 'publish'

        result = run_publish(p.account, p.title, p.content, tags=p.tags, category=p.category, mode=mode)
        if result.get('success'):
            from django.utils import timezone
            p.status = 'published' if mode == 'publish' else 'tistory_draft'
            p.published_url = result.get('url', '')
            p.error_message = ''
            if mode == 'publish':
                p.published_at = timezone.now()
            p.save(update_fields=['status', 'published_url', 'error_message', 'published_at'])
            return Response({'ok': True, 'status': p.status})
        else:
            p.status = 'failed'
            p.error_message = result.get('error', '')
            p.save(update_fields=['status', 'error_message'])
            return Response({'error': result.get('error', '')}, status=400)

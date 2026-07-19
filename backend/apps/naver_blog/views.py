import os
import subprocess
import tempfile
from datetime import date, timedelta

from django.db.models import Count, Q
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import NaverBlogAccount, NaverKeyword, NaverBlogPost, NaverBlogSetting, NaverBlogPostImage


# ──── 계정 ────

class AccountListView(APIView):
    def get(self, request):
        accounts = NaverBlogAccount.objects.filter(is_active=True).order_by('display_order')
        return Response([{
            'id': a.id,
            'login_id': a.login_id,
            'blog_id': a.blog_id,
            'display_name': a.display_name or a.login_id,
            'memo': a.memo,
            'has_pw': bool(a.login_pw),
            'is_active': a.is_active,
            'display_order': a.display_order,
        } for a in accounts])

    def post(self, request):
        d = request.data
        obj = NaverBlogAccount.objects.create(
            login_id=d['login_id'],
            login_pw=d.get('login_pw', ''),
            blog_id=d.get('blog_id', ''),
            display_name=d.get('display_name', ''),
            memo=d.get('memo', ''),
            display_order=d.get('display_order', 99),
        )
        return Response({'id': obj.id}, status=201)


class AccountDetailView(APIView):
    def patch(self, request, pk):
        try:
            obj = NaverBlogAccount.objects.get(pk=pk)
        except NaverBlogAccount.DoesNotExist:
            return Response({'error': 'not found'}, status=404)
        for field in ('login_id', 'login_pw', 'blog_id', 'display_name', 'memo', 'is_active', 'display_order'):
            if field in request.data:
                setattr(obj, field, request.data[field])
        obj.save()
        return Response({'ok': True})

    def delete(self, request, pk):
        NaverBlogAccount.objects.filter(pk=pk).update(is_active=False)
        return Response({'ok': True})


# ──── 키워드 ────

class KeywordListView(APIView):
    def get(self, request):
        qs = NaverKeyword.objects.all().order_by('-priority', '-search_total', 'keyword')
        search = request.query_params.get('q')
        if search:
            qs = qs.filter(keyword__icontains=search)
        competition = request.query_params.get('competition')
        if competition:
            qs = qs.filter(competition=competition)
        active = request.query_params.get('active')
        if active == '1':
            qs = qs.filter(is_active=True)

        data = []
        for kw in qs[:200]:
            data.append({
                'id': kw.id,
                'keyword': kw.keyword,
                'category': kw.category,
                'search_pc': kw.search_pc,
                'search_mobile': kw.search_mobile,
                'search_total': kw.search_total or (kw.search_pc + kw.search_mobile),
                'blog_count': kw.blog_count,
                'competition': kw.competition,
                'priority': kw.priority,
                'is_active': kw.is_active,
                'trend_data': kw.trend_data,
                'last_collected': kw.last_collected.isoformat() if kw.last_collected else None,
                'post_count': kw.naverblogpost_set.count(),
            })
        return Response(data)

    def post(self, request):
        keywords_raw = request.data.get('keywords', '')
        category = request.data.get('category', '')
        priority = int(request.data.get('priority', 0))

        created = []
        for kw in keywords_raw.replace('\n', ',').split(','):
            kw = kw.strip()
            if not kw:
                continue
            obj, _ = NaverKeyword.objects.get_or_create(keyword=kw)
            if category:
                obj.category = category
            if priority:
                obj.priority = priority
            obj.is_active = True
            obj.save()
            created.append(kw)

        return Response({'created': created, 'count': len(created)}, status=201)


class KeywordDetailView(APIView):
    def patch(self, request, pk):
        try:
            obj = NaverKeyword.objects.get(pk=pk)
        except NaverKeyword.DoesNotExist:
            return Response({'error': 'not found'}, status=404)
        for field in ('category', 'priority', 'is_active'):
            if field in request.data:
                setattr(obj, field, request.data[field])
        obj.save()
        return Response({'ok': True})

    def delete(self, request, pk):
        NaverKeyword.objects.filter(pk=pk).delete()
        return Response({'ok': True})


class KeywordCollectView(APIView):
    """백그라운드 키워드 트렌드 수집 트리거"""
    def post(self, request):
        keywords = request.data.get('keywords', '')
        cmd = ['python3', 'manage.py', 'collect_naver_keywords']
        if keywords:
            cmd += ['--keywords', keywords]
        subprocess.Popen(cmd, cwd='/home/rejoice888/Avengers/backend',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return Response({'ok': True, 'message': '수집 시작'})


# ──── 포스트 ────

class PostListView(APIView):
    def get(self, request):
        qs = NaverBlogPost.objects.select_related('account', 'keyword').order_by('-created_at')
        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        account_id = request.query_params.get('account_id')
        if account_id:
            qs = qs.filter(account_id=account_id)

        data = []
        for p in qs[:100]:
            data.append({
                'id': p.id,
                'title': p.title,
                'keyword': p.keyword.keyword if p.keyword else '',
                'account': p.account.display_name if p.account else '',
                'status': p.status,
                'tags': p.tags,
                'content_length': len(p.content),
                'published_url': p.published_url,
                'published_at': p.published_at.isoformat() if p.published_at else None,
                'created_at': p.created_at.isoformat(),
            })
        return Response(data)

    def post(self, request):
        """글 생성 트리거 (Claude API)"""
        keyword = request.data.get('keyword', '')
        account_id = request.data.get('account_id')
        category = request.data.get('category', '')
        context = request.data.get('context', '')
        auto_publish = request.data.get('auto_publish', False)

        if not keyword:
            return Response({'error': 'keyword 필수'}, status=400)

        cmd = ['python3', 'manage.py', 'generate_blog_post', '--keyword', keyword]
        if account_id:
            cmd += ['--account', str(account_id)]
        if category:
            cmd += ['--category', category]
        if context:
            cmd += ['--context', context]
        if auto_publish:
            cmd += ['--publish']

        subprocess.Popen(cmd, cwd='/home/rejoice888/Avengers/backend',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return Response({'ok': True, 'message': f'글 생성 시작: {keyword}'})


class GenerateFromLinkView(APIView):
    """쇼핑 링크 하나로 리뷰형 포스팅 생성 트리거"""
    def post(self, request):
        url = request.data.get('url', '').strip()
        account_id = request.data.get('account_id')
        category = request.data.get('category', '')
        context = request.data.get('context', '')

        if not url:
            return Response({'error': 'url 필수'}, status=400)

        cmd = ['python3', 'manage.py', 'generate_shopping_post', '--url', url]
        if account_id:
            cmd += ['--account', str(account_id)]
        if category:
            cmd += ['--category', category]
        if context:
            cmd += ['--context', context]

        subprocess.Popen(cmd, cwd='/home/rejoice888/Avengers/backend',
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return Response({'ok': True, 'message': '링크에서 상품 정보 확인 후 글 생성 시작 (1~2분 소요)'})


class PostDetailView(APIView):
    def get(self, request, pk):
        try:
            p = NaverBlogPost.objects.select_related('account', 'keyword').get(pk=pk)
        except NaverBlogPost.DoesNotExist:
            return Response({'error': 'not found'}, status=404)
        return Response({
            'id': p.id,
            'title': p.title,
            'content': p.content,
            'tags': p.tags,
            'keyword': p.keyword.keyword if p.keyword else '',
            'account': {'id': p.account.id, 'name': p.account.display_name} if p.account else None,
            'status': p.status,
            'published_url': p.published_url,
            'error_message': p.error_message,
            'created_at': p.created_at.isoformat(),
        })

    def patch(self, request, pk):
        try:
            obj = NaverBlogPost.objects.get(pk=pk)
        except NaverBlogPost.DoesNotExist:
            return Response({'error': 'not found'}, status=404)
        for field in ('title', 'content', 'tags', 'status', 'account_id'):
            if field in request.data:
                setattr(obj, field, request.data[field])
        obj.save()
        return Response({'ok': True})

    def delete(self, request, pk):
        NaverBlogPost.objects.filter(pk=pk).delete()
        return Response({'ok': True})


class PostManualCreateView(APIView):
    """수동 작성 글 저장"""
    def post(self, request):
        d = request.data
        keyword_str = d.get('keyword', '').strip()
        account_id = d.get('account_id')
        status = d.get('status', 'draft')

        kw_obj = None
        if keyword_str:
            kw_obj, _ = NaverKeyword.objects.get_or_create(keyword=keyword_str)

        account = None
        if account_id:
            account = NaverBlogAccount.objects.filter(id=account_id, is_active=True).first()

        post = NaverBlogPost.objects.create(
            account=account,
            keyword=kw_obj,
            title=d.get('title', ''),
            content=d.get('content', ''),
            tags=d.get('tags', ''),
            status=status,
        )
        return Response({'id': post.id, 'status': post.status}, status=201)


class PostPublishView(APIView):
    """특정 포스트 즉시 발행/임시저장"""
    def post(self, request, pk):
        try:
            NaverBlogPost.objects.get(pk=pk)
        except NaverBlogPost.DoesNotExist:
            return Response({'error': 'not found'}, status=404)

        # 실제 발행(공개)은 아직 미검증 + 사용자 요청으로 비활성화. 항상 임시저장만 수행(2026-07-19).
        mode = 'draft'

        subprocess.Popen(
            ['python3', 'manage.py', 'publish_blog_post', '--post-id', str(pk), '--mode', mode],
            cwd='/home/rejoice888/Avengers/backend',
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return Response({'ok': True, 'message': '네이버 임시저장 시작'})


class PostBulkDraftSaveView(APIView):
    """상태=draft(우리 DB 초안)인 글들을 한 번에 네이버 임시저장으로 순차 실행 (계정당 1.5~3.5분 간격, 봇처럼 안 보이게)"""
    def post(self, request):
        limit = int(request.data.get('limit', 50))
        pending = NaverBlogPost.objects.filter(status='draft').count()
        if pending == 0:
            return Response({'ok': False, 'message': '초안 상태인 글이 없습니다'})

        subprocess.Popen(
            ['python3', 'manage.py', 'publish_blog_post', '--status', 'draft',
             '--mode', 'draft', '--limit', str(limit)],
            cwd='/home/rejoice888/Avengers/backend',
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return Response({'ok': True, 'message': f'{min(pending, limit)}건 네이버 임시저장 순차 실행 시작 (간격 두고 진행)'})


# ──── 설정 ────

class SettingView(APIView):
    def get(self, request):
        s = NaverBlogSetting.get()
        return Response({
            'gemini_api_key': '****' if s.gemini_api_key else '',
            'has_gemini': bool(s.gemini_api_key),
            'naver_client_id': s.naver_client_id or os.environ.get('NAVER_CLIENT_ID', ''),
            'has_naver': bool(s.naver_client_id or os.environ.get('NAVER_CLIENT_ID')),
            'style_prompt': s.style_prompt,
        })

    def post(self, request):
        s = NaverBlogSetting.get()
        if 'gemini_api_key' in request.data and request.data['gemini_api_key'] != '****':
            s.gemini_api_key = request.data['gemini_api_key']
        if 'naver_client_id' in request.data:
            s.naver_client_id = request.data['naver_client_id']
        if 'naver_client_secret' in request.data:
            s.naver_client_secret = request.data['naver_client_secret']
        if 'style_prompt' in request.data:
            s.style_prompt = request.data['style_prompt']
        s.save()
        return Response({'ok': True})


# ──── 제미나이 글 생성 ────

UPLOAD_DIR = '/tmp/blog_images'


class GeneratePostView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        keyword = request.data.get('keyword', '').strip()
        category = request.data.get('category', '')
        context = request.data.get('context', '')
        account_id = request.data.get('account_id')
        status = request.data.get('status', 'draft')

        if not keyword:
            return Response({'error': 'keyword 필수'}, status=400)

        # 이미지 저장
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        image_paths = []
        for f in request.FILES.getlist('images'):
            ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else 'jpg'
            tmp = tempfile.NamedTemporaryFile(dir=UPLOAD_DIR, suffix=f'.{ext}', delete=False)
            for chunk in f.chunks():
                tmp.write(chunk)
            tmp.close()
            image_paths.append(tmp.name)

        # 제미나이 호출
        try:
            from apps.naver_blog.services.gemini import generate_post_gemini
            result = generate_post_gemini(keyword, category, context, image_paths)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
        finally:
            for p in image_paths:
                try:
                    os.remove(p)
                except Exception:
                    pass

        # 계정 조회
        account = None
        if account_id:
            account = NaverBlogAccount.objects.filter(id=account_id, is_active=True).first()

        kw_obj, _ = NaverKeyword.objects.get_or_create(keyword=keyword)

        post = NaverBlogPost.objects.create(
            account=account,
            keyword=kw_obj,
            title=result['title'],
            content=result['content'],
            tags=result['tags'],
            status=status,
        )

        return Response({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'tags': post.tags,
            'status': post.status,
        }, status=201)


# ──── 포스트 이미지 ────

PERSIST_IMG_DIR = os.path.join(settings.MEDIA_ROOT, 'naver_blog_images')


class PostImageListView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        images = NaverBlogPostImage.objects.filter(post_id=pk).order_by('order')
        return Response([{
            'id': img.id,
            'url': settings.MEDIA_URL + 'naver_blog_images/' + os.path.basename(img.image_path),
            'order': img.order,
            'marker': f'[이미지{i + 1}]',
        } for i, img in enumerate(images)])

    def post(self, request, pk):
        try:
            post = NaverBlogPost.objects.get(pk=pk)
        except NaverBlogPost.DoesNotExist:
            return Response({'error': 'not found'}, status=404)

        f = request.FILES.get('image')
        if not f:
            return Response({'error': 'image 필수'}, status=400)

        os.makedirs(PERSIST_IMG_DIR, exist_ok=True)
        ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else 'jpg'
        fname = f'post{pk}_{int(__import__("time").time() * 1000)}.{ext}'
        fpath = os.path.join(PERSIST_IMG_DIR, fname)
        with open(fpath, 'wb') as out:
            for chunk in f.chunks():
                out.write(chunk)

        next_order = (NaverBlogPostImage.objects.filter(post=post).count())
        img = NaverBlogPostImage.objects.create(post=post, image_path=fpath, order=next_order)
        return Response({
            'id': img.id,
            'url': settings.MEDIA_URL + 'naver_blog_images/' + fname,
            'order': img.order,
            'marker': f'[이미지{next_order + 1}]',
        }, status=201)


class PostChartCreateView(APIView):
    """실제 숫자 데이터로 막대 차트 이미지를 생성해 포스트에 첨부(AI 이미지 생성 대신 —
    Gemini 이미지 모델은 무료 티어 할당량 0이라 사용 불가, 2026-07-19 확인)."""
    def post(self, request, pk):
        try:
            post = NaverBlogPost.objects.get(pk=pk)
        except NaverBlogPost.DoesNotExist:
            return Response({'error': 'not found'}, status=404)

        title = request.data.get('title', '').strip()
        labels = request.data.get('labels') or []
        values = request.data.get('values') or []
        unit = request.data.get('unit', '')
        reference_value = request.data.get('reference_value')
        reference_label = request.data.get('reference_label', '')

        if not title or not labels or not values or len(labels) != len(values):
            return Response({'error': 'title, labels, values(labels와 개수 동일) 필수'}, status=400)
        try:
            values = [float(v) for v in values]
            reference_value = float(reference_value) if reference_value not in (None, '') else None
        except (TypeError, ValueError):
            return Response({'error': 'values/reference_value는 숫자여야 함'}, status=400)

        os.makedirs(PERSIST_IMG_DIR, exist_ok=True)
        fname = f'chart_post{pk}_{int(__import__("time").time() * 1000)}.png'
        fpath = os.path.join(PERSIST_IMG_DIR, fname)

        from apps.naver_blog.services.chart_gen import generate_bar_chart
        try:
            generate_bar_chart(labels, values, title, fpath, unit=unit,
                               reference_value=reference_value, reference_label=reference_label)
        except Exception as e:
            return Response({'error': f'차트 생성 실패: {e}'}, status=500)

        next_order = NaverBlogPostImage.objects.filter(post=post).count()
        img = NaverBlogPostImage.objects.create(post=post, image_path=fpath, order=next_order)
        return Response({
            'id': img.id,
            'url': settings.MEDIA_URL + 'naver_blog_images/' + fname,
            'order': img.order,
            'marker': f'[이미지{next_order + 1}]',
        }, status=201)


class PostImageDetailView(APIView):
    def delete(self, request, pk, image_id):
        img = NaverBlogPostImage.objects.filter(pk=image_id, post_id=pk).first()
        if not img:
            return Response({'error': 'not found'}, status=404)
        try:
            os.remove(img.image_path)
        except OSError:
            pass
        img.delete()
        # 남은 이미지 순번 재정렬 ([이미지N] 마커가 어긋나지 않도록)
        remaining = NaverBlogPostImage.objects.filter(post_id=pk).order_by('order')
        for i, im in enumerate(remaining):
            if im.order != i:
                im.order = i
                im.save(update_fields=['order'])
        return Response({'ok': True})


# ──── 대시보드 통계 ────

class DashboardView(APIView):
    def get(self, request):
        total_keywords = NaverKeyword.objects.filter(is_active=True).count()
        total_accounts = NaverBlogAccount.objects.filter(is_active=True).count()

        status_counts = dict(
            NaverBlogPost.objects.values('status')
            .annotate(cnt=Count('id'))
            .values_list('status', 'cnt')
        )

        recent_posts = NaverBlogPost.objects.select_related('account', 'keyword')\
            .filter(status='published').order_by('-published_at')[:5]

        competition_counts = dict(
            NaverKeyword.objects.filter(is_active=True)
            .values('competition').annotate(cnt=Count('id'))
            .values_list('competition', 'cnt')
        )

        s = NaverBlogSetting.get()
        has_api_key = bool(s.gemini_api_key or os.environ.get('GEMINI_API_KEY'))
        has_naver_key = bool(s.naver_client_id or os.environ.get('NAVER_CLIENT_ID'))

        return Response({
            'total_keywords': total_keywords,
            'total_accounts': total_accounts,
            'post_status': status_counts,
            'competition_dist': competition_counts,
            'has_api_key': has_api_key,
            'has_naver_key': has_naver_key,
            'recent_posts': [{
                'id': p.id,
                'title': p.title,
                'account': p.account.display_name if p.account else '',
                'keyword': p.keyword.keyword if p.keyword else '',
                'published_at': p.published_at.isoformat() if p.published_at else None,
                'url': p.published_url,
            } for p in recent_posts],
        })

"""
python manage.py generate_blog_post --keyword "키워드" [--account ID] [--category "카테고리"]
Claude API로 블로그 글 초안 생성
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.naver_blog.models import NaverKeyword, NaverBlogAccount, NaverBlogPost
from apps.naver_blog.services.content_gen import generate_post


class Command(BaseCommand):
    help = 'Claude API로 블로그 포스팅 초안 생성'

    def add_arguments(self, parser):
        parser.add_argument('--keyword', type=str, required=True)
        parser.add_argument('--account', type=int, help='발행 계정 ID')
        parser.add_argument('--category', type=str, default='')
        parser.add_argument('--context', type=str, default='', help='추가 맥락')
        parser.add_argument('--publish', action='store_true', help='생성 후 즉시 발행')

    def handle(self, *args, **options):
        keyword_str = options['keyword']
        category = options['category']
        context = options['context']

        self.stdout.write(f'[blog] 글 생성 시작: {keyword_str}')

        # 키워드 객체 조회/생성
        kw_obj, _ = NaverKeyword.objects.get_or_create(keyword=keyword_str)

        # 계정 설정
        account = None
        if options['account']:
            account = NaverBlogAccount.objects.filter(id=options['account'], is_active=True).first()
        if not account:
            account = NaverBlogAccount.objects.filter(is_active=True, login_pw__gt='').first()

        if not account:
            self.stdout.write('활성 계정 없음 — draft로 저장')

        # 글 생성
        try:
            result = generate_post(keyword_str, category, context)
        except Exception as e:
            self.stdout.write(f'[blog] 생성 오류: {e}')
            return

        # DB 저장
        post = NaverBlogPost.objects.create(
            account=account,
            keyword=kw_obj,
            title=result['title'],
            content=result['content'],
            tags=result['tags'],
            status='ready' if (account and options['publish']) else 'draft',
        )

        self.stdout.write(f'[blog] 저장 완료: ID={post.id}')
        self.stdout.write(f'  제목: {post.title}')
        self.stdout.write(f'  길이: {len(post.content)}자')
        self.stdout.write(f'  태그: {post.tags}')
        self.stdout.write(f'  상태: {post.status}')

        if options['publish'] and account:
            self.stdout.write(f'[blog] 네이버 임시저장 시작: {account.display_name}')
            from django.core.management import call_command
            # 실제 발행(공개)은 미검증 + 사용자 요청으로 비활성화. mode 생략 시 기본값이
            # 'publish'라 반드시 명시해야 함 — 이걸 놓쳐서 실제 발행 사고가 났었음(2026-07-19).
            call_command('publish_blog_post', post_id=post.id, mode='draft')

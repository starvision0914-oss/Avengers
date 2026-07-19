"""
python manage.py generate_shopping_post --url "https://naver.me/..." [--account ID] [--category ""] [--context ""]
쇼핑커넥트/스마트스토어 상품 링크 하나로: 링크 열어서 실제 가격·평점·리뷰 읽기 → AI 글 생성 → Avengers DB에 초안 저장.
네이버에는 자동으로 안 올라감 — 저장된 초안을 검토 후 '네이버 임시저장' 버튼으로 별도 실행.
"""
from django.core.management.base import BaseCommand

from apps.naver_blog.models import NaverKeyword, NaverBlogAccount, NaverBlogPost, NaverBlogSetting
from apps.naver_blog.services.content_gen import generate_shopping_post, ANTHROPIC_API_KEY
from apps.naver_blog.services.gemini import generate_shopping_post_gemini, _get_api_key as get_gemini_key
from crawlers.browser import create_driver
from crawlers.naver_blog_crawler import ensure_login, resolve_shopping_product


class Command(BaseCommand):
    help = '쇼핑 링크 하나로 리뷰형 블로그 포스팅 초안 생성'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, required=True)
        parser.add_argument('--account', type=int, help='링크 확인/발행에 쓸 네이버 계정 ID')
        parser.add_argument('--category', type=str, default='')
        parser.add_argument('--context', type=str, default='')

    def handle(self, *args, **options):
        url = options['url']
        category = options['category']
        context = options['context']

        account = None
        if options['account']:
            account = NaverBlogAccount.objects.filter(id=options['account'], is_active=True).first()
        if not account:
            account = NaverBlogAccount.objects.filter(is_active=True, login_pw__gt='').first()
        if not account:
            self.stdout.write('[shopping] 네이버 계정 없음 — 상품 정보를 읽어올 수 없어 중단')
            return

        self.stdout.write(f'[shopping] 링크 확인: {url}')
        log_fn = lambda msg: self.stdout.write('  ' + msg)

        driver = None
        try:
            driver = create_driver()
            if not ensure_login(driver, account, log_fn):
                self.stdout.write('[shopping] 로그인 실패 — 중단')
                return
            product_info = resolve_shopping_product(driver, url, log_fn)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        if not product_info.get('title'):
            self.stdout.write('[shopping] 상품 정보를 읽지 못함 — 중단')
            return

        product_match = ' '.join(product_info['title'].split()[:2])
        self.stdout.write(f'[shopping] 쇼핑커넥트 매칭 문자열: "{product_match}"')

        if not ANTHROPIC_API_KEY and not get_gemini_key():
            self.stdout.write('[shopping] Claude/Gemini API 키가 모두 없음 — 설정 탭에서 Gemini API 키를 등록하세요')
            return

        result = None
        last_err = None
        for attempt in range(1, 3):  # 모델이 형식 틀을 그대로 반환하는 간헐적 오류 대비 최대 2회 시도
            try:
                if ANTHROPIC_API_KEY:
                    self.stdout.write(f'[shopping] Claude로 생성 (시도 {attempt})')
                    result = generate_shopping_post(product_info, product_match, category, context)
                else:
                    self.stdout.write(f'[shopping] Gemini로 생성 (시도 {attempt})')
                    result = generate_shopping_post_gemini(product_info, product_match, category, context)
                break
            except Exception as e:
                last_err = e
                self.stdout.write(f'[shopping] 생성 실패(시도 {attempt}): {e}')

        if result is None:
            self.stdout.write(f'[shopping] 생성 최종 실패: {last_err}')
            return

        kw_obj, _ = NaverKeyword.objects.get_or_create(keyword=product_info['title'][:100])

        post = NaverBlogPost.objects.create(
            account=account,
            keyword=kw_obj,
            title=result['title'],
            content=result['content'],
            tags=result['tags'],
            status='draft',
        )

        self.stdout.write(f'[shopping] 저장 완료: ID={post.id}')
        self.stdout.write(f'  제목: {post.title}')
        self.stdout.write(f'  길이: {len(post.content)}자')
        self.stdout.write(f'  태그: {post.tags}')
        self.stdout.write('  상태: draft (네이버 미전송 — "네이버 임시저장"으로 별도 실행 필요)')

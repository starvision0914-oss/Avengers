"""
python manage.py publish_blog_post [--post-id ID] [--status ready]
Selenium으로 네이버 블로그 자동 발행
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.naver_blog.models import NaverBlogPost
from crawlers.browser import create_driver
from crawlers.naver_blog_crawler import ensure_login, write_and_publish

LOCK_FILE = '/tmp/naver_blog_publish.lock'


def _acquire_lock():
    import os
    if os.path.exists(LOCK_FILE):
        try:
            pid = int(open(LOCK_FILE).read().strip().split('|')[0])
            os.kill(pid, 0)
            return False
        except (ProcessLookupError, OSError, ValueError):
            pass
    with open(LOCK_FILE, 'w') as f:
        f.write(f'{os.getpid()}|publish_blog|{timezone.now().isoformat()}')
    return True


def _release_lock():
    import os
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass


class Command(BaseCommand):
    help = '네이버 블로그 포스팅 발행'

    def add_arguments(self, parser):
        parser.add_argument('--post-id', type=int, help='특정 포스트 ID')
        parser.add_argument('--status', type=str, default='ready', help='발행 대상 상태 (기본: ready)')
        parser.add_argument('--limit', type=int, default=5, help='최대 발행 수')
        # 기본값을 draft로 둠(안전 기본값): --mode를 깜빡 빠뜨려도 실수로 실제 발행되지 않도록.
        # 실제 공개 발행은 미검증 + 사용자 요청으로 비활성화 상태(2026-07-19, generate_blog_post.py
        # 호출부가 mode 생략 → 기본값 publish 때문에 실제 발행 사고가 났던 적 있음).
        parser.add_argument('--mode', type=str, default='draft', choices=['publish', 'draft'],
                            help='publish=네이버에 실제 발행(공개), draft=네이버 자체 임시저장(비공개, 기본값)')

    def handle(self, *args, **options):
        if not _acquire_lock():
            self.stdout.write('[publish] 이미 실행 중 — 건너뜀')
            return

        try:
            self._run(options)
        finally:
            _release_lock()

    def _run(self, options):
        if options['post_id']:
            posts = NaverBlogPost.objects.filter(id=options['post_id']).select_related('account', 'keyword')
        else:
            posts = NaverBlogPost.objects.filter(
                status=options['status']
            ).select_related('account', 'keyword').order_by('created_at')[:options['limit']]

        posts = list(posts)
        if not posts:
            self.stdout.write('[publish] 발행할 포스팅 없음')
            return

        mode = options['mode']
        self.stdout.write(f'[publish] 대상: {len(posts)}개 (mode={mode})')

        # 계정별로 그룹핑하여 로그인 1회
        from collections import defaultdict
        by_account = defaultdict(list)
        for p in posts:
            if p.account:
                by_account[p.account.id].append(p)
            else:
                self.stdout.write(f'  [skip] post={p.id} 계정 없음')

        for account_id, acc_posts in by_account.items():
            account = acc_posts[0].account
            if not account.login_pw:
                self.stdout.write(f'  [{account.display_name}] 비밀번호 없음 — 스킵')
                continue

            driver = None
            try:
                driver = create_driver()
                log_fn = lambda msg: self.stdout.write('    ' + msg)

                if not ensure_login(driver, account, log_fn):
                    for p in acc_posts:
                        p.status = 'failed'
                        p.error_message = '로그인 실패'
                        p.save()
                    continue

                blog_id = account.blog_id or account.login_id

                for post in acc_posts:
                    action_label = '발행' if mode == 'publish' else '네이버 임시저장'
                    image_paths = [
                        img.image_path for img in post.images.order_by('order')
                        if img.image_path
                    ]
                    # mode=draft이고 예전에 저장한 제목이 있으면, 목록에서 그 글을 클릭해 열어 덮어씀(중복 방지)
                    edit_match_title = post.naver_last_saved_title if mode == 'draft' else ''
                    self.stdout.write(f'  [{account.display_name}] {action_label}: {post.title[:30]} (이미지 {len(image_paths)}개)'
                                       + (f' [기존 임시저장 수정 시도: "{edit_match_title[:20]}"]' if edit_match_title else ''))
                    result = write_and_publish(
                        driver,
                        blog_id=blog_id,
                        title=post.title,
                        content=post.content,
                        tags=post.tags,
                        image_paths=image_paths,
                        log_fn=log_fn,
                        publish=(mode == 'publish'),
                        edit_match_title=edit_match_title,
                    )

                    if mode == 'draft':
                        if result:
                            post.status = 'naver_draft'
                            post.naver_last_saved_title = post.title
                            if result != 'saved_draft':
                                post.naver_log_no = result
                        else:
                            post.status = 'failed'
                            post.error_message = '임시저장 실패'
                    elif result and 'blog.naver.com' in result:
                        post.status = 'published'
                        post.published_url = result
                        post.published_at = timezone.now()
                    else:
                        post.status = 'failed'
                        post.error_message = f'발행 후 URL 없음: {result}'
                    post.save()

                    import time, random
                    time.sleep(random.randint(90, 210))  # 계정당 글 저장 간격(봇 패턴처럼 안 보이게 사람 간격에 가깝게)

            except Exception as e:
                self.stdout.write(f'  [{account.display_name}] 오류: {e}')
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

        self.stdout.write('[publish] 전체 완료')

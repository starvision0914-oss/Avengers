"""
python manage.py publish_blog_post [--post-id ID] [--status ready]
Selenium으로 네이버 블로그 자동 발행
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.naver_blog.models import NaverBlogPost
from crawlers.browser import create_driver
from crawlers.naver_blog_crawler import login_naver, write_and_publish

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

        self.stdout.write(f'[publish] 대상: {len(posts)}개')

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

                if not login_naver(driver, account.login_id, account.login_pw, log_fn):
                    for p in acc_posts:
                        p.status = 'failed'
                        p.error_message = '로그인 실패'
                        p.save()
                    continue

                blog_id = account.blog_id or account.login_id

                for post in acc_posts:
                    self.stdout.write(f'  [{account.display_name}] 발행: {post.title[:30]}')
                    url = write_and_publish(
                        driver,
                        blog_id=blog_id,
                        title=post.title,
                        content=post.content,
                        tags=post.tags,
                        log_fn=log_fn,
                    )

                    if url and 'blog.naver.com' in url:
                        post.status = 'published'
                        post.published_url = url
                        post.published_at = timezone.now()
                    else:
                        post.status = 'failed'
                        post.error_message = f'발행 후 URL 없음: {url}'
                    post.save()

                    import time
                    time.sleep(30)  # 계정당 글 발행 간격

            except Exception as e:
                self.stdout.write(f'  [{account.display_name}] 오류: {e}')
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

        self.stdout.write('[publish] 전체 완료')

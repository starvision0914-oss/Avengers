from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '티스토리 글 임시저장(기본)/발행 테스트'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', type=int, required=True)
        parser.add_argument('--title', type=str, required=True)
        parser.add_argument('--content', type=str, required=True)
        parser.add_argument('--tags', type=str, default='')
        parser.add_argument('--mode', type=str, default='draft', choices=['draft', 'publish'])

    def handle(self, *args, **options):
        from apps.tistory_blog.models import TistoryAccount
        from crawlers.tistory_crawler import run_publish

        account = TistoryAccount.objects.get(id=options['account_id'])
        log_fn = lambda m: self.stdout.write(m)
        result = run_publish(
            account, options['title'], options['content'],
            tags=options['tags'], mode=options['mode'], log_fn=log_fn,
        )
        self.stdout.write(str(result))

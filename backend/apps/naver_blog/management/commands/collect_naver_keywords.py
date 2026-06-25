"""
python manage.py collect_naver_keywords [--keywords "키워드1,키워드2"] [--all]
네이버 데이터랩 트렌드 + 블로그 수 수집
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.naver_blog.models import NaverKeyword
from apps.naver_blog.services.datalab import get_trend
from apps.naver_blog.services.keywordmaster import collect_keyword_data


class Command(BaseCommand):
    help = '네이버 키워드 트렌드 + 경쟁도 수집'

    def add_arguments(self, parser):
        parser.add_argument('--keywords', type=str, help='콤마 구분 키워드 (미입력시 DB 전체 활성)')
        parser.add_argument('--all', action='store_true', help='비활성 포함 전체')

    def handle(self, *args, **options):
        if options['keywords']:
            kw_list = [k.strip() for k in options['keywords'].split(',') if k.strip()]
            # DB에 없으면 생성
            for kw in kw_list:
                NaverKeyword.objects.get_or_create(keyword=kw)
        else:
            qs = NaverKeyword.objects.all() if options['all'] else NaverKeyword.objects.filter(is_active=True)
            kw_list = list(qs.values_list('keyword', flat=True))

        if not kw_list:
            self.stdout.write('수집할 키워드 없음')
            return

        self.stdout.write(f'[keyword] 대상: {len(kw_list)}개')

        # 데이터랩 (5개씩 배치)
        trend_map = {}
        for i in range(0, len(kw_list), 5):
            batch = kw_list[i:i+5]
            result = get_trend(batch)
            trend_map.update(result)
            if result:
                self.stdout.write(f'  데이터랩 수집: {list(result.keys())}')

        # 키워드별 저장
        for kw in kw_list:
            data = collect_keyword_data(kw)
            trend_data = trend_map.get(kw)

            NaverKeyword.objects.filter(keyword=kw).update(
                search_pc=data['search_pc'],
                search_mobile=data['search_mobile'],
                search_total=data['search_total'],
                blog_count=data['blog_count'],
                competition=data['competition'],
                trend_data=trend_data,
                last_collected=timezone.now(),
            )
            self.stdout.write(
                f'  [{kw}] 블로그수={data["blog_count"]:,} 경쟁={data["competition"]}'
            )

        self.stdout.write(f'[keyword] 완료: {len(kw_list)}개')

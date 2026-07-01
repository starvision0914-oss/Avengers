"""지마켓 상품별 광고비(CPC+AI매출업) 리포트 크롤 → GmarketProductAdCost 누적저장.
예) python manage.py crawl_gmarket_ad_report --eid rejoice666
    python manage.py crawl_gmarket_ad_report --year 2026 --month 6   (전체 활성계정)"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = '지마켓 상품별 광고비(CPC+AI) 리포트 크롤·저장'

    def add_arguments(self, parser):
        parser.add_argument('--eid', default=None, help='특정 계정만(login_id). 미지정시 전체 활성계정(공유ESM 서브 제외)')
        parser.add_argument('--year', type=int, default=None)
        parser.add_argument('--month', type=int, default=None)
        parser.add_argument('--months', default=None,
                            help="여러 달 한번에. 예: '1-6'(1~6월) 또는 '1,3,5'. --year 와 함께(기본 올해)")
        parser.add_argument('--ym-from', default=None, help="연도범위 시작 'YYYY-MM' (예 2025-01). --ym-to 와 함께")
        parser.add_argument('--ym-to', default=None, help="연도범위 끝 'YYYY-MM' (예 2026-06)")
        parser.add_argument('--with-keywords', action='store_true',
                            help='계정 광고비 수집 후 같은 세션에서 ROAS≥200 상품 CPC 키워드까지 수집(로그인 1회)')
        parser.add_argument('--with-gsheet', action='store_true',
                            help='같은 세션에서 일자별 리포트(CPC/AI)도 다운로드해 계정별 구글시트 업로드(당월/1일=전월)')

    def handle(self, *args, **o):
        from crawlers.gmarket_ad_report_crawler import run
        today = timezone.localdate()
        year = o['year'] or today.year
        login_ids = [o['eid']] if o['eid'] else None
        wk = o['with_keywords']
        wg = o['with_gsheet']

        # 연도범위(2025-01 ~ 2026-06 처럼 해 넘어가는 기간) 우선
        if o['ym_from'] and o['ym_to']:
            yf, mf = (int(x) for x in o['ym_from'].split('-'))
            yt, mt = (int(x) for x in o['ym_to'].split('-'))
            periods, yy, mm = [], yf, mf
            while (yy, mm) <= (yt, mt):
                periods.append((yy, mm))
                mm += 1
                if mm > 12:
                    mm, yy = 1, yy + 1
            self.stdout.write(f'지마켓 상품별 광고비 크롤 {o["ym_from"]}~{o["ym_to"]} ({len(periods)}개월) / 대상={o["eid"] or "전체(대표만)"}')
            res = run(login_ids=login_ids, periods=periods, log_fn=lambda m: self.stdout.write(m), with_keywords=wk)
            self.stdout.write(str(res))
            return

        periods = None
        if o['months']:
            ms = []
            for part in str(o['months']).split(','):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-'); ms += list(range(int(a), int(b) + 1))
                elif part:
                    ms.append(int(part))
            periods = [(year, m) for m in sorted(set(ms)) if 1 <= m <= 12]
            self.stdout.write(f'지마켓 상품별 광고비 크롤 {year}년 {[m for _, m in periods]}월 / 대상={o["eid"] or "전체"}')
            res = run(login_ids=login_ids, periods=periods, log_fn=lambda m: self.stdout.write(m), with_keywords=wk)
        else:
            if o['month']:
                month = o['month']
            elif today.day == 1:
                from datetime import timedelta
                prev = today - timedelta(days=1)
                year, month = prev.year, prev.month
            else:
                month = today.month
            self.stdout.write(f'지마켓 상품별 광고비 크롤 {year}-{month:02d} / 대상={o["eid"] or "전체"}'
                              + (' +일자별구글시트' if wg else '') + (' [1일→전월]' if today.day == 1 and not o['month'] else ''))
            res = run(login_ids=login_ids, year=year, month=month, log_fn=lambda m: self.stdout.write(m),
                      with_keywords=wk, with_gsheet=wg)
        self.stdout.write(str(res))

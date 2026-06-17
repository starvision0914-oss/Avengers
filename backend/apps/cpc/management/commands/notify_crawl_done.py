"""시간별 광고비 '전계정 크롤 종료' 텔레그램 알림.
매시간 광고비 크롤(지마켓 09~19시 / 11번가 17~20시)이 전 계정을 다 돌고 끝난 시점에
완료 시각·계정수·소요시간·오늘 누적 광고비를 텔레그램으로 통지한다.
사용: manage.py notify_crawl_done --platform gmarket --started 09:00:01
"""
import datetime
import pytz
from django.core.management.base import BaseCommand
from django.db.models import Sum


class Command(BaseCommand):
    help = '시간별 광고비 전계정 크롤 종료 알림(텔레그램)'

    def add_arguments(self, parser):
        parser.add_argument('--platform', required=True, choices=['gmarket', '11st'])
        parser.add_argument('--started', default=None, help='크롤 시작 HH:MM:SS (소요시간 계산용)')
        parser.add_argument('--no-telegram', action='store_true', help='발송 없이 출력만')

    def handle(self, *args, **o):
        from apps.cpc import eleven_block_guard as guard
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.datetime.now(kst)
        today = now.date()
        plat = o['platform']

        if plat == 'gmarket':
            from apps.cpc.models import GmarketCostHistory as H
            qs = H.objects.filter(use_date=today, transaction_type__in=['CPC', 'AI매출업'])
            label = '지마켓 시간별 광고비(09~19시)'
        else:  # 11st — transaction_datetime은 aware(UTC) → KST 오늘 범위로 필터(__date 금지)
            from apps.cpc.models import ElevenCostHistory as H
            s = kst.localize(datetime.datetime.combine(today, datetime.time.min))
            e = s + datetime.timedelta(days=1)
            qs = H.objects.filter(transaction_datetime__gte=s, transaction_datetime__lt=e,
                                  transaction_type='CPC')
            label = '11번가 시간별 광고비(17~20시)'

        total = abs(qs.aggregate(s=Sum('amount'))['s'] or 0)
        nacc = qs.values('seller_id').distinct().count()

        dur = ''
        if o['started']:
            try:
                st = datetime.datetime.strptime(o['started'], '%H:%M:%S').time()
                stdt = kst.localize(datetime.datetime.combine(today, st))
                mins = max(0, int((now - stdt).total_seconds() // 60))
                dur = f' · 소요 {mins}분'
            except Exception:
                pass

        body = (f'🟢 [{label}] 전계정 크롤 완료\n'
                f'{now:%H:%M} 종료{dur}\n'
                f'오늘 광고비발생 {nacc}계정 · 누적 {total:,}원')
        self.stdout.write(body)
        if not o['no_telegram']:
            guard._send_telegram_alert(body)
            self.stdout.write('→ 텔레그램 발송 완료')

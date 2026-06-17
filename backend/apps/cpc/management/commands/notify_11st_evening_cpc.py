"""11번가 17시(기본) 이후 발생한 CPC 광고비를 계정별로 텔레그램 알림.
DB만 읽음(크롤 없음). 17시 이후 발생 광고비가 없으면 발송하지 않는다.
시간당 체크 크론(cron_11st_evening_cpc.sh)에서 호출."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '11번가 17시 이후 발생 광고비(CPC) 텔레그램 알림 (없으면 미발송)'

    def add_arguments(self, parser):
        parser.add_argument('--after-hour', type=int, default=17, help='기준 시각(기본 17시)')

    def handle(self, *args, **opts):
        from crawlers.eleven_crawler import _alert_evening_cpc
        sent = _alert_evening_cpc(after_hour=opts['after_hour'])
        self.stdout.write(f'17시이후 광고비 알림 발송={sent} (False=발생없음/미발송)')

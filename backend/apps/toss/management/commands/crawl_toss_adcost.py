import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from crawlers.toss_crawler import collect_all
from apps.toss.models import TossAdCost


class Command(BaseCommand):
    help = '토스쇼핑 파트너스 광고비 수집 (기본: 어제) — 완료 후 텔레그램 결과 통지'

    def add_arguments(self, parser):
        parser.add_argument('--when', default='yesterday', choices=['yesterday', 'today'])

    def handle(self, *args, **opts):
        when = opts['when']
        results = collect_all(when=when)
        target_date = timezone.localtime().date() - datetime.timedelta(days=1 if when == 'yesterday' else 0)

        lines = [f'🔔 [토스 광고비] {target_date} 수집 결과']
        for login_id, ok in results.items():
            self.stdout.write(f'{login_id}: {"성공" if ok else "실패"}')
            if ok:
                rec = TossAdCost.objects.filter(date=target_date).first()
                cost = f'{rec.exec_ad_cost:,}원' if rec else '-'
                lines.append(f'✅ {login_id}: {cost}')
            else:
                lines.append(f'⚠️ {login_id}: 실패 — 확인 필요')

        msg = '\n'.join(lines)
        try:
            from apps.cpc import eleven_block_guard as guard
            guard._send_telegram_alert(msg)
        except Exception as e:
            self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(msg)

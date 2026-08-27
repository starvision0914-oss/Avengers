"""지마켓 간편광고(CPC2)+일반광고(CPC1) 전체계정 ON 여부 점검(2026-08-27 사용자 요청).
비용증가 여부와 무관하게 전체 24개 계정을 순서대로 확인해 ON이 있으면 그 자리에서 바로 끄고
다음 계정으로 진행. 17시 이후에만 실행(그 전엔 정상 운영시간이라 ON이 당연함)."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 전체계정 간편+일반광고 ON 여부 점검 후 즉시 OFF(17시 이후 전용)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='OFF 실행 없이 조회만')
        parser.add_argument('--force', action='store_true', help='17시 이전이어도 강제 실행(테스트용)')

    def handle(self, *args, **opts):
        from django.utils import timezone
        from apps.cpc.models import CrawlerAccount, protected_login_ids

        now = timezone.localtime()
        if now.hour < 17 and not opts['force']:
            self.stdout.write(f'{now.strftime("%H:%M")} — 17시 이전이라 스킵(정상 운영시간)')
            return

        qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
        protected = protected_login_ids('gmarket')
        if protected:
            qs = qs.exclude(login_id__in=protected)
        accts = [a for a in qs.order_by('display_order', 'login_id')
                 if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

        from crawlers.gmarket_cpc2_control_crawler import run_control
        from apps.cpc import eleven_block_guard as guard

        found_on = []
        for a in accts:
            login_id = a.login_id
            if opts['dry_run']:
                self.stdout.write(f'[{login_id}] 조회 예정(DRY-RUN이라 실제 조회는 생략)')
                continue
            self.stdout.write(f'=== [{login_id}] 간편+일반광고 ON 확인 ===')
            results = run_control('off', source='schedule', log_fn=lambda m: self.stdout.write(m),
                                   account_filter=[login_id], include_cpc1=True)
            for r in results or []:
                if r and r.get('before_on', 0) > 0:
                    found_on.append(f"{login_id}: ON {r.get('before_on')}건 발견 → OFF")
            self.stdout.write(f'=== [{login_id}] 완료 — 다음 계정 진행 ===')

        if opts['dry_run']:
            self.stdout.write(f'DRY-RUN — 대상 {len(accts)}개 계정 (실제 조회 안 함)')
            return

        if not found_on:
            msg = f"✅ [지마켓 간편+일반광고 전체점검] {now.strftime('%m/%d %H:%M')}\n{len(accts)}개 계정 전부 OFF 상태 확인됨"
        else:
            msg = (f"🛑 [지마켓 간편+일반광고 전체점검] {now.strftime('%m/%d %H:%M')}\n"
                   f"ON 상태로 발견돼 OFF 처리한 계정 {len(found_on)}개\n"
                   + "\n".join(f"  · {r}" for r in found_on))
        try:
            guard._send_telegram_alert(msg)
        except Exception as e:
            self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(self.style.SUCCESS(msg))

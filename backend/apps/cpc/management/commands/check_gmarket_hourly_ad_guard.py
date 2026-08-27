"""지마켓 시간별 광고비 가드(2026-08-27 사용자 요청).
17시부터 매시간, 계정을 하나씩 순서대로 확인 → 직전 시간 대비 늘었으면 그 자리에서 바로 끄고
다음 계정으로 진행(전체를 먼저 다 확인한 뒤 나중에 몰아서 끄지 않음).
거래내역상 간편(CPC2)과 일반(CPC1)은 구분이 안 돼 항상 묶어서 같이 끄지만, AI광고는
별도 항목(ai_usage)으로 분리 수집되므로 증가 원인에 따라 선택적으로 끈다:
  - AI 사용액만 늘었으면 → AI광고만 OFF
  - CPC(간편+일반) 사용액만 늘었으면 → 간편+일반광고만 OFF
  - 둘 다 늘었으면 → 둘 다 OFF
안 늘었으면 아무 것도 안 하고 바로 다음 계정.

crawl_gmarket_cost가 만드는 GmarketDepositSnapshot(매시 정각, 09-21시)을 그대로 사용 —
비교 자체는 DB 조회만으로 끝나 로그인 불필요, OFF가 필요한 계정만 그 자리에서 로그인해 처리."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 계정을 하나씩 확인하며 직전시간 대비 광고비 증가 원인(AI/CPC)에 따라 즉시 선택적 OFF'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='OFF 실행 없이 대상만 출력')

    def handle(self, *args, **opts):
        from django.utils import timezone
        from apps.cpc.models import GmarketDepositSnapshot, CrawlerAccount, protected_login_ids

        now = timezone.localtime()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
        protected = protected_login_ids('gmarket')
        if protected:
            qs = qs.exclude(login_id__in=protected)
        # 공유ESM 서브 제외(대표만) — 서브는 대표 스냅샷에 합쳐져 있음(notify_gmarket_adcost_hourly와 동일 원칙)
        accts = [a for a in qs.order_by('display_order', 'login_id')
                 if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

        from crawlers.gmarket_ai_control_crawler import run_control as run_ai_control
        from crawlers.gmarket_cpc2_control_crawler import run_control as run_cpc2_control
        from apps.cpc import eleven_block_guard as guard

        acted_rows = []
        ai_off_cnt = cpc_off_cnt = 0

        for a in accts:
            login_id = a.login_id
            snaps = list(GmarketDepositSnapshot.objects
                         .filter(gmarket_id=login_id, collected_at__gte=day_start)
                         .order_by('collected_at'))
            if len(snaps) < 2:
                self.stdout.write(f'{login_id}: 스냅샷 부족(비교불가) — 스킵')
                continue

            cur, prev = snaps[-1], snaps[-2]
            cur_ai, prev_ai = cur.ai_usage, prev.ai_usage
            cur_cpc, prev_cpc = cur.gmarket_cpc + cur.auction_cpc, prev.gmarket_cpc + prev.auction_cpc
            ai_diff, cpc_diff = cur_ai - prev_ai, cur_cpc - prev_cpc
            need_ai = ai_diff > 0
            need_cpc = cpc_diff > 0

            if not (need_ai or need_cpc):
                self.stdout.write(f'{login_id}: AI {prev_ai:,}→{cur_ai:,} / CPC {prev_cpc:,}→{cur_cpc:,} 문제없음')
                continue

            tag = ' '.join(t for t in (f'AI +{ai_diff:,}' if need_ai else '',
                                        f'CPC +{cpc_diff:,}' if need_cpc else '') if t)
            self.stdout.write(f'{login_id}: AI {prev_ai:,}→{cur_ai:,} / CPC {prev_cpc:,}→{cur_cpc:,} ⛔ {tag}')

            if opts['dry_run']:
                acted_rows.append(f'{login_id}: {tag} (DRY-RUN, 미실행)')
                continue

            # 확인 즉시 그 자리에서 OFF — 전체를 다 확인한 뒤 나중에 몰아서 처리하지 않음
            if need_ai:
                self.stdout.write(f'=== [{login_id}] AI광고 OFF ===')
                run_ai_control('off', source='schedule', log_fn=lambda m: self.stdout.write(m),
                                account_filter=[login_id])
                ai_off_cnt += 1
            if need_cpc:
                self.stdout.write(f'=== [{login_id}] 간편+일반광고 OFF ===')
                run_cpc2_control('off', source='schedule', log_fn=lambda m: self.stdout.write(m),
                                  account_filter=[login_id], include_cpc1=True)
                cpc_off_cnt += 1
            self.stdout.write(f'=== [{login_id}] 완료 — 다음 계정 진행 ===')
            acted_rows.append(f'{login_id}: {tag}')

        if not acted_rows:
            self.stdout.write(self.style.SUCCESS('증가 계정 없음 — OFF 없음'))
            return

        if opts['dry_run']:
            self.stdout.write('DRY-RUN — 실제 OFF 미실행\n' + '\n'.join(acted_rows))
            return

        msg = (f"🛑 [지마켓 시간별 광고비 가드] {now.strftime('%m/%d %H:%M')}\n"
               f"AI OFF {ai_off_cnt}계정 · CPC(간편+일반) OFF {cpc_off_cnt}계정\n"
               + "\n".join(f"  · {r}" for r in acted_rows))
        try:
            guard._send_telegram_alert(msg)
        except Exception as e:
            self.stderr.write(f'텔레그램 발송 실패: {e}')
        self.stdout.write(self.style.SUCCESS(f'{len(acted_rows)}개 계정 처리 완료'))

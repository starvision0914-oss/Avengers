"""지마켓 신규광고센터 ROAS 100%+ 상품의 키워드 자동 수집(2026-09-19 신설).
gmarket_newad_product_cost(당월 누적)에서 계정별 ROAS 100%+ 상품을 뽑아 키워드별 리포트로
매칭 — 상품별 광고비 크론(09:00, 락='gmarket_newad_product')이 그날 데이터를 다 채운 뒤에
돌아야 그날치 ROAS 기준으로 정확하게 뽑히므로 더 늦은 시각에 예약. 같은 락 네임스페이스를
써서 상품별 광고비 수집과는 자동으로 순서가 맞춰지고(같은 락), 옥션 거래원장 수집(platform=
'gmarket')과는 여전히 독립적으로 동시 실행된다."""
from datetime import date, timedelta

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 신규광고센터 ROAS 100%+ 상품 키워드 전계정 수집'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')
        parser.add_argument('--min-roas', type=float, default=100.0)

    def handle(self, *args, **opts):
        from django.db.models import Sum
        from apps.cpc.models import CrawlerAccount, GmarketNewAdProductCost
        from apps.cpc import eleven_block_guard as guard
        from crawlers.gmarket_new_adcenter_control import collect_product_keywords, NEWAD_DL
        from crawlers.browser import create_driver

        ok, reason = guard.preflight('지마켓신규광고센터키워드', platform='gmarket_newad_product', wait=True)
        if not ok:
            self.stdout.write(f'스킵 — {reason}')
            return

        try:
            since = date.today().replace(day=1)
            until = date.today() - timedelta(days=1)
            if since > until:
                self.stdout.write('이번달 1일 실행 — 조회 가능한 날짜 없음, 스킵')
                return

            grp = (GmarketNewAdProductCost.objects
                   .filter(use_date__gte=since, use_date__lte=until)
                   .values('login_id', 'product_no')
                   .annotate(cost=Sum('cost'), conv=Sum('conv_amount'))
                   .filter(cost__gt=0))
            targets = {}
            for g in grp:
                roas = (g['conv'] or 0) * 100.0 / g['cost']
                if roas >= opts['min_roas']:
                    targets.setdefault(g['login_id'], []).append(g['product_no'])

            if opts.get('accounts'):
                targets = {k: v for k, v in targets.items() if k in opts['accounts']}

            # 상품별 광고비와 같은 이유로 뒤에서부터 처리(같은 락이라 순서 자체는 자동으로
            # 맞춰지지만, 락 대기 중에도 서로 다른 계정 먼저 잡을 여지를 줄임).
            login_ids = list(reversed(targets.keys()))
            self.stdout.write(f'대상 {len(login_ids)}개 계정, 총 {sum(len(v) for v in targets.values())}개 상품(ROAS {opts["min_roas"]}%+)')

            driver = create_driver(download_dir=NEWAD_DL, kill_existing=False)
            success, failed = 0, 0
            try:
                for login_id in login_ids:
                    acct = CrawlerAccount.objects.filter(platform='gmarket', login_id=login_id).first()
                    if not acct:
                        self.stdout.write(f'[{login_id}] 계정없음 — 스킵')
                        failed += 1
                        continue
                    try:
                        r = collect_product_keywords(driver, login_id, acct.password_enc,
                                                      targets[login_id], since, until, log_fn=self.stdout.write)
                        if r is not None:
                            success += 1
                        else:
                            failed += 1
                    except Exception as e:
                        self.stdout.write(f'[{login_id}] 오류: {e}')
                        failed += 1
            finally:
                driver.quit()

            self.stdout.write(self.style.SUCCESS(f'완료 — 성공 {success} / 실패 {failed}'))
        finally:
            guard.release_global_lock(platform='gmarket_newad_product')

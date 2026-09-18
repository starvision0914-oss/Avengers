"""지마켓 신규광고센터(adcenter.esmplus.com) 상품별×날짜별 광고비 전계정 수집(2026-09-18 신설).

2026-09-18 실측 검증: adcenter.esmplus.com은 signin.esmplus.com/ad.esmplus.com(구광고센터·
거래원장/옥션 수집이 쓰는 로그인)과 완전히 별도 인증 시스템 — 서로 다른 계정으로 동시에
로그인/조회해도 '다른광고주가 선택되었습니다' 충돌이나 캡차 없이 정상 동작함을 확인(2계정씩
동시 테스트, 옥션쪽 2/2·지마켓쪽 2/2 성공). 그래서 전역락(platform='gmarket')을 공유하지 않고
별도 락 네임스페이스(platform='gmarket_newad_product')를 써서 거래원장/옥션 수집·AI상태크롤·
CPC ON/OFF 등 기존 지마켓 크론들과 동시 실행되도록 함(사용자 확정, 2026-09-18).
⚠️ 단, kill_existing=False 필수 — 그렇지 않으면 다른 지마켓 크론의 Chrome을 죽여버림."""
from datetime import date, timedelta

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '지마켓 신규광고센터 상품별 광고비 전계정 수집'

    def add_arguments(self, parser):
        parser.add_argument('--accounts', nargs='*')

    def handle(self, *args, **opts):
        from apps.cpc.models import CrawlerAccount, protected_login_ids
        from apps.cpc import eleven_block_guard as guard
        from crawlers.gmarket_new_adcenter_control import collect_product_costs, NEWAD_DL
        from crawlers.browser import create_driver

        ok, reason = guard.preflight('지마켓신규광고센터상품별', platform='gmarket_newad_product', wait=True)
        if not ok:
            self.stdout.write(f'스킵 — {reason}')
            return

        try:
            if opts.get('accounts'):
                accts = list(CrawlerAccount.objects.filter(platform='gmarket', login_id__in=opts['accounts']))
            else:
                qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
                protected = protected_login_ids('gmarket') - {'dlwodb777'}
                if protected:
                    qs = qs.exclude(login_id__in=protected)
                accts = [a for a in qs.order_by('display_order', 'login_id')
                         if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]
                # 거래원장/옥션 수집(cron_gmarket_adcost_month.sh)이 앞에서부터(1번→) 도는 것과
                # 겹치는 시간대가 있어도 같은 계정을 동시에 건드릴 확률을 낮추려고 뒤에서부터
                # 처리(2026-09-18 사용자 요청).
                accts = list(reversed(accts))

            since = date.today().replace(day=1)
            until = date.today() - timedelta(days=1)

            # kill_existing=False 필수 — True면 동시에 도는 다른 지마켓 크론의 Chrome을 죽여버림.
            driver = create_driver(download_dir=NEWAD_DL, kill_existing=False)
            success, failed = 0, 0
            try:
                for acct in accts:
                    try:
                        r = collect_product_costs(driver, acct.login_id, acct.password_enc,
                                                   since, until, log_fn=self.stdout.write)
                        if r is not None:
                            success += 1
                        else:
                            failed += 1
                    except Exception as e:
                        self.stdout.write(f'[{acct.login_id}] 오류: {e}')
                        failed += 1
            finally:
                driver.quit()

            self.stdout.write(self.style.SUCCESS(f'완료 — 성공 {success} / 실패 {failed}'))
        finally:
            guard.release_global_lock(platform='gmarket_newad_product')

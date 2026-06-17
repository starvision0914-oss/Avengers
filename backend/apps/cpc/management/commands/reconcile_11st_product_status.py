"""11번가 나의상품 '판매중지(목록이탈)' 정정.

근본문제: crawl_11st_products는 셀러오피스 상품엑셀에 '나온' 상품만 upsert(갱신)한다.
판매중지/종료되어 엑셀에서 빠진 상품은 행이 갱신되지 않아 status_type이 마지막으로 본
'판매중'에 그대로 얼어붙는다(stale). → 적자/ROAS 판단 시 '판매중'으로 오판.

판별: 한 계정의 한 회차 수집은 모든 상품이 동일한 synced_at(그 회차 시각)을 받는다.
따라서 `synced_at < 그 계정의 MAX(synced_at)` = 이번 최신 수집 목록에서 빠진 상품 = 판매중지/이탈.

안전장치:
- 최근(--days, 기본 2일) 안에 수집된 계정만 대상(오래 안 돈 계정은 export 신선도 보장 안 됨).
- 한 계정에서 이탈 비율이 --max-frac(기본 0.6) 초과면 '부분수집/실패' 의심으로 건너뜀(대량 오탐 방지).
- 이미 판매중지/판매종료인 행은 건드리지 않음(멱등). 재등록되면 다음 크롤이 자동 복원.
"""
from django.core.management.base import BaseCommand
from django.db.models import Max, Count
from django.utils import timezone
from datetime import timedelta

STOPPED_LABELS = {'판매중지', '판매종료'}
DELISTED_LABEL = '판매중지'


def reconcile(days=2, max_frac=0.6, account_filter=None, dry_run=False, log=print):
    from apps.cpc.models import CrawlerAccount, ElevenMyProduct
    now = timezone.now()
    qs = CrawlerAccount.objects.filter(platform='11st', is_active=True)
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    total_marked = 0
    skipped_partial = []
    for a in qs:
        agg = ElevenMyProduct.objects.filter(account=a).aggregate(m=Max('synced_at'), n=Count('id'))
        mx, n = agg['m'], agg['n']
        if not mx or n == 0:
            continue
        if (now - mx) > timedelta(days=days):
            continue  # 최근 수집 없음 → 신선도 보장 안 됨, 건너뜀
        cand = ElevenMyProduct.objects.filter(account=a, synced_at__lt=mx).exclude(status_type__in=STOPPED_LABELS)
        cnt = cand.count()
        if cnt == 0:
            continue
        if cnt / n > max_frac:
            skipped_partial.append((a.login_id, cnt, n))
            log(f'⚠️  {a.login_id}: 이탈 {cnt}/{n} ({cnt*100//n}%) — 부분수집 의심, 건너뜀')
            continue
        if not dry_run:
            cand.update(status_type=DELISTED_LABEL)
        total_marked += cnt
        log(f'{a.login_id}: {cnt}건 → 판매중지(목록이탈){" [dry-run]" if dry_run else ""}')
    return {'marked': total_marked, 'skipped_partial': skipped_partial}


class Command(BaseCommand):
    help = "11번가 나의상품: 최신 수집목록에서 빠진(판매중지/이탈) 상품의 status_type을 정정"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='변경 없이 대상만 출력')
        parser.add_argument('--days', type=int, default=2, help='최근 N일 내 수집된 계정만 대상(기본 2)')
        parser.add_argument('--max-frac', type=float, default=0.6, help='이탈비율 초과 시 건너뜀(부분수집 방지, 기본 0.6)')
        parser.add_argument('--account', nargs='*', help='특정 login_id만')

    def handle(self, *args, **opts):
        r = reconcile(days=opts['days'], max_frac=opts['max_frac'],
                      account_filter=opts.get('account'), dry_run=opts['dry_run'],
                      log=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(
            f"정정 완료: {r['marked']}건 판매중지 처리"
            f"{' (dry-run)' if opts['dry_run'] else ''}"
            f"{', 부분수집의심 건너뜀 %d계정' % len(r['skipped_partial']) if r['skipped_partial'] else ''}"))

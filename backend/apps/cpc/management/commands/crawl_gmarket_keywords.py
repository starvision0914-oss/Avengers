"""지마켓 CPC 키워드별 실적 수집 — 대상 상품번호(기본=CPC ROAS≥200%)의 키워드 추출.

대상 산정: 선택 기간(ym_from~ym_to) 집계에서 ad_type=cpc & ROAS≥roas_min & 구매금액>0 인 상품번호.
명시 상품번호(--product-nos, 엑셀업로드용)를 주면 그걸 우선 사용(login_id는 광고비 데이터로 매핑).
크롤은 기간 내 각 월별로 수행(GmarketKeywordReport는 월 단위 멱등 저장).
"""
import calendar
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone


def _months(ym_from, ym_to):
    y0, m0 = ym_from
    y1, m1 = ym_to
    if (y0, m0) > (y1, m1):
        (y0, m0), (y1, m1) = (y1, m1), (y0, m0)
    out, yy, mm = [], y0, m0
    while (yy, mm) <= (y1, m1):
        out.append((yy, mm))
        mm += 1
        if mm > 12:
            mm, yy = 1, yy + 1
    return out[-12:]


def _parse_ym(s, default):
    try:
        y, m = str(s).split('-')
        return (int(y), int(m))
    except Exception:
        return default


class Command(BaseCommand):
    help = '지마켓 CPC 키워드별 실적 수집(대상=CPC ROAS≥200% 상품 또는 지정 상품번호)'

    def add_arguments(self, parser):
        today = timezone.localdate()
        parser.add_argument('--ym-from', default=f'{today.year}-{today.month:02d}')
        parser.add_argument('--ym-to', default=f'{today.year}-{today.month:02d}')
        parser.add_argument('--roas-min', type=float, default=200.0)
        parser.add_argument('--eid', default='', help='특정 로그인 계정만')
        parser.add_argument('--product-nos', nargs='*', default=None,
                            help='대상 상품번호 직접 지정(엑셀업로드). 미지정시 CPC ROAS≥roas-min 자동 산정')
        parser.add_argument('--year', type=int, default=None,
                            help='연도-누적 버킷 모드: 그 해 전체를 상품당 1회 범위조회로 수집(month=0 저장)')

    def handle(self, *args, **opts):
        from django.db.models import Sum, Q
        from datetime import date
        from apps.cpc.models import GmarketProductAdCost
        from crawlers.gmarket_keyword_crawler import run

        today = timezone.localdate()

        # ── 연도-누적 버킷 모드 ──
        if opts.get('year'):
            yr = int(opts['year'])
            roas_min = opts['roas_min']
            eid = opts['eid'] or ''
            base = GmarketProductAdCost.objects.filter(year=yr, ad_type='cpc')
            if eid:
                base = base.filter(login_id=eid)
            grp = (base.values('product_no', 'login_id')
                   .annotate(cost=Sum('cost'), conv=Sum('conv_amount')).filter(cost__gt=0))
            targets = {}
            for g in grp:
                roas = (g['conv'] or 0) * 100.0 / g['cost'] if g['cost'] else 0
                if (g['conv'] or 0) > 0 and roas >= roas_min:
                    targets.setdefault(g['login_id'], []).append(g['product_no'])
            if not targets:
                self.stdout.write('대상 상품 없음 — 종료'); return
            start = date(yr, 1, 1)
            end = min(date(yr, 12, 31), today)   # 현재연도는 오늘까지
            n = sum(len(v) for v in targets.values())
            self.stdout.write(f'[연도버킷 {yr}] 대상 {len(targets)}계정 / {n}상품 · 범위 {start}~{end} · ROAS≥{roas_min}')
            res = run(targets, year=yr, month=0, log_fn=lambda m: self.stdout.write(m),
                      date_range=(start.isoformat(), end.isoformat()))
            self.stdout.write(self.style.SUCCESS(f'완료: {res}'))
            return
        ymf = _parse_ym(opts['ym_from'], (today.year, today.month))
        ymt = _parse_ym(opts['ym_to'], (today.year, today.month))
        months = _months(ymf, ymt)
        roas_min = opts['roas_min']
        eid = opts['eid'] or ''
        explicit = [str(p).strip() for p in (opts['product_nos'] or []) if str(p).strip()]

        from django.db.models import Q
        mq = Q()
        for (yy, mm) in months:
            mq |= Q(year=yy, month=mm)

        base = GmarketProductAdCost.objects.filter(mq, ad_type='cpc')
        if eid:
            base = base.filter(login_id=eid)

        # 대상 상품번호 → login_id 매핑
        targets = {}
        if explicit:
            pno_set = {''.join(ch for ch in p if ch.isdigit()) for p in explicit}
            pno_set.discard('')
            lid_by_pno = {}
            for r in base.filter(product_no__in=pno_set).values('product_no', 'login_id'):
                lid_by_pno.setdefault(r['product_no'], r['login_id'])
            for pno in pno_set:
                lid = lid_by_pno.get(pno) or eid
                if not lid:
                    self.stdout.write(f'  ⚠️ 상품 {pno}: login_id 매핑 실패(광고비 데이터 없음) — 건너뜀')
                    continue
                targets.setdefault(lid, []).append(pno)
        else:
            grp = (base.values('product_no', 'login_id')
                   .annotate(cost=Sum('cost'), conv=Sum('conv_amount'))
                   .filter(cost__gt=0))
            for g in grp:
                roas = (g['conv'] or 0) * 100.0 / g['cost'] if g['cost'] else 0
                if (g['conv'] or 0) > 0 and roas >= roas_min:
                    targets.setdefault(g['login_id'], []).append(g['product_no'])

        if not targets:
            self.stdout.write('대상 상품 없음 — 종료')
            return
        n_pno = sum(len(v) for v in targets.values())
        self.stdout.write(f'대상 {len(targets)}계정 / {n_pno}상품 · 기간 {opts["ym_from"]}~{opts["ym_to"]} '
                          f'· {len(months)}개월 · ROAS≥{roas_min}')
        for (yy, mm) in months:
            self.stdout.write(f'── {yy}-{mm:02d} 키워드 수집 ──')
            res = run(targets, year=yy, month=mm, log_fn=lambda m: self.stdout.write(m))
            self.stdout.write(f'  결과: {res}')
        self.stdout.write(self.style.SUCCESS('완료'))

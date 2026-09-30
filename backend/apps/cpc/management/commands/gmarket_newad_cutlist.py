"""지마켓 신규광고센터 '무전환 상품' 컷 리스트 생성(읽기 전용, 2026-09-30).

GmarketNewAdProductCost(상품별×날짜별 광고비)를 기간 합산해서 광고비가 일정 이상 나갔는데 판매자 전환이
0건인 상품을 계정별로 뽑아 엑셀로 저장한다. 광고를 끄거나 그룹에서 상품을 빼는 판단용이며, 이 명령은
광고센터에 접속하지도 DB를 바꾸지도 않는다(파일만 생성).

  python manage.py gmarket_newad_cutlist                     # 이번 달 1일~어제, 광고비 3,000원 이상
  python manage.py gmarket_newad_cutlist --min-cost 5000 --days 14
"""
import datetime as dt
import os

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum

OUT_DIR = '/home/rejoice888/PUBLIC/지마켓_신규광고센터_분석'


class Command(BaseCommand):
    help = '신규광고센터 무전환 상품 컷 리스트 엑셀 생성(읽기 전용)'

    def add_arguments(self, parser):
        parser.add_argument('--from', dest='date_from', help='시작일 YYYY-MM-DD (기본: 이번 달 1일)')
        parser.add_argument('--to', dest='date_to', help='종료일 YYYY-MM-DD (기본: 데이터의 마지막 날)')
        parser.add_argument('--days', type=int, default=0, help='종료일 기준 최근 N일(지정 시 --from 무시)')
        parser.add_argument('--min-cost', type=int, default=3000, help='기간 광고비가 이 금액 이상인 상품만')
        parser.add_argument('--out', default='', help='저장 경로(기본: PUBLIC 폴더)')

    def handle(self, *args, **o):
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter
        from apps.cpc.models import GmarketNewAdProductCost as P, GmarketMyProduct as G
        from apps.cpc.eleven_my_product_service import get_lcode_soldout_rows

        last = P.objects.order_by('-use_date').values_list('use_date', flat=True).first()
        if not last:
            self.stdout.write('신규광고센터 상품별 데이터 없음')
            return
        d_to = dt.date.fromisoformat(o['date_to']) if o['date_to'] else last
        if o['days']:
            d_from = d_to - dt.timedelta(days=o['days'] - 1)
        elif o['date_from']:
            d_from = dt.date.fromisoformat(o['date_from'])
        else:
            d_from = d_to.replace(day=1)

        agg = (P.objects.filter(use_date__gte=d_from, use_date__lte=d_to)
               .values('login_id', 'product_no')
               .annotate(cost=Sum('cost'), conv=Sum('conv_amount'), clk=Sum('clicks'), imp=Sum('impressions'),
                         days=Count('use_date', distinct=True)))
        names = dict(P.objects.filter(use_date__gte=d_from, use_date__lte=d_to)
                     .order_by('use_date').values_list('product_no', 'product_name'))

        cand = [a for a in agg if a['conv'] == 0 and a['cost'] >= o['min_cost']]
        pnos = {a['product_no'] for a in cand}
        status = dict(G.objects.filter(product_no__in=pnos).values_list('product_no', 'status_type'))
        lsold = {pno for _, pno in get_lcode_soldout_rows(G, 'seller_product_code', 'product_no', 'status_type', '판매중')}

        by_acct = {}
        for a in cand:
            by_acct.setdefault(a['login_id'], []).append(a)
        for v in by_acct.values():
            v.sort(key=lambda x: -x['cost'])

        total_cost = sum(a['cost'] for a in agg)
        wb = openpyxl.Workbook()
        ws0 = wb.active
        ws0.title = '요약'
        head = Font(bold=True, color='FFFFFF')
        fill = PatternFill('solid', fgColor='1F4E79')
        ws0.append([f'무전환 상품 컷 리스트 — 기간 {d_from} ~ {d_to} · 기간 광고비 {o["min_cost"]:,}원 이상 · 전환 0건'])
        ws0.append([f'전체 광고비 {total_cost:,}원 · 컷 후보 {len(cand):,}개 상품 · 후보 광고비 {sum(a["cost"] for a in cand):,}원'
                    f' ({sum(a["cost"] for a in cand) * 100 // max(1, total_cost)}%)'])
        ws0.append([])
        ws0.append(['계정', '컷 후보 상품수', '후보 광고비', '계정 전체 광고비', '후보 비중(%)', '이미 판매중 아님', 'L코드 품절/미확인'])
        for c in ws0[4]:
            c.font, c.fill = head, fill
        acct_tot = {}
        for a in agg:
            acct_tot[a['login_id']] = acct_tot.get(a['login_id'], 0) + a['cost']
        for lid, rows in sorted(by_acct.items(), key=lambda kv: -sum(x['cost'] for x in kv[1])):
            c = sum(x['cost'] for x in rows)
            ws0.append([lid, len(rows), c, acct_tot.get(lid, 0), round(c * 100 / max(1, acct_tot.get(lid, 0)), 1),
                        sum(1 for x in rows if status.get(x['product_no']) not in (None, '판매중')),
                        sum(1 for x in rows if x['product_no'] in lsold)])

        ws = wb.create_sheet('컷후보_전체')
        ws.append(['계정', '상품번호', '상품명', '기간 광고비', '클릭', '노출', '광고 일수', '판매상태', 'L코드 품절/미확인'])
        for c in ws[1]:
            c.font, c.fill = head, fill
        for lid, rows in sorted(by_acct.items(), key=lambda kv: -sum(x['cost'] for x in kv[1])):
            for a in rows:
                ws.append([lid, a['product_no'], names.get(a['product_no'], '')[:80], a['cost'], a['clk'], a['imp'],
                           a['days'], status.get(a['product_no'], '(나의상품에 없음)'),
                           'O' if a['product_no'] in lsold else ''])
        ws.freeze_panes = 'A2'
        for wsx in (ws0, ws):
            for i, w in enumerate((14, 16, 60, 14, 8, 8, 10, 16, 18), 1):
                wsx.column_dimensions[get_column_letter(i)].width = w

        os.makedirs(OUT_DIR, exist_ok=True)
        out = o['out'] or os.path.join(OUT_DIR, f'무전환상품_컷리스트_{d_from:%Y-%m-%d}_{d_to:%Y-%m-%d}.xlsx')
        wb.save(out)
        self.stdout.write(self.style.SUCCESS(
            f'저장: {out}\n계정 {len(by_acct)}개 · 컷 후보 {len(cand):,}개 · 후보 광고비 {sum(a["cost"] for a in cand):,}원 '
            f'(전체 {total_cost:,}원의 {sum(a["cost"] for a in cand) * 100 // max(1, total_cost)}%)'))

"""상품번호→판매자코드 영구 보존(ProductCodeArchive) 적재.
- --snapshot: 현재 나의상품(11번가/지마켓) 카탈로그에서 판매자코드 있는 상품을 보존고에 upsert (매일 크론용).
- --ingest-csv <path> --platform <11st|gmarket>: 받아둔 적자/ROAS 엑셀(상품번호·판매자코드 컬럼)을 보존고에 적재(과거 복구).
판매자코드가 비어있는 행은 적재하지 않음(기존 보존값 보호)."""
import csv
from django.core.management.base import BaseCommand
from django.utils import timezone


def _upsert(records, source):
    """records: [(platform, login_id, product_no, seller_code, product_name), ...] — 판매자코드 있는 것만."""
    from apps.cpc.models import ProductCodeArchive
    now = timezone.now()
    objs = []
    for platform, login_id, pno, sc, name in records:
        pno = str(pno or '').strip()
        sc = str(sc or '').strip()
        if not pno or not sc:
            continue
        objs.append(ProductCodeArchive(
            platform=platform, login_id=(login_id or '')[:100], product_no=pno[:50],
            seller_code=sc[:100], product_name=(name or '')[:500], source=source, last_seen=now))
    n = 0
    for i in range(0, len(objs), 2000):
        batch = objs[i:i + 2000]
        ProductCodeArchive.objects.bulk_create(
            batch, update_conflicts=True,
            update_fields=['login_id', 'seller_code', 'product_name', 'source', 'last_seen'], batch_size=2000)
        n += len(batch)
    return n


class Command(BaseCommand):
    help = '상품번호→판매자코드 영구 보존고 적재(스냅샷/CSV)'

    def add_arguments(self, p):
        p.add_argument('--snapshot', action='store_true')
        p.add_argument('--ingest-csv')
        p.add_argument('--platform', default='')

    def handle(self, *a, **o):
        from apps.cpc.models import ElevenMyProduct, GmarketMyProduct
        if o.get('ingest_csv'):
            plat = o['platform']
            if plat not in ('11st', 'gmarket'):
                self.stderr.write('--platform 11st|gmarket 필요'); return
            with open(o['ingest_csv'], encoding='utf-8-sig') as f:
                rows = list(csv.reader(f))
            hdr = rows[0]
            def idx(*names):
                for i, h in enumerate(hdr):
                    if any(n in h for n in names):
                        return i
                return -1
            pi, si, ai, ni = idx('상품번호'), idx('판매자코드'), idx('아이디', '계정'), idx('상품명')
            if pi < 0 or si < 0:
                self.stderr.write(f'상품번호/판매자코드 컬럼 못찾음: {hdr}'); return
            recs = []
            for r in rows[1:]:
                if len(r) <= max(pi, si):
                    continue
                recs.append((plat, r[ai] if ai >= 0 and len(r) > ai else '', r[pi], r[si],
                             r[ni] if ni >= 0 and len(r) > ni else ''))
            n = _upsert(recs, source='excel')
            self.stdout.write(f'CSV 적재({plat}): {len(recs)}행 중 판매자코드 있는 {n}건 보존')
            return

        # 기본/--snapshot: 현재 카탈로그 스냅샷
        e = list(ElevenMyProduct.objects.exclude(seller_product_code='')
                 .values_list('account__login_id', 'product_no', 'seller_product_code', 'product_name'))
        ne = _upsert([('11st', a, p, s, nm) for a, p, s, nm in e], source='crawl')
        g = list(GmarketMyProduct.objects.exclude(seller_product_code='')
                 .values_list('account__login_id', 'product_no', 'seller_product_code', 'product_name'))
        ng = _upsert([('gmarket', a, p, s, nm) for a, p, s, nm in g], source='crawl')
        from apps.cpc.models import ProductCodeArchive
        self.stdout.write(f'스냅샷 보존: 11번가 {ne}건 / 지마켓 {ng}건 | 보존고 총 {ProductCodeArchive.objects.count()}건')

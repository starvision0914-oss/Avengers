import glob
import os

from django.core.management.base import BaseCommand

from apps.ownerclan import services


class Command(BaseCommand):
    help = 'PlayAuto "11번가 등록현황" .xls/zip 파일을 예비상품으로 적재(값 가공 없이 있는 그대로)'

    def add_arguments(self, parser):
        parser.add_argument('paths', nargs='*', help='파일 경로 또는 글롭')
        parser.add_argument('--dir', help='폴더 내 *.zip 전체 적재')

    def handle(self, *args, **opts):
        paths = list(opts.get('paths') or [])
        if opts.get('dir'):
            paths += sorted(glob.glob(os.path.join(opts['dir'], '*.zip')))
        # 글롭 확장
        expanded = []
        for p in paths:
            expanded += sorted(glob.glob(p)) if any(c in p for c in '*?[') else [p]
        paths = [p for p in expanded if os.path.exists(p)]
        if not paths:
            self.stderr.write('적재할 파일이 없습니다.')
            return

        tot = {'inserted': 0, 'updated': 0, 'skipped': 0}
        for p in paths:
            self.stdout.write(f'[적재] {os.path.basename(p)}')
            try:
                res = services.ingest_playauto(path=p, log_fn=lambda m: self.stdout.write(m))
            except Exception as e:
                self.stderr.write(f'  실패: {e}')
                continue
            for k in tot:
                tot[k] += res.get(k, 0)
            self.stdout.write(self.style.SUCCESS(f'  → 신규 {res["inserted"]} / 갱신 {res["updated"]}'))
        self.stdout.write(self.style.SUCCESS(
            f'전체 완료: 신규 {tot["inserted"]} / 갱신 {tot["updated"]} (파일 {len(paths)}개)'))

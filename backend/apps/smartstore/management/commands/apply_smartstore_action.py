"""스마트스토어 대량 액션(판매중지/가격맞추기/고단가인하)을 백그라운드 프로세스로 실행.
기존엔 Django runserver 프로세스 안의 daemon Thread로 돌았는데, 그 서버 프로세스가
pm2 restart 등으로 재시작되면 스레드가 그 즉시 통째로 죽어 로그 한 줄 못 남기고 사라지는
문제가 있었다(2026-08-26 실측: 사용자가 '가격맞추기' 클릭 → 200 응답까지 받았는데
백엔드 재시작 한 번에 통째로 유실). 11번가/지마켓/롯데온처럼 완전히 분리된 프로세스로
돌려 서버 재시작과 무관하게 끝까지 실행되게 한다."""
import json
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '스마트스토어 선택 상품 판매중지/가격맞추기/고단가인하를 별도 프로세스로 실행'

    def add_arguments(self, parser):
        parser.add_argument('--mode', required=True, choices=['suspend', 'price_match', 'price_cap'])
        parser.add_argument('--ids-file', required=True, help='SmartStoreProduct PK 목록(JSON 배열) 파일 경로')
        parser.add_argument('--log-file', required=True)

    def handle(self, *args, **opts):
        from apps.smartstore.models import SmartStoreProduct
        from apps.smartstore.services.naver_api import _get_access_token, suspend_product_api, update_price_api

        mode = opts['mode']
        log_path = opts['log_file']
        ids = json.load(open(opts['ids_file']))

        targets = list(SmartStoreProduct.objects.select_related('account').filter(pk__in=ids))
        store_groups = {}
        for t in targets:
            store_groups.setdefault(t.account_id, {'account': t.account, 'items': []})['items'].append(t)

        def _log(msg):
            with open(log_path, 'a') as f:
                f.write(msg + '\n')

        mode_label = {'suspend': '판매중지', 'price_match': '단가 마켓가 맞춤', 'price_cap': '고단가 인하'}[mode]
        _log(f'{time.strftime("%F %T")} {mode_label} 시작 — {len(targets)}건 / {len(store_groups)}스토어')

        # 토큰 유효시간이 있어 대형 스토어(수천~1만+건)를 한 계정에서 계속 처리하다 보면
        # 도중에 만료돼 그 뒤 전부 401로 연쇄실패하는 사고가 있었다(2026-08-26 실측: 유진코리아몰
        # 11,907건 처리 중 약 3시간40분 지점에서 토큰 만료 → 남은 항목 전부 401). 15분마다
        # 선제적으로 재발급 + 401을 만나면 즉시 재발급 후 1회 재시도.
        TOKEN_REFRESH_SEC = 900

        success = 0
        fail = 0
        for sid, group in store_groups.items():
            acc = group['account']
            if not acc.commerce_api_key or not acc.commerce_secret_key:
                fail += len(group['items'])
                _log(f'  [{acc.store_name}] API키 미등록 — {len(group["items"])}건 스킵')
                continue
            try:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                token_issued_at = time.time()
            except Exception as e:
                fail += len(group['items'])
                _log(f'  [{acc.store_name}] 토큰 발급 실패: {e}')
                continue

            for item in group['items']:
                if time.time() - token_issued_at > TOKEN_REFRESH_SEC:
                    try:
                        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                        token_issued_at = time.time()
                    except Exception as e:
                        _log(f'  [{acc.store_name}] 토큰 재발급 실패: {e} — 기존 토큰으로 계속')
                try:
                    if mode == 'suspend':
                        suspend_product_api(item.channel_product_no, token)
                        SmartStoreProduct.objects.filter(pk=item.pk).update(status_type='SUSPENSION')
                    else:
                        update_price_api(item.channel_product_no, item.purchase_cost, token)
                        SmartStoreProduct.objects.filter(pk=item.pk).update(sale_price=item.purchase_cost)
                    success += 1
                except Exception as e:
                    if '401' in str(e):
                        # 토큰 만료 의심 — 즉시 재발급 후 1회만 재시도(무한루프 방지)
                        try:
                            token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                            token_issued_at = time.time()
                            if mode == 'suspend':
                                suspend_product_api(item.channel_product_no, token)
                                SmartStoreProduct.objects.filter(pk=item.pk).update(status_type='SUSPENSION')
                            else:
                                update_price_api(item.channel_product_no, item.purchase_cost, token)
                                SmartStoreProduct.objects.filter(pk=item.pk).update(sale_price=item.purchase_cost)
                            success += 1
                            time.sleep(1)
                            continue
                        except Exception as e2:
                            e = e2
                    fail += 1
                    _log(f'  [{acc.store_name}] {item.product_no} 실패: {e}')
                time.sleep(1)

        _log(f'{time.strftime("%F %T")} 완료 — 성공 {success} / 실패 {fail}')
        self.stdout.write(f'완료: 성공 {success} / 실패 {fail}')

"""Claude(나)가 생성한 상품명 결정을 실제 11번가에 적용 (hulk detail 재조회 → PUT)."""
import os, sys, django, json, time
import requests as _requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/home/rejoice888/Avengers/backend')
django.setup()

from apps.cpc.models import CrawlerAccount
from apps.cpc.management.commands.optimize_11st_product_names import (
    _get_session, _get_hulk_detail, _put_hulk_update, _byte_len,
)

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'starvis7942'
DECISIONS_PATH = sys.argv[2] if len(sys.argv) > 2 else '/tmp/11st_ai_decisions.json'

acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='11st')
decisions = json.load(open(DECISIONS_PATH, encoding='utf-8'))
print(f'적용 대상 {len(decisions)}건 (계정: {LOGIN_ID})')

print('로그인 중...')
sess = _get_session(acct)
print('로그인 완료')

ok = fail = skip = 0
for i, d in enumerate(decisions):
    prd_no = d['prd_no']
    if d.get('status') != 'ok':
        print(f'  [{i+1}/{len(decisions)}] {prd_no} SKIP ({d.get("status")}: {d.get("reason","")})')
        skip += 1
        continue
    new_name = d.get('product_name', '')
    promo = d.get('promo_text', '')
    nb = _byte_len(new_name)
    if not new_name or nb > 50 or len(promo) > 20:
        print(f'  [{i+1}/{len(decisions)}] {prd_no} SKIP (byte/char 검증 실패)')
        skip += 1
        continue
    try:
        detail = _get_hulk_detail(sess, prd_no)
        old_name = detail.get('productName', '')
        orig_promo = detail.get('advertisementPhrase')   # 재시도 시 원본 그대로 복원용(키 삭제 아님)
        detail['productName'] = new_name
        if promo:
            detail['advertisementPhrase'] = promo
        try:
            success = _put_hulk_update(sess, prd_no, detail)
        except _requests.exceptions.HTTPError as e:
            body = e.response.text if e.response is not None else ''
            retried = False
            # RAW_MATERIAL(원재료=05인데 origin.code 충돌)만 반응형으로 정리 후 재시도.
            # ★ rawMaterial==05라고 무조건 origin.code를 지우면 원래 정상이던 값(예: '03')까지
            #   같이 날려서 ORIGIN 오류를 새로 만들어냄 — 실제 이 에러가 난 경우에만 손댈 것.
            if 'RAW_MATERIAL' in body and detail.get('origin', {}).get('code'):
                detail['origin']['code'] = None
                try:
                    success = _put_hulk_update(sess, prd_no, detail)
                    retried = True
                except _requests.exceptions.HTTPError:
                    pass
            # CERTIFICATION(인증정보 필수)/ORIGIN(원산지 필수)은 실제 값을 조작할 수 없는
            # 규제필드(허위입력 금지) — 홍보문구는 원본 그대로 되돌리고 상품명만 재시도
            if not retried and promo and any(k in body for k in ('CERTIFICATION', 'ORIGIN')):
                detail['advertisementPhrase'] = orig_promo
                success = _put_hulk_update(sess, prd_no, detail)
                retried = True
            if retried:
                print(f'  [{i+1}/{len(decisions)}] {prd_no} (필수필드 누락 대응 재시도: {body[:60]})')
            else:
                raise
        if success:
            print(f'  [{i+1}/{len(decisions)}] {prd_no} OK | {old_name[:30]} -> {new_name}')
            ok += 1
        else:
            print(f'  [{i+1}/{len(decisions)}] {prd_no} 저장실패(status!=200)')
            fail += 1
    except Exception as e:
        print(f'  [{i+1}/{len(decisions)}] {prd_no} 오류: {e}')
        fail += 1
    time.sleep(1.5)

print(f'\n완료: ok={ok} fail={fail} skip={skip}')

"""스마트스토어 상품명 정리 + 카테고리 연관키워드 추가 + 속성 매핑 (외부 AI API 미사용)

카테고리별 대표키워드를 하드코딩하지 않고, 해당 계정의 실제 등록상품명에서
같은 리프카테고리 내 통계적으로 자기참조 추출한다 — 엉뚱한 카테고리에 무관한
키워드가 붙는 사고(예: 칫솔에 "작업 수공구")를 구조적으로 방지한다.

예상 클린위반 스캔(중복/위험물품/원산지/KC인증/생활화학)에 걸린 상품은 사람 확인이
필요하므로 이 명령에서 자동으로 건드리지 않고 건너뛴다.

사용법:
  python manage.py optimize_smartstore_products_self --account-id 1 --dry-run --limit 20
  python manage.py optimize_smartstore_products_self --account-id 1
"""
import re
import sys
import time
import json
from collections import Counter

import requests
from django.core.management.base import BaseCommand

from apps.smartstore.models import SmartStoreAccount, SmartStoreProduct
from apps.smartstore.services.naver_api import _get_access_token
from apps.smartstore.management.commands.apply_ss_products import clean_name, match_attr, ATTR_RULES
from apps.smartstore.views import _pred_queryset
from crawlers.browser import create_driver
from crawlers.smartstore_crawler import login_smartstore

CATEGORY_CACHE_FILE = '/tmp/category_attr_cache.json'
LOG_PATH = '/tmp/optimize_smartstore_self.jsonl'

_STOP = {'개', '세트', '전용', '용', '및', '겸용', '고급', '신상', '인기', '단품', '색상', '색깔'}

# 카테고리 내 여러 제조사 상품이 섞여있을 때 다른 브랜드 상품에 경쟁사/타사 브랜드명이
# 잘못 붙는 사고 방지(실측: '팔도 왕뚜껑'에 '농심'이 붙음, 2026-07-02). 브랜드성 고유명사는
# 연관키워드 후보에서 원천 제외 — 필요하면 그 상품 자신의 원래 이름에 이미 포함돼 있어야 함.
_BRAND_STOP = {
    '농심', '오뚜기', '팔도', '삼양', '풀무원', 'CJ', '대상', '오리온', '롯데', '해태', '동원',
    '청정원', '샘표', '빙그레', '삼성', 'LG', '애플', '샤오미', '다이슨', '필립스', '테팔', '쿠쿠',
    '한샘', '일룸', '나이키', '아디다스', '뉴발란스', '휠라', '유니클로', '유한킴벌리', '크리넥스', '스카트',
}


def _tokenize(name):
    toks = re.split(r'[\s/,\(\)\[\]\-]+', name)
    return [t for t in toks if len(t) >= 2 and not t.isdigit() and t not in _STOP and t not in _BRAND_STOP]


def _build_category_keywords(products):
    """계정 내 리프카테고리별 대표키워드 자기참조 추출 (최소 3건, 20% 이상 등장 토큰만)"""
    by_cat = {}
    for p in products:
        by_cat.setdefault(p['category_id'], []).append(p['name'])
    cat_kw = {}
    for cat, names in by_cat.items():
        if len(names) < 3:
            continue
        cnt = Counter()
        for n in names:
            cnt.update(set(_tokenize(n)))
        threshold = max(2, int(len(names) * 0.2))
        top = [w for w, c in cnt.most_common(10) if c >= threshold]
        if top:
            cat_kw[cat] = top
    return cat_kw


def _add_keyword(name, cat, cat_kw_map):
    for kw in cat_kw_map.get(cat, []):
        if kw not in name:
            candidate = f'{name} {kw}'
            if len(candidate) <= 100:
                return candidate, kw
            break
    return name, None


def _generic_attr_match(name, attr_groups, already_seq):
    """규칙기반(ATTR_RULES)이 못 채운 속성을, 그 상품 '자기 이름'에 이미 등장하는 네이버 공식
    속성값과 문자 그대로 매칭해 보강. 다른 상품 이름을 빌려오지 않으므로 브랜드 오염 위험 없음."""
    toks = set(_tokenize(name))
    result = []
    for group in attr_groups:
        attr = group.get('attribute', {})
        aseq = attr.get('id')
        if aseq in already_seq:
            continue
        values = attr.get('attributeValues', [])
        cands = [v for v in values if len(v.get('attributeValueText', '')) >= 2
                 and v.get('attributeValueText') in toks]
        if cands:
            best = max(cands, key=lambda v: len(v.get('attributeValueText', '')))
            result.append({'attributeSeq': aseq, 'attributeValueSeq': best.get('attributeValueSeq')})
    return result


class Command(BaseCommand):
    help = '스마트스토어 상품명 정리 + 카테고리 연관키워드 추가 + 속성 매핑 (AI 미사용)'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', type=int, required=True)
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--offset', type=int, default=0)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--name-only', action='store_true', help='속성 매핑 생략(판매자센터 로그인 불필요)')
        parser.add_argument('--sleep', type=float, default=0.4)

    def handle(self, *args, **options):
        account_id = options['account_id']
        dry_run = options['dry_run']
        name_only = options['name_only']
        sleep_sec = options['sleep']

        acc = SmartStoreAccount.objects.get(id=account_id)
        self.stdout.write(f'계정: {acc.store_name} (id={account_id})')

        all_products = list(SmartStoreProduct.objects.filter(
            account_id=account_id, status_type='SALE'
        ).order_by('id').values('id', 'channel_product_no', 'name', 'category_id'))
        self.stdout.write(f'전체 SALE 상품: {len(all_products)}개')

        # 예상 클린위반(중복/위험물품/원산지/KC인증/생활화학) 스캔된 상품은 사람 확인 필요 → 제외
        risk_ids = set()
        for key in ('duplicate', 'danger', 'origin', 'kc', 'chem'):
            risk_ids |= set(_pred_queryset(key).filter(account_id=account_id).values_list('id', flat=True))
        self.stdout.write(f'예상 클린위반 스캔 제외: {len(risk_ids)}개 (사람 확인 필요, 건드리지 않음)')

        cat_kw_map = _build_category_keywords(all_products)
        self.stdout.write(f'카테고리 연관키워드 추출: {len(cat_kw_map)}개 카테고리')

        targets = [p for p in all_products if p['id'] not in risk_ids]
        offset = options['offset']
        limit = options['limit']
        if offset:
            targets = targets[offset:]
        if limit:
            targets = targets[:limit]
        self.stdout.write(f'처리 대상: {len(targets)}개')
        if not targets:
            return

        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        ss = None
        if not name_only:
            self.stdout.write('판매자센터 로그인...')
            driver = create_driver(download_dir='/tmp')
            ok = login_smartstore(driver, acc.login_id, acc.login_pw, self.stdout.write)
            if not ok:
                driver.quit()
                self.stderr.write(self.style.ERROR('판매자센터 로그인 실패'))
                sys.exit(1)
            cookies = {c['name']: c['value'] for c in driver.get_cookies()}
            driver.quit()
            ss = requests.Session()
            for k, v in cookies.items():
                ss.cookies.set(k, v)

        try:
            with open(CATEGORY_CACHE_FILE) as f:
                cat_cache = json.load(f)
        except Exception:
            cat_cache = {}

        ok_cnt = fail_cnt = skip_cnt = 0
        name_changed = attr_changed = 0
        logs = []

        for i, p in enumerate(targets):
            if i > 0 and i % 150 == 0:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

            cno = p['channel_product_no']
            cur_name = p['name'] or ''
            cat = str(p.get('category_id') or '')

            new_name = clean_name(cur_name)
            added_kw = None
            if cat:
                new_name, added_kw = _add_keyword(new_name, cat, cat_kw_map)
            new_name = new_name[:100]
            name_diff = new_name != cur_name

            new_attrs = []
            if not name_only and cat and ss:
                if cat not in cat_cache:
                    try:
                        r = ss.get(
                            f'https://sell.smartstore.naver.com/api/category-attribute/attribute-group?leafCategoryId={cat}',
                            headers={'Referer': 'https://sell.smartstore.naver.com/', 'Accept': 'application/json'},
                            timeout=10)
                        cat_cache[cat] = r.json() if r.ok and r.text else []
                        time.sleep(0.2)
                    except Exception:
                        cat_cache[cat] = []
                matched_seq = set()
                for group in cat_cache.get(cat, []):
                    attr = group.get('attribute', {})
                    matched = match_attr(attr.get('attributeName', ''), new_name, attr.get('attributeValues', []))
                    for av in matched:
                        new_attrs.append({'attributeSeq': attr.get('id'), 'attributeValueSeq': av.get('attributeValueSeq')})
                        matched_seq.add(attr.get('id'))
                # 규칙기반이 못 채운 속성은 상품 자기 이름 문자매칭으로 보강(브랜드 오염 위험 없음)
                new_attrs += _generic_attr_match(new_name, cat_cache.get(cat, []), matched_seq)

            if not name_diff and not new_attrs:
                skip_cnt += 1
                continue

            if (i + 1) % 100 == 0 or i < 5:
                self.stdout.write(f'  [{i+1}/{len(targets)}] {cur_name[:35]} → {new_name[:35]}'
                                  + (f' (+{added_kw})' if added_kw else ''))

            if dry_run:
                continue

            try:
                r = None
                for _ in range(3):
                    r = requests.get(
                        f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                        headers={'Authorization': headers['Authorization']}, timeout=20)
                    if r.status_code == 200:
                        break
                    if r.status_code == 429:
                        time.sleep(5)
                if not r or r.status_code != 200:
                    fail_cnt += 1
                    logs.append({'cno': cno, 'error': f'GET {r.status_code if r else "?"}'})
                    time.sleep(sleep_sec)
                    continue

                data = r.json()
                op = data.get('originProduct', {})
                op['statusType'] = 'SALE'

                if name_diff:
                    op['name'] = new_name
                    name_changed += 1

                da = op.setdefault('detailAttribute', {})
                if new_attrs:
                    da['productAttributes'] = new_attrs
                    attr_changed += 1

                da.pop('seoInfo', None)
                unit_cap = da.get('unitCapacity')
                if unit_cap is None:
                    da['unitCapacity'] = {'unitPriceYn': False}
                elif 'unitPriceYn' not in unit_cap:
                    unit_cap['unitPriceYn'] = False

                pr = None
                for _ in range(3):
                    pr = requests.put(
                        f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                        headers=headers,
                        json={'originProduct': op, 'smartstoreChannelProduct': data.get('smartstoreChannelProduct', {})},
                        timeout=20)
                    if pr.status_code == 200:
                        break
                    if pr.status_code == 429:
                        time.sleep(5)

                if pr is not None and pr.status_code == 200:
                    ok_cnt += 1
                else:
                    fail_cnt += 1
                    logs.append({'cno': cno, 'error': pr.status_code if pr is not None else '?',
                                 'msg': (pr.text[:200] if pr is not None else ''), 'name': cur_name})
            except Exception as e:
                fail_cnt += 1
                logs.append({'cno': cno, 'error': str(e)[:200]})

            if (i + 1) % 100 == 0:
                self.stdout.write(f'  [{i+1}/{len(targets)}] 성공={ok_cnt} 실패={fail_cnt} 스킵={skip_cnt}')
            # 캐시파일이 누적 실행으로 수십~수백MB까지 커져서(2026-07-02 실측 121MB) 매번 통째로
            # 다시 쓰면 갈수록 느려짐 — 저장 주기를 늘려 I/O 부담을 줄인다.
            if (i + 1) % 2000 == 0:
                with open(CATEGORY_CACHE_FILE, 'w') as f:
                    json.dump(cat_cache, f, ensure_ascii=False)

            time.sleep(sleep_sec)

        with open(CATEGORY_CACHE_FILE, 'w') as f:
            json.dump(cat_cache, f, ensure_ascii=False)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            for e in logs:
                f.write(json.dumps({'account_id': account_id, **e}, ensure_ascii=False) + '\n')

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(f'완료: 성공={ok_cnt} 실패={fail_cnt} 스킵(변경없음)={skip_cnt}')
        self.stdout.write(f'  상품명 변경={name_changed}개 / 속성 적용={attr_changed}개')
        if dry_run:
            self.stdout.write('(DRY-RUN — 실제 변경 없음)')
        self.stdout.write(f'로그: {LOG_PATH}')

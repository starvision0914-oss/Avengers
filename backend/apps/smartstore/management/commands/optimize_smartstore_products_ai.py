"""스마트스토어 상품명 + 검색태그 + 속성 AI 최적화 (Claude haiku)

사용법:
  # 드라이런(이름만, API 호출 없이 AI 결과만 확인 — 속성/PUT 없음, 가장 빠름)
  python manage.py optimize_smartstore_products_ai --account-id 1 --limit 5 --dry-run --name-only

  # 드라이런(속성 매칭까지 포함, 판매자센터 로그인 필요)
  python manage.py optimize_smartstore_products_ai --account-id 1 --limit 5 --dry-run

  # 실제 실행
  python manage.py optimize_smartstore_products_ai --account-id 1 --limit 200
"""
import os
import sys
import time
import json
import random
import urllib.request
import urllib.error
import traceback

import requests
from django.core.management.base import BaseCommand

from apps.smartstore.models import SmartStoreAccount, SmartStoreProduct
from apps.smartstore.services.naver_api import _get_access_token
from crawlers.browser import create_driver
from crawlers.smartstore_crawler import login_smartstore

PROMPT_PATH = '/home/rejoice888/PUBLIC/스마트스토어_상품명키워드속성_프롬프트.txt'
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
CATEGORY_CACHE_FILE = '/tmp/category_attr_cache.json'
LOG_PATH = '/tmp/optimize_smartstore_ai.jsonl'


def _load_prompt():
    with open(PROMPT_PATH, encoding='utf-8') as f:
        return f.read()


def _byte_len(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def _call_claude(system_prompt, user_content):
    if not ANTHROPIC_API_KEY:
        raise ValueError('ANTHROPIC_API_KEY 환경변수 없음 — .env에 추가 필요')
    body = json.dumps({
        'model': CLAUDE_MODEL,
        'max_tokens': 1024,
        'system': system_prompt,
        'messages': [{'role': 'user', 'content': user_content}],
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=body,
        headers={
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode('utf-8'))
    return resp['content'][0]['text']


def _parse_json_response(text):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    text = text.strip().rstrip('`').strip()
    return json.loads(text)


def _match_attributes(ai_attrs, attr_groups):
    """AI가 제안한 {속성명: 값텍스트} → 실제 category-attribute-group ID 매핑"""
    if not ai_attrs:
        return []
    result = []
    for group in attr_groups:
        attr = group.get('attribute', {})
        aname = attr.get('attributeName', '')
        if aname not in ai_attrs:
            continue
        want = str(ai_attrs[aname]).strip()
        values = attr.get('attributeValues', [])
        match = next((v for v in values if v.get('attributeValueText') == want), None)
        if not match:
            match = next((v for v in values if want in v.get('attributeValueText', '')
                          or v.get('attributeValueText', '') in want), None)
        if match:
            result.append({'attributeSeq': attr.get('id'), 'attributeValueSeq': match.get('attributeValueSeq')})
    return result


class Command(BaseCommand):
    help = '스마트스토어 상품명 + 검색태그 + 속성 AI 최적화 (Claude haiku)'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', type=int, required=True)
        parser.add_argument('--limit', type=int, default=50)
        parser.add_argument('--offset', type=int, default=0)
        parser.add_argument('--dry-run', action='store_true', help='실제 PUT 없이 AI 결과만 확인')
        parser.add_argument('--name-only', action='store_true', help='속성/태그 매칭 생략(판매자센터 로그인 불필요, 가장 빠름)')
        parser.add_argument('--sleep', type=float, default=1.5)

    def handle(self, *args, **options):
        account_id = options['account_id']
        limit = options['limit']
        offset = options['offset']
        dry_run = options['dry_run']
        name_only = options['name_only']
        sleep_sec = options['sleep']

        if not ANTHROPIC_API_KEY:
            self.stderr.write(self.style.ERROR('ANTHROPIC_API_KEY 환경변수 없음'))
            return

        acc = SmartStoreAccount.objects.get(id=account_id)
        self.stdout.write(f'계정: {acc.store_name} (id={account_id})')

        system_prompt = _load_prompt()
        self.stdout.write(f'프롬프트 로드 완료 ({len(system_prompt)}자)')

        products = list(SmartStoreProduct.objects.filter(
            account_id=account_id, status_type='SALE'
        ).order_by('id').values('channel_product_no', 'name', 'category_id', 'sale_price')[offset:offset + limit])
        self.stdout.write(f'대상: {len(products)}개')
        if not products:
            return

        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        # 속성 매칭용 판매자센터 세션 (name-only면 생략)
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

        ok_cnt = fail_cnt = skip_cnt = risk_cnt = 0
        logs = []

        for i, p in enumerate(products):
            if i > 0 and i % 150 == 0:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

            cno = p['channel_product_no']
            cur_name = p['name'] or ''
            cat = str(p.get('category_id') or '')
            self.stdout.write(f'\n[{i+1}/{len(products)}] {cno} | {cur_name[:40]}')

            user_content = (
                f"원본 상품명: {cur_name}\n"
                f"카테고리ID: {cat}\n"
                f"판매가: {p['sale_price']}원\n"
                f"계정: {acc.store_name}"
            )

            try:
                raw = _call_claude(system_prompt, user_content)
                result = _parse_json_response(raw)
            except Exception as e:
                self.stderr.write(f'  AI 오류: {e}')
                fail_cnt += 1
                continue

            status = result.get('status', 'ok')
            new_name = (result.get('product_name') or '').strip()
            tags = result.get('search_tags') or []
            ai_attrs = result.get('attributes') or {}

            log_entry = {'cno': cno, 'orig': cur_name, 'status': status, **result}
            logs.append(log_entry)

            if status != 'ok':
                self.stdout.write(self.style.WARNING(f'  ⚠ {status}: {result.get("reason", "")}'))
                risk_cnt += 1
                continue

            if not new_name or _byte_len(new_name) > 100:
                self.stdout.write('  → SKIP (이름 비었거나 100byte 초과)')
                skip_cnt += 1
                continue

            self.stdout.write(f'  ✓ {new_name[:40]} | 태그={tags[:3]}... | 속성={ai_attrs}')

            if dry_run:
                self.stdout.write('  → DRY-RUN: 변경 안함')
                if i < len(products) - 1:
                    time.sleep(sleep_sec + random.uniform(0, 0.5))
                continue

            # ── 실제 적용 ──
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
                    raise RuntimeError(f'GET {r.status_code if r else "?"}')

                data = r.json()
                op = data.get('originProduct', {})
                op['statusType'] = 'SALE'
                op['name'] = new_name

                da = op.setdefault('detailAttribute', {})
                orig_seo = da.get('seoInfo')

                if tags:
                    da['seoInfo'] = {'sellerTags': [{'text': t} for t in tags[:10] if t]}
                else:
                    da.pop('seoInfo', None)

                new_attrs = []
                if ss and cat:
                    if cat not in cat_cache:
                        try:
                            cr = ss.get(
                                f'https://sell.smartstore.naver.com/api/category-attribute/attribute-group?leafCategoryId={cat}',
                                headers={'Referer': 'https://sell.smartstore.naver.com/', 'Accept': 'application/json'},
                                timeout=10)
                            cat_cache[cat] = cr.json() if cr.ok and cr.text else []
                            time.sleep(0.2)
                        except Exception:
                            cat_cache[cat] = []
                    new_attrs = _match_attributes(ai_attrs, cat_cache.get(cat, []))
                    if new_attrs:
                        da['productAttributes'] = new_attrs

                unit_cap = da.get('unitCapacity')
                if unit_cap is None:
                    da['unitCapacity'] = {'unitPriceYn': False}
                elif 'unitPriceYn' not in unit_cap:
                    unit_cap['unitPriceYn'] = False

                def _put(payload):
                    pr = None
                    for _ in range(3):
                        pr = requests.put(
                            f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                            headers=headers,
                            json={'originProduct': payload, 'smartstoreChannelProduct': data.get('smartstoreChannelProduct', {})},
                            timeout=20)
                        if pr.status_code == 200:
                            return pr
                        if pr.status_code == 429:
                            time.sleep(5)
                    return pr

                pr = _put(op)
                if pr is None or pr.status_code != 200:
                    # 태그(seoInfo)가 원인일 수 있음 → 되돌리고 재시도
                    if tags:
                        if orig_seo is not None:
                            da['seoInfo'] = orig_seo
                        else:
                            da.pop('seoInfo', None)
                        pr = _put(op)

                if pr is not None and pr.status_code == 200:
                    self.stdout.write(self.style.SUCCESS('  → 저장 완료'))
                    ok_cnt += 1
                else:
                    self.stdout.write(self.style.ERROR(
                        f'  → 저장 실패 {pr.status_code if pr is not None else "?"} {(pr.text[:150] if pr is not None else "")}'))
                    fail_cnt += 1

            except Exception as e:
                self.stderr.write(f'  오류: {e}')
                traceback.print_exc()
                fail_cnt += 1

            if i < len(products) - 1:
                time.sleep(sleep_sec + random.uniform(0, 0.5))

        with open(CATEGORY_CACHE_FILE, 'w') as f:
            json.dump(cat_cache, f, ensure_ascii=False)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            for e in logs:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(f'완료: 성공={ok_cnt} 실패={fail_cnt} 스킵={skip_cnt} 위험/확인필요={risk_cnt}')
        if dry_run:
            self.stdout.write('(DRY-RUN 모드 — 실제 변경 없음)')
        self.stdout.write(f'로그: {LOG_PATH}')

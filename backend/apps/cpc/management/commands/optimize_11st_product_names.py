"""11번가 상품명 AI 최적화 (hulk API + Claude haiku)

사용법:
  # 드라이런 (실제 변경 없이 AI 결과만 확인)
  python manage.py optimize_11st_product_names --account jinag7460 --limit 5 --dry-run

  # 실제 실행
  python manage.py optimize_11st_product_names --account jinag7460 --limit 100

  # 특정 상품만
  python manage.py optimize_11st_product_names --account jinag7460 --prd-no 9465025300

  # 제재위험 상품만 목록 출력
  python manage.py optimize_11st_product_names --account jinag7460 --limit 100 --dry-run --show-risk-only
"""
import os
import sys
import time
import json
import random
import urllib.request
import urllib.error
import traceback

import django
from django.core.management.base import BaseCommand

# 패스 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))))

from apps.cpc.models import CrawlerAccount, ElevenMyProduct
from crawlers import eleven_crawler as _ec
from crawlers.browser import create_driver, stop_display

PROMPT_PATH = '/home/rejoice888/PUBLIC/11번가_상품명_프롬프트.txt'
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
HULK_BASE = 'https://apis.11st.co.kr/product/hulk/v2/product'
APIS_BASE = 'https://apis.11st.co.kr'
LOG_PATH = '/tmp/optimize_11st_names.jsonl'


def _load_prompt():
    with open(PROMPT_PATH, encoding='utf-8') as f:
        return f.read()


def _call_claude(system_prompt: str, user_content: str) -> str:
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


def _parse_json_response(text: str) -> dict:
    """Claude 응답에서 JSON 파싱"""
    # ```json ... ``` 마크다운 블록 제거
    text = text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    text = text.strip().rstrip('`').strip()
    return json.loads(text)


def _get_hulk_detail(sess, prd_no: int) -> dict:
    r = sess.get(f'{HULK_BASE}/{prd_no}/detail', timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get('status') != 200:
        raise ValueError(f'hulk detail 오류: {data}')
    return data['data']


def _put_hulk_update(sess, prd_no: int, payload: dict) -> bool:
    r = sess.put(
        f'{HULK_BASE}/{prd_no}/update',
        params={'createCd': '1201', 'siteCode': ''},
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data.get('status') == 200


def _get_session(acct: CrawlerAccount):
    """셀러오피스 쿠키로 requests 세션 생성"""
    import requests
    driver = create_driver()
    driver.set_page_load_timeout(40)
    _ec._try_cookie_login(driver, acct)
    driver.get('https://soffice.11st.co.kr/view/main')
    time.sleep(3)
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    try:
        driver.quit()
    except Exception:
        pass
    stop_display()

    sess = requests.Session()
    sess.cookies.update(cookies)
    sess.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Referer': 'https://soffice.11st.co.kr/view/main',
        'Origin': 'https://soffice.11st.co.kr',
    })
    return sess


def _byte_len(s: str) -> int:
    return sum(2 if ord(c) > 127 else 1 for c in s)


class Command(BaseCommand):
    help = '11번가 상품명 AI 최적화 (hulk API + Claude haiku)'

    def add_arguments(self, parser):
        parser.add_argument('--account', required=True, help='11st login_id (예: jinag7460)')
        parser.add_argument('--limit', type=int, default=10, help='처리할 최대 상품 수 (기본 10)')
        parser.add_argument('--offset', type=int, default=0, help='시작 오프셋')
        parser.add_argument('--dry-run', action='store_true', help='실제 변경 없이 AI 결과만 출력')
        parser.add_argument('--prd-no', type=int, help='특정 상품번호 하나만 처리')
        parser.add_argument('--show-risk-only', action='store_true', help='제재위험 상품만 표시')
        parser.add_argument('--sleep', type=float, default=2.0, help='상품 간 대기(초, 기본 2)')
        parser.add_argument('--skip-ok-names', action='store_true',
                            help='이미 50byte 이하이고 클린한 이름은 스킵')

    def handle(self, *args, **options):
        login_id = options['account']
        limit = options['limit']
        offset = options['offset']
        dry_run = options['dry_run']
        prd_no_filter = options['prd_no']
        show_risk_only = options['show_risk_only']
        sleep_sec = options['sleep']
        skip_ok = options['skip_ok_names']

        if not ANTHROPIC_API_KEY:
            self.stderr.write(self.style.ERROR(
                'ANTHROPIC_API_KEY 환경변수 없음. .env에 ANTHROPIC_API_KEY=sk-ant-... 추가 필요'))
            return

        try:
            acct = CrawlerAccount.objects.get(login_id=login_id, platform='11st')
        except CrawlerAccount.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'계정 없음: {login_id}'))
            return

        system_prompt = _load_prompt()
        self.stdout.write(f'프롬프트 로드 완료 ({len(system_prompt)}자)')

        # 대상 상품 조회
        qs = ElevenMyProduct.objects.filter(account=acct, status_type='판매중')
        if prd_no_filter:
            qs = qs.filter(product_no=prd_no_filter)
        else:
            qs = qs.order_by('id')[offset:offset + limit]

        products = list(qs)
        self.stdout.write(f'대상 상품 {len(products)}개 (계정: {login_id})')

        if not products:
            self.stdout.write('처리할 상품 없음')
            return

        # 세션 생성 (Selenium 로그인)
        self.stdout.write('셀러오피스 로그인 중...')
        sess = _get_session(acct)
        self.stdout.write('로그인 완료')

        ok_count = 0
        risk_count = 0
        fail_count = 0
        skip_count = 0

        log_entries = []

        for i, mp in enumerate(products):
            prd_no = mp.product_no
            orig_name = mp.product_name or ''
            self.stdout.write(f'\n[{i+1}/{len(products)}] {prd_no} | {orig_name[:40]}')

            # 이미 짧으면 스킵
            if skip_ok and _byte_len(orig_name) <= 50:
                self.stdout.write(f'  → SKIP (이미 {_byte_len(orig_name)}byte)')
                skip_count += 1
                continue

            try:
                # hulk detail 조회
                detail = _get_hulk_detail(sess, prd_no)
                current_name = detail.get('productName', orig_name)
                ad_phrase = detail.get('advertisementPhrase', '')
                category_no = detail.get('displayCategoryNo', '')
                seller_code = detail.get('sellerManagementCode', '')
                brand_name = (detail.get('brand') or {}).get('name', '')
                sell_price = detail.get('sellPrice', '')

                # AI 입력 구성
                user_content = f"""원본 상품명: {current_name}
카테고리번호: {category_no}
현재홍보문구: {ad_phrase}
판매자코드: {seller_code}
브랜드: {brand_name if brand_name and brand_name != '알수없음' else '없음'}
판매가: {sell_price}원"""

                self.stdout.write(f'  AI 요청 중...')
                raw = _call_claude(system_prompt, user_content)

                result = _parse_json_response(raw)
                status = result.get('status', 'ok')
                new_name = result.get('product_name', '')
                promo = result.get('promo_text', '')
                bytes_count = result.get('product_name_bytes', _byte_len(new_name))

                log_entry = {
                    'prd_no': prd_no,
                    'orig': current_name,
                    'new': new_name,
                    'promo': promo,
                    'status': status,
                    'bytes': bytes_count,
                    'reason': result.get('reason', ''),
                }
                log_entries.append(log_entry)

                if status == '제재위험':
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ 제재위험: {result.get("reason","")} | {current_name[:40]}'))
                    risk_count += 1
                else:
                    self.stdout.write(f'  ✓ {new_name[:40]} ({bytes_count}byte) | 홍보: {promo[:20]}')

                    if show_risk_only:
                        pass
                    elif dry_run:
                        self.stdout.write('  → DRY-RUN: 변경 안함')
                    elif new_name and new_name != current_name and bytes_count <= 50:
                        # PUT 업데이트
                        detail['productName'] = new_name
                        if promo:
                            detail['advertisementPhrase'] = promo
                        success = _put_hulk_update(sess, prd_no, detail)
                        if success:
                            self.stdout.write(self.style.SUCCESS(f'  → 저장 완료'))
                            ok_count += 1
                        else:
                            self.stdout.write(self.style.ERROR(f'  → 저장 실패'))
                            fail_count += 1
                    else:
                        self.stdout.write('  → SKIP (변경 없음 or byte 초과)')
                        skip_count += 1

            except urllib.error.HTTPError as e:
                self.stderr.write(f'  Claude API 오류: {e.code} {e.reason}')
                fail_count += 1
            except Exception as e:
                self.stderr.write(f'  오류: {e}')
                traceback.print_exc()
                fail_count += 1

            # 상품 간 대기
            if i < len(products) - 1:
                time.sleep(sleep_sec + random.uniform(0, 1))

        # 결과 요약
        self.stdout.write(f'\n' + '='*50)
        self.stdout.write(f'완료: ok={ok_count} 제재위험={risk_count} 실패={fail_count} 스킵={skip_count}')
        if dry_run:
            self.stdout.write('(DRY-RUN 모드)')

        # 로그 저장
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            for e in log_entries:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')
        self.stdout.write(f'로그: {LOG_PATH}')

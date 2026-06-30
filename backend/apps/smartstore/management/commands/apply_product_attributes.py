"""
스타비젼 상품 속성 일괄 적용
판매자센터 API로 카테고리별 속성 정의 조회 → 규칙 기반 매핑 → 커머스 API PUT
"""
import json
import time
import sys
import re
import requests
from django.core.management.base import BaseCommand
from crawlers.browser import create_driver
from crawlers.smartstore_crawler import login_smartstore
from apps.smartstore.models import SmartStoreAccount
from apps.smartstore.services.naver_api import _get_access_token

INPUT = '/tmp/starvision_products.json'
OUTPUT_LOG = '/tmp/apply_attr_log.json'
DELAY = 1.0
CATEGORY_CACHE_FILE = '/tmp/category_attr_cache.json'

# 속성값 매핑 규칙
ATTR_RULES = {
    '사용대상': {
        'keywords': [
            (['남성', '남자', '남', 'man', 'men', '마스쿨린', '보이', '보이즈', '아저씨', '아저씨', '실버', '미들'], '남성용'),
            (['여성', '여자', '여', 'woman', 'women', '레이디', '걸', '여름', '레이디', '쉬', '시니어여'], '여성용'),
        ],
        'default': '남녀공용',
    },
    '종류': {
        'keywords': [
            (['슬랙스', '정장바지'], '슬랙스'),
            (['조거', '트레이닝'], '조거팬츠'),
            (['반바지', '숏팬츠', '반팬츠'], '숏팬츠/3부'),
            (['청바지', '데님', '진'], '청바지'),
            (['레깅스'], '레깅스'),
            (['면바지'], '면바지'),
            (['부츠컷'], '부츠컷팬츠'),
            (['와이드', '배기', 'wide'], '와이드팬츠'),
        ],
    },
    '주요소재': {
        'keywords': [
            (['데님', '청', '진'], '데님'),
            (['면', '코튼', '순면'], '면'),
            (['폴리', '폴리에스테르'], '폴리에스테르'),
            (['린넨', '마'], '린넨'),
            (['가죽', '레더', 'pu', 'pu가죽'], '인조가죽'),
            (['스웨이드', '스웨이트'], '인조스웨이드'),
            (['나일론', '낚시줄'], '나일론'),
            (['시폰'], '시폰'),
            (['울', '울혼방'], '울혼방'),
            (['기모'], '기모'),
        ],
    },
    '신축성': {
        'keywords': [
            (['스트레치', '신축', '4way', '탄성', '밴딩', '밴드', '스판'], '신축성있음'),
        ],
        'default': '신축성없음',
    },
    '패턴': {
        'keywords': [
            (['체크', '타탄'], '체크'),
            (['스트라이프', '줄무늬', '스트라이프'], '스트라이프'),
            (['도트', '물방울', '점무늬'], '도트'),
            (['프린트', '패턴', '그래픽'], '프린트'),
            (['무지', '단색'], '무지'),
        ],
    },
    '밑위': {
        'keywords': [
            (['로우', '로우라이즈', 'lowrise'], '로우웨이스트'),
            (['하이', '하이웨이스트', '하이라이즈'], '하이웨이스트'),
        ],
        'default': '기본허리선',
    },
    '하의핏': {
        'keywords': [
            (['스키니', '슬림핏', '슬림'], '스키니핏'),
            (['일자', '스트레이트'], '일자핏'),
            (['부츠컷'], '부츠컷핏'),
            (['배기'], '배기핏'),
            (['루즈', '와이드', '오버사이즈', '빅사이즈'], '루즈핏'),
        ],
    },
    '하의기장': {
        'keywords': [
            (['반바지', '숏', '3부', '4부', '5부', '7부', '8부', '9부'], None),
        ],
    },
    '안감': {
        'keywords': [
            (['기모', '기모안감'], '기모'),
            (['융털', '털'], '융털'),
        ],
    },
    '디테일': {
        'keywords': [
            (['밴딩', '밴드', '고무줄'], '밴딩'),
            (['롤업'], '롤업'),
            (['멜빵', '서스펜더'], '멜빵'),
            (['카고', '포켓'], '카고'),
        ],
    },
    '소재': {
        'keywords': [
            (['면', '코튼'], '면'),
            (['폴리', '폴리에스테르'], '폴리에스테르'),
            (['나일론'], '나일론'),
            (['스웨이드'], '인조스웨이드'),
            (['가죽', '레더', 'pu'], '인조가죽'),
            (['울'], '울혼방'),
            (['린넨'], '린넨'),
        ],
    },
    '포인트': {
        'keywords': [
            (['리본'], '리본'),
            (['보석', '크리스탈', '다이아'], '보석'),
            (['플라워', '꽃'], '플라워'),
            (['이니셜'], '이니셜'),
            (['캐릭터', '귀여운'], '캐릭터'),
        ],
        'default': '무지',
    },
    '고정형태': {
        'keywords': [
            (['집게'], '집게형'),
            (['클립'], '클립형'),
            (['꽂이', '꽃이'], '꽂이형'),
            (['똑딱', '바나나'], '똑딱이형'),
            (['자동핀'], '자동핀형'),
        ],
    },
    '넥라인': {
        'keywords': [
            (['라운드', '원형'], '라운드넥'),
            (['v넥', 'v-넥', '브이넥', '브이넥'], 'V넥'),
            (['오프숄더', '오프숄더'], '오프숄더'),
            (['스퀘어', '사각'], '스퀘어넥'),
            (['터틀', '목폴라'], '터틀넥'),
            (['크루넥', 'crew'], '크루넥'),
            (['유넥', 'u넥', 'u-넥'], 'U넥'),
        ],
    },
    '핏': {
        'keywords': [
            (['슬림', '슬림핏'], '슬림핏'),
            (['루즈', '오버사이즈', '빅', 'wide', '와이드'], '루즈핏'),
            (['레귤러', '일자', '스트레이트', '기본'], '레귤러핏'),
            (['크롭', '짧은'], '크롭'),
        ],
    },
    '소매기장': {
        'keywords': [
            (['민소매', '나시', '슬리브리스'], '민소매'),
            (['반팔', '반소매', '5부', '7부'], '반팔'),
            (['긴팔', '긴소매', '장소매'], '긴팔'),
        ],
    },
    '두께감': {
        'keywords': [
            (['시스루', '쉬폰', '얇은', '얇은', '비침'], '얇음'),
            (['두꺼운', '두꺼운', '겨울', '울', '기모'], '두꺼움'),
        ],
        'default': '보통',
    },
}

# 사용대상 상품명 키워드 (상위레벨)
GENDER_MALE = ['남성', '남자', '남성용', '남', '맨', '멘', '보이', '보이즈', '아버지', '아재', '직장인남성', '유니섹스남성']
GENDER_FEMALE = ['여성', '여자', '여성용', '여', '여우', '레이디', '언니', '아내', '걸', '걸즈', '아줌마']


def match_attr_value(attr_name, product_name, options, attribute_values):
    """속성명, 상품명, 옵션으로 속성 값을 결정"""
    rule = ATTR_RULES.get(attr_name)
    if not rule:
        return []

    text = (product_name + ' ' + ' '.join(options)).lower()

    # 사용대상 특별 처리
    if attr_name == '사용대상':
        has_male = any(k in text for k in [m.lower() for m in GENDER_MALE])
        has_female = any(k in text for k in [f.lower() for f in GENDER_FEMALE])
        if has_male and not has_female:
            target = '남성용'
        elif has_female and not has_male:
            target = '여성용'
        else:
            target = rule.get('default', '남녀공용')

        matched = [av for av in attribute_values if av.get('attributeValueText', '') == target]
        return matched[:1]

    matched_values = []
    for keywords, target_text in rule.get('keywords', []):
        if any(kw.lower() in text for kw in keywords):
            if target_text:
                matched = [av for av in attribute_values if av.get('attributeValueText', '') == target_text]
                matched_values.extend(matched)

    if not matched_values and rule.get('default'):
        default = rule['default']
        matched = [av for av in attribute_values if av.get('attributeValueText', '') == default]
        matched_values.extend(matched)

    # 최대 2개 (MULTI_SELECT)
    seen = set()
    result = []
    for av in matched_values:
        seq = av.get('attributeValueSeq')
        if seq not in seen:
            seen.add(seq)
            result.append(av)
        if len(result) >= 2:
            break
    return result


class Command(BaseCommand):
    help = '스타비젼 상품 속성 일괄 적용'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--offset', type=int, default=0)

    def handle(self, *args, **options):
        with open(INPUT) as f:
            d = json.load(f)
        products = d['products']

        offset = options['offset']
        limit = options['limit']
        if offset:
            products = products[offset:]
        if limit:
            products = products[:limit]

        self.stdout.write(f'대상: {len(products)}개')

        acc = SmartStoreAccount.objects.get(login_id='dlrmsgh01234@gmail.com')
        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        # 판매자센터 세션 (속성 정의 조회용)
        self.stdout.write('판매자센터 로그인...')
        driver = create_driver(download_dir='/tmp')
        ok = login_smartstore(driver, acc.login_id, acc.login_pw, self.stdout.write)
        if not ok:
            driver.quit()
            sys.exit(1)
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        driver.quit()

        ss = requests.Session()
        for k, v in cookies.items():
            ss.cookies.set(k, v)
        ss_headers = {'Referer': 'https://sell.smartstore.naver.com/', 'Accept': 'application/json'}

        # 카테고리 속성 캐시 로드
        try:
            with open(CATEGORY_CACHE_FILE) as f:
                cat_cache = json.load(f)
        except:
            cat_cache = {}

        success = []
        failed = []
        skipped = 0

        for i, p in enumerate(products):
            if i > 0 and i % 150 == 0:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

            cno = p['channel_product_no']
            cat = str(p.get('category_id', ''))
            pname = p.get('new_name') or p.get('current_name', '')
            opts = p.get('options', [])

            if not cat:
                skipped += 1
                continue

            # 카테고리 속성 조회 (캐시)
            if cat not in cat_cache:
                try:
                    r = ss.get(
                        f'https://sell.smartstore.naver.com/api/category-attribute/attribute-group?leafCategoryId={cat}',
                        headers=ss_headers, timeout=10
                    )
                    cat_cache[cat] = r.json() if r.ok and r.text else []
                    time.sleep(0.2)
                except:
                    cat_cache[cat] = []

            attr_groups = cat_cache[cat]
            if not attr_groups:
                skipped += 1
                continue

            # 속성 값 결정
            new_attrs = []
            for group in attr_groups:
                attr = group.get('attribute', {})
                attr_name = attr.get('attributeName', '')
                attr_seq = attr.get('id')
                attr_values = attr.get('attributeValues', [])

                matched = match_attr_value(attr_name, pname, opts, attr_values)
                for av in matched:
                    new_attrs.append({
                        'attributeSeq': attr_seq,
                        'attributeValueSeq': av.get('attributeValueSeq'),
                    })

            if not new_attrs:
                skipped += 1
                continue

            if options['dry_run']:
                attr_labels = [f'{g["attribute"]["attributeName"]}={a["attributeValueSeq"]}' for g, a in zip(attr_groups, new_attrs[:3])]
                self.stdout.write(f'  [{i}] {pname[:30]} → {new_attrs}')
                continue

            # GET 현재 상품
            r = None
            for attempt in range(3):
                r = requests.get(
                    f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                    headers={'Authorization': headers['Authorization']}, timeout=20
                )
                if r.status_code == 200:
                    break
                if r.status_code == 429:
                    time.sleep(5)

            if not r or r.status_code != 200:
                failed.append({'cno': cno, 'error': f'GET {r.status_code if r else "no_resp"}'})
                time.sleep(DELAY)
                continue

            data = r.json()
            op = data.get('originProduct', {})
            op['statusType'] = 'SALE'
            da = op.get('detailAttribute', {})
            da['productAttributes'] = new_attrs
            op['detailAttribute'] = da

            # PUT
            pr = None
            for attempt in range(3):
                pr = requests.put(
                    f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                    headers=headers,
                    json={'originProduct': op, 'smartstoreChannelProduct': data.get('smartstoreChannelProduct', {})},
                    timeout=20
                )
                if pr.status_code == 200:
                    break
                if pr.status_code == 429:
                    time.sleep(5)

            if pr and pr.status_code == 200:
                success.append(cno)
            else:
                failed.append({
                    'cno': cno, 'error': pr.status_code if pr else 'no_resp',
                    'msg': pr.text[:100] if pr else '',
                    'name': pname
                })

            if (i + 1) % 50 == 0:
                self.stdout.write(f'  [{i+1}/{len(products)}] 성공={len(success)}, 실패={len(failed)}, 스킵={skipped}')
                with open(CATEGORY_CACHE_FILE, 'w') as f:
                    json.dump(cat_cache, f, ensure_ascii=False)
                with open(OUTPUT_LOG, 'w') as f:
                    json.dump({'success': success, 'failed': failed, 'skipped': skipped}, f, ensure_ascii=False)

            time.sleep(DELAY)

        # 캐시 저장
        with open(CATEGORY_CACHE_FILE, 'w') as f:
            json.dump(cat_cache, f, ensure_ascii=False)
        with open(OUTPUT_LOG, 'w') as f:
            json.dump({'success': success, 'failed': failed, 'skipped': skipped}, f, ensure_ascii=False)

        self.stdout.write(f'\n완료: 성공={len(success)}, 실패={len(failed)}, 스킵={skipped}')
        if failed:
            self.stdout.write('실패 샘플:')
            for f in failed[:3]:
                self.stdout.write(f'  {f}')

"""
주노그노(id=15) 상품명 키워드 추가 + 속성 일괄 적용
- 상품명: 대괄호 제거 + 규격코드 정리 + 카테고리 키워드 추가
- 속성: 카테고리별 attribute-group 조회 → 규칙 매핑 → PUT
"""
import re
import json
import time
import sys
import requests
from django.core.management.base import BaseCommand
from crawlers.browser import create_driver
from crawlers.smartstore_crawler import login_smartstore
from apps.smartstore.models import SmartStoreAccount, SmartStoreProduct
from apps.smartstore.services.naver_api import _get_access_token

ACCOUNT_ID = 15
DELAY = 0.6
CATEGORY_CACHE_FILE = '/tmp/category_attr_cache.json'
LOG_FILE = '/tmp/junogno_apply.log'

# ── 카테고리별 추가 키워드 ──
CATEGORY_KEYWORDS = {
    '50008888': ['사무용품', '문구'],
    '50008068': ['클리어파일', '문서정리', '화일'],
    '50003767': ['파티의상', '코스튬', '이벤트'],
    '50008249': ['문서케이스', '서류보관함'],
    '50007968': ['사무용품', '문구용품'],
    '50019780': ['접착테이프', '다용도테이프'],
    '50007689': ['벽수납', '서류정리', '수납정리'],
    '50003733': ['스티커라벨', '라벨지', '문구'],
    '50003556': ['학용품', '공책', '노트'],
    '50003775': ['파티용품', '생일파티', '파티데코'],
    '50006877': ['서류정리함', '데스크정리', '사무용'],
    '50007548': ['필통', '연필통', '수납'],
    '50003568': ['볼펜', '필기구', '사무용'],
    '50003754': ['제본용품', '사무용'],
    '50003740': ['프린트용지', '사무용'],
    '50003573': ['연필용품', '학용품'],
    '50003803': ['포장용품', '선물포장', '리본'],
    '50003735': ['장부', '가계부'],
    '50008069': ['봉투', '포장용품'],
    '50003567': ['마카펜', '미술용품'],
    '50007608': ['고무줄', '사무용품'],
    '50003578': ['형광펜', '색깔펜', '필기구'],
    '50007849': ['자석', '부자재', '공예용품'],
    '50003591': ['화이트보드', '메모보드', '사무용'],
    '50003597': ['우산', '자동우산'],
    '50003592': ['데스크매트', '책상깔판', '사무용'],
    '50003890': ['미술도구', '아크릴', '스파출라'],
    '50007848': ['커터칼', '사무용', '문구'],
    '50003884': ['미술붓', '수채화붓', '미술용품'],
    '50007909': ['삼각자', '스케일', '제도용품'],
    '50003895': ['색연필', '미술용품', '학용품'],
    '50003598': ['게시물꽂이', '공지사항꽂이', '사무용'],
    '50007728': ['명함홀더', '명함보관함', '사무용'],
    '50003774': ['가랜드', '파티장식', '파티용품'],
    '50003550': ['바인더', '다이어리', '가계부'],
    '50003748': ['코팅기', '사무용'],
    '50003768': ['야광돌', '파티용품', '인테리어'],
    '50007828': ['가위', '사무용', '문구'],
    '50003570': ['사인펜', '색깔펜', '학용품'],
    '50003563': ['볼펜리필심', '필기구'],
    '50008049': ['클립보드', '파일철', '사무용'],
    '50007988': ['서류집게', '사무용품', '문구'],
    '50007908': ['지우개', '볼펜용품'],
    '50003565': ['마카펜', '미술용품'],
    '50003885': ['수채화붓', '미술용품'],
    '50003766': ['가면', '파티용품', '만들기'],
    '50003734': ['라벨지', '라벨스티커'],
    '50003888': ['미술붓', '수채화붓세트'],
    '50008130': ['풍선', '파티용품'],
    '50007708': ['서류집게', '결재판', '사무용'],
    '50003571': ['샤프', '제도용샤프', '필기구'],
    '50007770': ['미니스테이플러', '사무용'],
    '50003553': ['마스킹테이프', '다이어리꾸미기'],
    '50003751': ['커터기', '문서커터', '사무용'],
    '50003788': ['부직포', '미술재료'],
    '50007928': ['수정테이프', '사무용품'],
    '50019739': ['책갈피', '북마크'],
    '50003743': ['계산기', '사무용'],
    '50007868': ['펀칭기', '펀치', '사무용'],
    '50003893': ['아크릴물감', '미술용품'],
    '50003797': ['켄트지', '도화지', '미술용'],
    '50003758': ['코팅기', '가정용코팅기'],
    '50003738': ['코팅지', 'A4코팅지', '사무용'],
    '50003564': ['깃털펜', '캘리그라피', '만년필'],
    '50003763': ['샤프', '제도샤프', '학용품'],
    '50003558': ['메모지', '점착메모', '포스트잇'],
    '50003732': ['레이저전용지', 'A4용지'],
    '50003886': ['유화붓', '아크릴붓', '미술용품'],
    '50003906': ['클레이', '점토', '미술놀이'],
    '50000636': ['칼라보드롱', '미술재료'],
    '50008131': ['편지지', '레터세트'],
    '50003899': ['윈도우마카', '마카펜', '미술용품'],
    '50003889': ['수채화물감', '미술용품'],
    '50003566': ['색깔펜', '컬러펜', '필기구'],
    '50003559': ['수첩', '메모장', '휴대용노트'],
    '50007649': ['케이크토퍼', '파티용품', '생일'],
    '50007750': ['풀', '접착제', '미술용품'],
    '50003574': ['롤링펜', '다색펜', '필기구'],
    '50003572': ['샤프심', '연필심', '필기구'],
    '50003789': ['물통', '붓세척기', '미술용품'],
    '50003560': ['스프링노트', '공책', '학용품'],
    '50003771': ['폭죽', '파티용품'],
    '50003737': ['복사용지', 'A3용지', '프린터용지'],
    '50007769': ['스탬프', '도장', '문구'],
    '50007628': ['찍찍이', '벨크로', '부자재'],
    '50003785': ['미술도구정리함', '수납박스'],
    '50003896': ['채점용펜', '빨간펜', '교사용'],
    '50003736': ['포토용지', '광택용지'],
    '50007969': ['문구세트', '학용품세트', '선물'],
    '50003744': ['저금통', '캐릭터저금통'],
    '50003594': ['북앤드', '책받침대', '사무용'],
    '50003891': ['아크릴물감', '미술용품'],
    '50003757': ['순찰시계', '관리용품'],
    '50003582': ['포카앨범', '포토카드앨범', '미니앨범'],
    '50003551': ['탁상달력', '2026달력', '캘린더'],
    '50003794': ['아크릴판', '투명판', '디스플레이'],
    '50003887': ['미술붓세트', '화필세트'],
    '50008288': ['깃발거치대', '광고깃발'],
    '50003905': ['물레', '도예용품'],
    '50007788': ['스탬프잉크', '도장잉크'],
    '50003761': ['삼각자', '목공자'],
    '50007568': ['붓펜', '캘리그라피'],
    '50003581': ['포토앨범', '사진앨범', '스크랩북'],
    '50003770': ['파티컵', '일회용컵', '파티용품'],
    '50003579': ['고무밴드', '고무줄'],
    '50007668': ['국기함', '태극기'],
    '50003786': ['붓케이스', '붓통', '미술용품'],
    '50008308': ['상장케이스', '상장지'],
    '50003577': ['젤펜', '필기구세트'],
    '50003557': ['폴더', '서류파일'],
    '50008268': ['아크릴명패', '명판', '가격표'],
    '50003742': ['공학용계산기', '전자계산기'],
    '50003897': ['오일파스텔', '미술용품'],
    '50008088': ['바인더내지', '다공바인더'],
    '50003549': ['주문서꽂이', '영수증꽂이'],
    '50003800': ['화선지', '서예지'],
    '50003555': ['가계부', '금전출납부'],
    '50003756': ['제본용품', '제본나사'],
    '50003739': ['색복사지', 'A4색지'],
    '50003755': ['위폐감별기', '지폐감별기'],
    '50003764': ['책상깔판', '데스크매트'],
    '50003563': ['볼펜리필심', '필기구'],
    '50003796': ['캔버스', '미술용'],
    '50003900': ['크레파스', '크레용', '유아미술'],
    '50003787': ['이젤', '미술용이젤'],
    '50003777': ['서예연습지', '붓글씨'],
    '50003552': ['바인더', '다이어리커버'],
    '50003892': ['동양화물감', '한국화물감'],
    '50003791': ['팔토시', '방수토시'],
    '50003901': ['드로잉보드', '광학드로잉'],
    '50003576': ['경면주사', '부적펜'],
    '50003583': ['스크랩앨범', '사진앨범'],
    '50001768': ['운동화', '런닝화', '스니커즈'],
}

# ── 속성 규칙 (apply_product_attributes와 동일) ──
ATTR_RULES = {
    '사용대상': {'default': '남녀공용', 'male_kw': ['남성','남자','남'], 'female_kw': ['여성','여자','여']},
    '포인트': {'default': '무지', 'keywords': [(['리본'],'리본'),(['보석','크리스탈'],'보석'),(['플라워','꽃'],'플라워'),(['캐릭터'],'캐릭터')]},
    '고정형태': {'keywords': [(['집게'],'집게형'),(['클립'],'클립형'),(['꽂이'],'꽂이형'),(['똑딱'],'똑딱이형'),(['자동핀'],'자동핀형')]},
    '종류': {'keywords': [(['슬랙스','정장바지'],'슬랙스'),(['조거','트레이닝'],'조거팬츠'),(['반바지','숏팬츠'],'숏팬츠/3부'),(['청바지','데님'],'청바지'),(['레깅스'],'레깅스'),(['면바지'],'면바지'),(['와이드','배기'],'와이드팬츠')]},
    '신축성': {'keywords': [(['스트레치','스판','밴딩'],'신축성있음')], 'default': '신축성없음'},
    '패턴': {'keywords': [(['체크'],'체크'),(['스트라이프'],'스트라이프'),(['도트','물방울'],'도트'),(['프린트','패턴'],'프린트'),(['무지','단색'],'무지')]},
    '소재': {'keywords': [(['면','코튼'],'면'),(['폴리'],'폴리에스테르'),(['나일론'],'나일론'),(['가죽','레더'],'인조가죽'),(['울'],'울혼방'),(['린넨'],'린넨')]},
    '주요소재': {'keywords': [(['데님','청'],'데님'),(['면','코튼'],'면'),(['폴리'],'폴리에스테르'),(['나일론'],'나일론'),(['가죽','레더'],'인조가죽')]},
    '하의핏': {'keywords': [(['스키니','슬림'],'스키니핏'),(['일자','스트레이트'],'일자핏'),(['루즈','와이드','오버사이즈'],'루즈핏'),(['배기'],'배기핏')]},
    '밑위': {'default': '기본허리선', 'keywords': [(['로우','로우라이즈'],'로우웨이스트'),(['하이','하이웨이스트'],'하이웨이스트')]},
    '핏': {'keywords': [(['슬림'],'슬림핏'),(['루즈','오버사이즈','빅'],'루즈핏'),(['레귤러','일자'],'레귤러핏'),(['크롭'],'크롭')]},
    '소매기장': {'keywords': [(['민소매','나시'],'민소매'),(['반팔','반소매'],'반팔'),(['긴팔','긴소매'],'긴팔')]},
    '넥라인': {'keywords': [(['라운드'],'라운드넥'),(['v넥','브이넥'],'V넥'),(['터틀','목폴라'],'터틀넥'),(['크루넥'],'크루넥')]},
    '두께감': {'default': '보통', 'keywords': [(['시스루','얇은'],'얇음'),(['두꺼운','겨울','기모'],'두꺼움')]},
}


def clean_name(name):
    """상품명 정리: 대괄호 제거, 규격코드 정리"""
    # [브랜드] → 브랜드
    name = re.sub(r'^\[([^\]]+)\]\s*', r'\1 ', name)
    # ( N개 / N세트 ) 앞에 오는 수량 괄호 제거
    # " / 규격코드" 패턴 제거 (숫자+문자만 있는 경우)
    name = re.sub(r'\s*/\s*[\dA-Za-z가-힣\-\.]+\s*$', '', name)
    # 연속 공백 정리
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def add_keywords(name, category_id):
    """카테고리별 검색 키워드 추가"""
    kws = CATEGORY_KEYWORDS.get(str(category_id), [])
    for kw in kws:
        if kw not in name:
            candidate = f'{name} {kw}'
            if len(candidate) <= 100:
                name = candidate
                break
    return name


def match_attr(attr_name, name, attr_values):
    rule = ATTR_RULES.get(attr_name)
    if not rule:
        return []
    text = name.lower()

    if attr_name == '사용대상':
        has_male = any(k in text for k in [m.lower() for m in rule.get('male_kw', [])])
        has_female = any(k in text for k in [f.lower() for f in rule.get('female_kw', [])])
        target = '남성용' if (has_male and not has_female) else '여성용' if (has_female and not has_male) else rule.get('default', '남녀공용')
        return [av for av in attr_values if av.get('attributeValueText') == target][:1]

    matched = []
    for keywords, target_text in rule.get('keywords', []):
        if any(kw.lower() in text for kw in keywords):
            matched += [av for av in attr_values if av.get('attributeValueText') == target_text]

    if not matched and rule.get('default'):
        matched += [av for av in attr_values if av.get('attributeValueText') == rule['default']]

    seen, result = set(), []
    for av in matched:
        seq = av.get('attributeValueSeq')
        if seq not in seen:
            seen.add(seq); result.append(av)
        if len(result) >= 2:
            break
    return result


class Command(BaseCommand):
    help = '주노그노 상품명 키워드 추가 + 속성 일괄 적용'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--offset', type=int, default=0)
        parser.add_argument('--name-only', action='store_true', help='상품명만 수정')
        parser.add_argument('--attr-only', action='store_true', help='속성만 수정')

    def handle(self, *args, **options):
        acc = SmartStoreAccount.objects.get(id=ACCOUNT_ID)
        token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        products = list(SmartStoreProduct.objects.filter(
            account_id=ACCOUNT_ID, status_type='SALE'
        ).order_by('id').values('channel_product_no', 'name', 'category_id'))

        offset = options['offset']
        limit = options['limit']
        if offset:
            products = products[offset:]
        if limit:
            products = products[:limit]

        self.stdout.write(f'대상: {len(products)}개')

        # 판매자센터 쿠키 (속성 조회용)
        ss = None
        if not options.get('name_only'):
            self.stdout.write('판매자센터 로그인...')
            driver = create_driver(download_dir='/tmp')
            ok = login_smartstore(driver, acc.login_id, acc.login_pw, self.stdout.write)
            if not ok:
                driver.quit(); sys.exit(1)
            cookies = {c['name']: c['value'] for c in driver.get_cookies()}
            driver.quit()
            ss = requests.Session()
            for k, v in cookies.items():
                ss.cookies.set(k, v)

        try:
            with open(CATEGORY_CACHE_FILE) as f:
                cat_cache = json.load(f)
        except:
            cat_cache = {}

        ok_cnt = fail_cnt = skip_cnt = name_changed = attr_changed = 0
        logs = []

        for i, p in enumerate(products):
            if i > 0 and i % 150 == 0:
                token = _get_access_token(acc.commerce_api_key, acc.commerce_secret_key)
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

            cno = p['channel_product_no']
            cur_name = p['name'] or ''
            cat = str(p.get('category_id') or '')

            # 상품명 최적화
            new_name = clean_name(cur_name)
            if cat:
                new_name = add_keywords(new_name, cat)
            new_name = new_name[:100]
            name_diff = new_name != cur_name

            # 속성 결정
            new_attrs = []
            if not options.get('name_only') and cat and ss:
                if cat not in cat_cache:
                    try:
                        r = ss.get(
                            f'https://sell.smartstore.naver.com/api/category-attribute/attribute-group?leafCategoryId={cat}',
                            headers={'Referer': 'https://sell.smartstore.naver.com/', 'Accept': 'application/json'},
                            timeout=10
                        )
                        cat_cache[cat] = r.json() if r.ok and r.text else []
                        time.sleep(0.2)
                    except:
                        cat_cache[cat] = []

                for group in cat_cache.get(cat, []):
                    attr = group.get('attribute', {})
                    matched = match_attr(attr.get('attributeName', ''), new_name, attr.get('attributeValues', []))
                    for av in matched:
                        new_attrs.append({'attributeSeq': attr.get('id'), 'attributeValueSeq': av.get('attributeValueSeq')})

            if not name_diff and not new_attrs:
                skip_cnt += 1
                continue

            if options['dry_run']:
                self.stdout.write(f'  [{i}] {cur_name[:40]}')
                if name_diff:
                    self.stdout.write(f'       → {new_name[:40]}')
                if new_attrs:
                    self.stdout.write(f'       attrs={new_attrs}')
                continue

            # GET
            r = None
            for _ in range(3):
                r = requests.get(
                    f'https://api.commerce.naver.com/external/v2/products/channel-products/{cno}',
                    headers={'Authorization': headers['Authorization']}, timeout=20
                )
                if r.status_code == 200:
                    break
                if r.status_code == 429:
                    time.sleep(5)

            if not r or r.status_code != 200:
                fail_cnt += 1
                logs.append({'cno': cno, 'error': f'GET {r.status_code if r else "?"}'})
                time.sleep(DELAY)
                continue

            data = r.json()
            op = data.get('originProduct', {})
            op['statusType'] = 'SALE'

            if name_diff:
                op['name'] = new_name
                name_changed += 1

            if new_attrs and not options.get('name_only'):
                da = op.get('detailAttribute', {})
                da['productAttributes'] = new_attrs
                op['detailAttribute'] = da
                attr_changed += 1

            # PUT
            pr = None
            for _ in range(3):
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
                ok_cnt += 1
            else:
                fail_cnt += 1
                logs.append({'cno': cno, 'error': pr.status_code if pr else '?', 'msg': (pr.text[:100] if pr else ''), 'name': cur_name})

            if (i + 1) % 100 == 0:
                self.stdout.write(f'  [{i+1}/{len(products)}] 성공={ok_cnt} 실패={fail_cnt} 스킵={skip_cnt} (명={name_changed} 속성={attr_changed})')
                with open(CATEGORY_CACHE_FILE, 'w') as f:
                    json.dump(cat_cache, f, ensure_ascii=False)

            time.sleep(DELAY)

        with open(CATEGORY_CACHE_FILE, 'w') as f:
            json.dump(cat_cache, f, ensure_ascii=False)
        with open(LOG_FILE, 'w') as f:
            json.dump({'ok': ok_cnt, 'fail': fail_cnt, 'skip': skip_cnt, 'name_changed': name_changed, 'attr_changed': attr_changed, 'errors': logs}, f, ensure_ascii=False)

        self.stdout.write(f'\n완료: 성공={ok_cnt} 실패={fail_cnt} 스킵={skip_cnt}')
        self.stdout.write(f'  상품명 변경={name_changed}개 / 속성 적용={attr_changed}개')
        if logs[:3]:
            self.stdout.write('실패 샘플:')
            for l in logs[:3]:
                self.stdout.write(f'  {l}')

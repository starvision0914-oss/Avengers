"""
스피드고 핵심 서비스 — 도매매 수집 + 네이버 카테고리 매칭.

MVP 범위
1) 도매매 마이박스 → SpeedgoItem 누적 (Selenium, 추후 구현 — 본 파일에 골격만)
2) 각 SpeedgoItem에 대해 네이버 검색 → 1위 상품 카테고리 추출 → 저장

상품명은 이번 MVP 에서는 가공하지 않고 원본 그대로 사용.
"""
import re
import time
import random
import logging
from typing import Optional
from urllib.parse import quote

import requests
from django.utils import timezone

from .models import SpeedgoItem, SpeedgoLog

logger = logging.getLogger(__name__)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


# ─────────────────────────────────────────────────────────────────────────────
# 1) 네이버 카테고리 매칭
# ─────────────────────────────────────────────────────────────────────────────

NAVER_SHOPPING_SEARCH = 'https://search.shopping.naver.com/search/all?query={}'
NAVER_INTEGRATED_SEARCH = 'https://search.naver.com/search.naver?where=nexearch&query={}'


def _make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.5',
    })
    return s


def _extract_top_category_from_naver(html: str) -> Optional[dict]:
    """네이버 검색결과 HTML에서 1위 쇼핑 카테고리 경로 추출.

    여러 패턴 시도:
    - <div class="category"> 안 텍스트
    - data 속성 'data-shp-category', 'data-category'
    - JSON 임베드된 카테고리 정보
    """
    # 패턴 1: shopping_module 안의 카테고리 텍스트
    m = re.search(
        r'<div class="shopping_module[^"]*"[\s\S]*?<a[^>]*class="[^"]*category[^"]*"[^>]*>([^<]+)</a>',
        html,
    )
    if m:
        path = re.sub(r'\s+', ' ', m.group(1)).strip()
        return {'path': path, 'source': 'shopping_module'}

    # 패턴 2: 단순한 '>' 구분 카테고리 라인
    m = re.search(r'>(?:[가-힣A-Za-z0-9]+\s*&gt;\s*){2,}(?:[가-힣A-Za-z0-9]+)<', html)
    if m:
        path = m.group(0).strip('<>').replace('&gt;', '>').strip()
        return {'path': re.sub(r'\s+', ' ', path), 'source': 'breadcrumb'}

    # 패턴 3: cat_main / cat_sub 클래스
    cats = re.findall(r'<(?:span|a)[^>]*class="[^"]*(?:cat_main|cat_sub|cat_path)[^"]*"[^>]*>([^<]+)<', html)
    if cats:
        path = ' > '.join(s.strip() for s in cats[:5] if s.strip())
        if path.count('>') >= 1:
            return {'path': path, 'source': 'cat_classes'}

    return None


def fetch_naver_category(query: str, session=None, driver=None) -> dict:
    """단일 상품명으로 네이버 검색 → 1위 쇼핑 결과 카테고리 추출.

    네이버 쇼핑은 봇 차단(HTTP 418)이라 Selenium 으로 우회.
    returns: {'path': str, 'top_url': str, 'source': str} | {'error': str}
    """
    return _fetch_via_selenium(query, driver=driver)


def _fetch_via_selenium(query: str, driver=None) -> dict:
    """Selenium 기반 카테고리 추출 — 봇 차단 우회."""
    import sys
    sys.path.insert(0, '/home/rejoice888/Avengers/backend')
    from crawlers.browser import create_driver, stop_display
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    own_driver = driver is None
    d = driver or create_driver()
    try:
        url = f'https://search.shopping.naver.com/search/all?query={quote(query)}'
        d.get(url)
        # 페이지 로딩 대기 — basicList 또는 product 카드 등장까지
        try:
            WebDriverWait(d, 8).until(lambda x: 'shopping.naver.com' in x.current_url)
        except Exception:
            pass
        time.sleep(2)

        # 1) 1위 상품 카드 안의 카테고리 경로 추출
        # 네이버 쇼핑 DOM 변화에 대비해 여러 selector 시도
        category_selectors = [
            'a.product_category__SkN0v',                 # 새 디자인
            'a[class*="product_category"]',
            'div.basicList_depth__2QIie',                # 기존 디자인
            'div[class*="basicList_depth"]',
            'div.product_depth__JSs5G',
            'a.depth_link__C2dD7',
            'a[class*="depth_link"]',
        ]
        path = None
        top_url = ''
        for sel in category_selectors:
            try:
                els = d.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    txt = els[0].text.strip()
                    if txt and ('>' in txt or len(txt) > 4):
                        path = re.sub(r'\s+', ' ', txt).replace(' > ', ' > ')
                        break
            except Exception:
                continue

        # 2) 1위 상품 URL 추출 (별도 selector)
        try:
            link_els = d.find_elements(By.CSS_SELECTOR,
                'a[class*="product_link"], a[class*="basicList_link"], a.thumb_link__Csopf')
            if link_els:
                top_url = link_els[0].get_attribute('href') or ''
        except Exception:
            pass

        # 3) 카테고리 못 찾았으면 1위 상품 상세 페이지 진입 시도
        if not path and top_url:
            try:
                d.get(top_url)
                time.sleep(2)
                # 상세 페이지에 카테고리 경로 (breadcrumb)
                for sel in [
                    'div[class*="category_list"]',
                    'div[class*="categoryPath"]',
                    'ul[class*="breadcrumb"]',
                    '#_categoryDisp',
                ]:
                    try:
                        e = d.find_element(By.CSS_SELECTOR, sel)
                        txt = e.text.strip()
                        if txt:
                            path = re.sub(r'\s+', ' ', txt)
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if path:
            # '>' 또는 '/' 정규화
            path = path.replace(' >> ', ' > ').replace(' / ', ' > ').strip()
            return {'path': path, 'top_url': top_url, 'source': 'selenium'}
        return {'error': '카테고리 영역을 찾지 못함 (DOM 변경 가능)',
                'top_url': top_url}
    except Exception as e:
        return {'error': f'Selenium 오류: {type(e).__name__}: {e}'}
    finally:
        if own_driver:
            try:
                d.quit()
            except Exception:
                pass
            stop_display()


def match_category_for_item(item: SpeedgoItem, driver=None) -> dict:
    """단일 SpeedgoItem 카테고리 매칭 + DB 저장 (driver 공유 가능)."""
    query = item.display_name()
    if not query:
        return {'error': '상품명 없음', 'item_id': item.id}

    r = fetch_naver_category(query, driver=driver)
    if 'error' in r:
        SpeedgoLog.objects.create(
            item=item, stage='match_category', level='warn',
            message=r['error'],
        )
        return {**r, 'item_id': item.id}

    item.naver_category_path = r['path']
    item.naver_top_product_url = r.get('top_url', '')
    item.naver_matched_at = timezone.now()
    if item.status == '새로담김':
        item.status = '카테고리매칭'
    item.save(update_fields=['naver_category_path', 'naver_top_product_url',
                              'naver_matched_at', 'status', 'updated_at'])
    SpeedgoLog.objects.create(
        item=item, stage='match_category', level='success',
        message=f'카테고리: {r["path"]}',
    )
    return {
        'item_id': item.id, 'query': query,
        'path': r['path'], 'top_url': r.get('top_url', ''),
        'source': r.get('source', ''),
    }


def match_categories_batch(item_ids=None, only_unmatched=True,
                            sleep_range=(1.0, 2.5), log_fn=None) -> dict:
    """여러 SpeedgoItem 일괄 카테고리 매칭 (driver 공유로 빠름)."""
    import sys
    sys.path.insert(0, '/home/rejoice888/Avengers/backend')
    from crawlers.browser import create_driver, stop_display

    qs = SpeedgoItem.objects.all()
    if item_ids:
        qs = qs.filter(id__in=item_ids)
    if only_unmatched:
        qs = qs.filter(naver_category_path='')

    items = list(qs)
    if not items:
        return {'matched': 0, 'failed': 0, 'total': 0, 'results': []}

    matched = 0
    failed = 0
    results = []
    driver = None
    try:
        driver = create_driver()
        for i, it in enumerate(items, 1):
            if log_fn:
                log_fn(f'[{i}/{len(items)}] #{it.id} "{it.display_name()[:30]}..."')
            r = match_category_for_item(it, driver=driver)
            if 'error' in r:
                failed += 1
                if log_fn:
                    log_fn(f'  실패: {r["error"]}')
            else:
                matched += 1
                if log_fn:
                    log_fn(f'  ✓ {r["path"]}')
            results.append(r)
            if i < len(items):
                time.sleep(random.uniform(*sleep_range))
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        stop_display()

    return {
        'matched': matched, 'failed': failed,
        'total': len(items), 'results': results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2) 도매매 마이박스 수집 (Selenium 골격 — 사용자 계정 필요)
# ─────────────────────────────────────────────────────────────────────────────

DOMEMEA_LOGIN_URL = 'https://domeggook.com/main/login.php'
DOMEMEA_MYBOX_URL = 'https://domeggook.com/ssl/member/myItem/myBox.php'


def collect_from_domemea(login_id: str, password: str, log_fn=None) -> dict:
    """도매매 로그인 → 마이박스 페이지 → 상품 수집.

    NOTE: 도매매 실제 페이지 구조에 따라 selector 조정 필요.
    본 골격은 일반적 흐름이며 사용자 계정으로 1회 시범 후 selector 확정 권장.
    """
    import sys
    sys.path.insert(0, '/home/rejoice888/Avengers/backend')
    from crawlers.browser import create_driver, stop_display, human_sleep
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    def L(msg):
        if log_fn:
            log_fn(msg)
        logger.info('[domemea] %s', msg)

    saved = 0
    skipped = 0
    failed = 0
    d = create_driver()
    try:
        # 1) 로그인
        L('로그인 페이지 진입')
        d.get(DOMEMEA_LOGIN_URL)
        time.sleep(2)
        try:
            d.find_element(By.NAME, 'mb_id').send_keys(login_id)
            d.find_element(By.NAME, 'mb_password').send_keys(password)
            human_sleep(0.5, 1.0)
            d.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]').click()
            time.sleep(3)
        except Exception as e:
            return {'error': f'로그인 실패: {e}', 'saved': 0}

        # 2) 마이박스 진입
        L('마이박스 페이지 진입')
        d.get(DOMEMEA_MYBOX_URL)
        time.sleep(3)

        # 3) 상품 목록 추출 (페이지네이션)
        # 실제 도매매 마이박스 DOM 에 맞춰 selector 조정 필요
        page = 1
        while True:
            L(f'페이지 {page} 수집 중')
            try:
                rows = d.find_elements(By.CSS_SELECTOR, 'tr.item, .product-item, .myItem')
            except Exception:
                rows = []
            if not rows:
                L('상품 행을 찾을 수 없음 — selector 조정 필요')
                break

            for row in rows:
                try:
                    # 상품번호 추출
                    no_el = row.find_element(By.CSS_SELECTOR, '[data-no], .item-no, .prdNo')
                    domemea_no = (no_el.get_attribute('data-no')
                                  or no_el.text.strip())
                    name_el = row.find_element(By.CSS_SELECTOR, '.item-name, .prdName, a[href*="prd"]')
                    name = name_el.text.strip()
                    price_el = row.find_element(By.CSS_SELECTOR, '.price, .prdPrice')
                    price = int(re.sub(r'[^\d]', '', price_el.text or '0') or 0)
                    img_el = row.find_element(By.TAG_NAME, 'img')
                    img = img_el.get_attribute('src') or ''

                    obj, created = SpeedgoItem.objects.update_or_create(
                        domemea_no=domemea_no,
                        defaults={
                            'original_name': name,
                            'wholesale_price': price,
                            'main_image_url': img,
                        },
                    )
                    if created:
                        saved += 1
                        SpeedgoLog.objects.create(
                            item=obj, stage='collect', level='success',
                            message=f'신규 수집: {name}',
                        )
                    else:
                        skipped += 1
                except Exception as e:
                    failed += 1
                    L(f'  행 파싱 실패: {e}')

            # 다음 페이지
            try:
                next_btn = d.find_element(
                    By.XPATH,
                    f'//a[normalize-space(text())="{page+1}"] | //a[@title="다음"]',
                )
                d.execute_script('arguments[0].click();', next_btn)
                time.sleep(random.uniform(2, 3.5))
                page += 1
            except Exception:
                break

        L(f'완료 — 신규 {saved}건, 중복 {skipped}건, 실패 {failed}건')
        return {'saved': saved, 'skipped': skipped, 'failed': failed, 'pages': page}
    finally:
        try:
            d.quit()
        except Exception:
            pass
        stop_display()


# ─────────────────────────────────────────────────────────────────────────────
# 3) 헬퍼 — 통계/리스트
# ─────────────────────────────────────────────────────────────────────────────

def get_stats():
    qs = SpeedgoItem.objects.all()
    total = qs.count()
    by_status = dict(
        (s, qs.filter(status=s).count()) for s, _ in
        __import__('apps.speedgo.models', fromlist=['STATUS_CHOICES']).STATUS_CHOICES
    )
    matched = qs.exclude(naver_category_path='').count()
    return {
        'total': total,
        'matched_categories': matched,
        'unmatched_categories': total - matched,
        'by_status': by_status,
    }


def list_items(page=1, per_page=50, status=None, search=None,
               only_unmatched=False):
    qs = SpeedgoItem.objects.all()
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(original_name__icontains=search)
    if only_unmatched:
        qs = qs.filter(naver_category_path='')

    total = qs.count()
    offset = (page - 1) * per_page
    items = qs[offset:offset + per_page]
    return {
        'items': [_serialize(it) for it in items],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total else 0,
    }


def _serialize(it: SpeedgoItem):
    return {
        'id': it.id,
        'domemea_no': it.domemea_no,
        'original_name': it.original_name,
        'processed_name': it.processed_name,
        'display_name': it.display_name(),
        'wholesale_price': it.wholesale_price,
        'shipping_fee': it.shipping_fee,
        'supplier': it.supplier,
        'main_image_url': it.main_image_url,
        'naver_category_path': it.naver_category_path,
        'naver_top_product_url': it.naver_top_product_url,
        'naver_matched_at': it.naver_matched_at.isoformat() if it.naver_matched_at else None,
        'status': it.status,
        'collected_at': it.collected_at.isoformat(),
        'updated_at': it.updated_at.isoformat(),
    }

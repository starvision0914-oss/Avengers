"""
11번가 셀러오피스 '상품' 크롤러 (Selenium fallback).

용도
- 셀러 OpenAPI 키가 없는 계정에서 '나의 상품'을 셀러오피스 화면에서 직접 수집.
- 결과는 OpenAPI 동기화와 동일한 ElevenMyProduct 테이블로 UPSERT.

차단 회피 원칙 (eleven_crawler.py 와 동일 전략을 그대로 차용)
- Xvfb + non-headless Chrome + stealth JS (browser.create_driver)
- 쿠키 재사용 (eleven_crawler._try_cookie_login / _save_cookies, TTL 4h)
- 계정마다 driver 재시작 (chrome 누수 + 핑거프린트 갱신)
- 계정 간 30~90초 랜덤 지연 + 페이지 간 2~5초 랜덤 지연
- 차단 신호 누적 시 circuit breaker → 글로벌 락 (eleven_block_guard)
- 최근 N시간 내 성공한 계정은 스킵 (신선도)
- 사람처럼: 스크롤, 잠깐 멈춤, viewport 무작위 (browser._VIEWPORT_CHOICES)

수집 전략 (안정성 순)
1) XLS 다운로드 — 엑셀 버튼이 있으면 우선 사용 (cost crawler 동일 패턴)
2) DOM 스크래핑 — 페이지네이션 따라가며 표를 직접 파싱

상품 페이지 URL 후보
- 11번가는 메뉴 view ID 가 자주 바뀌므로 ENV 로 override 가능.
- 기본 후보 리스트를 순회하며 iframe 내 상품 테이블이 보이는 첫 URL을 사용.
"""
import os
import re
import random
import time
import zipfile
import logging
from pathlib import Path
from datetime import timedelta

from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .browser import create_driver, stop_display, human_sleep, _kill_stale_chrome
from .utils import parse_int, wait_for_download
from . import eleven_crawler as _ec  # 로그인 인프라 재사용

logger = logging.getLogger('crawler')

DOWNLOAD_BASE = Path('/tmp/avengers_11st_product_downloads')

# 11번가 셀러오피스 '상품 조회/수정' 페이지 후보.
# 메뉴 view ID 가 변경될 수 있어 ENV 로 우선 override.
PRODUCT_URL_CANDIDATES = [
    os.environ.get('ELEVEN_PRODUCT_VIEW_URL'),
    'https://soffice.11st.co.kr/view/12200',
    'https://soffice.11st.co.kr/view/1101',
    'https://soffice.11st.co.kr/view/2401',
]
PRODUCT_URL_CANDIDATES = [u for u in PRODUCT_URL_CANDIDATES if u]

# 페이지 당 가능한 한 큰 사이즈로 (조회 횟수 ↓ = 봇 행동 ↓)
PAGE_SIZE_PREFERS = ['200', '100', '50']

EXCEL_XPATHS = [
    '//a[contains(@class,"excel")]',
    '//button[contains(@class,"excel")]',
    '//a[contains(normalize-space(text()),"엑셀")]',
    '//button[contains(normalize-space(text()),"엑셀")]',
    '//a[contains(normalize-space(text()),"Excel")]',
    '//*[@onclick and contains(@onclick,"excel")]',
    '//*[@onclick and contains(@onclick,"Excel")]',
]

SEARCH_BUTTON_XPATHS = [
    '//button[contains(normalize-space(text()),"검색")]',
    '//a[contains(normalize-space(text()),"검색")]',
    '//*[@id="frmSearch"]//button[@type="submit"]',
    '//button[@type="submit" and contains(@class,"search")]',
]

# 상품 테이블 후보 — 헤더 라벨 기반으로 탐지
PRODUCT_TABLE_HEADERS = ('상품번호', '상품명', '판매가', '재고')

# 페이싱 (광고비 크롤러와 동일 톤 — 보수적)
# 등록상품 크롤 제외 계정 (빈 계정 — 등록상품 0개라 11번가 대량엑셀이 생성 안 됨)
PRODUCT_EXCLUDE = {'tmxkzhfldk8'}  # 스타코3

INTER_ACCOUNT_SLEEP = (30.0, 90.0)
PAGE_NAV_SLEEP = (2.0, 5.0)
CIRCUIT_BREAKER_THRESHOLD = 5
SKIP_RECENT_HOURS = 12  # 상품은 변동이 광고비보다 느림 → 12시간 신선도
MAX_CONNECT_ATTEMPTS = 3  # 계정당 접속 최대 3회 시도, 3회 실패 시 중지→다음 계정


# ─────────────────────────────────────────────────────────────────────────────
# 사람처럼 보이는 동작
# ─────────────────────────────────────────────────────────────────────────────

def _human_pause(lo=0.4, hi=1.2):
    time.sleep(random.uniform(lo, hi))


def _human_scroll(driver):
    """페이지 내 자연스러운 스크롤 — 사람 패턴."""
    try:
        h = driver.execute_script('return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);')
        if not h or h < 600:
            return
        # 위→아래로 2~4 stop, 각 stop 사이 짧은 휴지
        stops = random.randint(2, 4)
        for i in range(1, stops + 1):
            y = int(h * (i / stops) * random.uniform(0.5, 0.9))
            driver.execute_script(f'window.scrollTo({{top: {y}, behavior: "smooth"}});')
            _human_pause(0.3, 0.9)
        # 마지막에 살짝 위로
        driver.execute_script('window.scrollTo({top: 0, behavior: "smooth"});')
        _human_pause(0.3, 0.7)
    except Exception:
        pass


def _human_move_idle(driver):
    """포인터를 임의 좌표로 살짝 움직이는 시그널."""
    try:
        ActionChains(driver).move_by_offset(random.randint(20, 200), random.randint(20, 200)).perform()
        _human_pause(0.2, 0.6)
        ActionChains(driver).move_by_offset(-random.randint(10, 100), -random.randint(10, 100)).perform()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 페이지 진입 + iframe switch
# ─────────────────────────────────────────────────────────────────────────────

def _switch_to_first_iframe(driver):
    """soffice.11st.co.kr 의 본문은 거의 모두 iframe 안. 첫 iframe 진입."""
    try:
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for fr in iframes:
            try:
                driver.switch_to.frame(fr)
                return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _looks_like_product_page(driver):
    """현재 (iframe 진입 후) 페이지가 상품 목록인지 휴리스틱."""
    try:
        src = driver.page_source
        hits = sum(1 for h in PRODUCT_TABLE_HEADERS if h in src)
        return hits >= 2
    except Exception:
        return False


def _open_product_page(driver, login_id, log):
    """후보 URL 들을 순회하며 상품 목록 페이지 진입. 성공 시 (url) 반환."""
    for url in PRODUCT_URL_CANDIDATES:
        try:
            log(f'상품 페이지 진입 시도: {url}')
            driver.get(url)
            time.sleep(random.uniform(2.0, 4.0))
            driver.switch_to.default_content()
            _switch_to_first_iframe(driver)
            _human_pause(0.5, 1.2)
            if _looks_like_product_page(driver):
                log(f'상품 페이지 OK: {url}')
                return url
            driver.switch_to.default_content()
        except Exception as e:
            log(f'페이지 진입 실패 ({url}): {e}')
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 수집 — XLS 우선, DOM 폴백
# ─────────────────────────────────────────────────────────────────────────────

def _try_change_page_size(driver):
    """페이지당 행 수를 가장 큰 값으로 변경 (보일 때만)."""
    try:
        selects = driver.find_elements(By.TAG_NAME, 'select')
        for sel in selects:
            try:
                options_text = [o.text.strip() for o in sel.find_elements(By.TAG_NAME, 'option')]
            except Exception:
                continue
            # '50/100/200' 류 선택지가 있으면 페이지 사이즈로 간주
            looks_paging = any(t in options_text for t in ('50', '100', '200'))
            if not looks_paging:
                continue
            for prefer in PAGE_SIZE_PREFERS:
                for opt in sel.find_elements(By.TAG_NAME, 'option'):
                    if opt.text.strip() == prefer:
                        try:
                            opt.click()
                            _human_pause(0.5, 1.0)
                            return True
                        except Exception:
                            pass
            break
    except Exception:
        pass
    return False


def _click_search(driver):
    for xp in SEARCH_BUTTON_XPATHS:
        try:
            btn = driver.find_element(By.XPATH, xp)
            driver.execute_script("arguments[0].click();", btn)
            return True
        except Exception:
            continue
    return False


def _try_excel_download(driver, download_dir, log):
    """엑셀 다운로드 시도. 성공 시 파일 경로 반환."""
    download_dir = Path(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    # 이전 파일 청소
    for f in download_dir.glob('*'):
        try:
            f.unlink()
        except Exception:
            pass

    try:
        driver.execute_cdp_cmd('Page.setDownloadBehavior', {
            'behavior': 'allow', 'downloadPath': str(download_dir),
        })
    except Exception:
        pass

    for xp in EXCEL_XPATHS:
        try:
            btn = driver.find_element(By.XPATH, xp)
            driver.execute_script("arguments[0].click();", btn)
            log(f'엑셀 버튼 클릭: {xp}')
            try:
                # 다운로드 확인 alert 처리
                a = driver.switch_to.alert
                a.accept()
            except Exception:
                pass
            try:
                fp = wait_for_download(str(download_dir), timeout=90)
                log(f'엑셀 다운로드 완료: {fp.name}')
                return fp
            except Exception as e:
                log(f'엑셀 대기 실패: {e}')
                return None
        except Exception:
            continue
    return None


def _parse_excel(filepath):
    """엑셀 파일 → product dict 리스트."""
    filepath = str(filepath)
    rows = []
    try:
        if filepath.endswith('.xls'):
            import xlrd
            wk = xlrd.open_workbook(filepath)
            ws = wk.sheet_by_index(0)
            rows = [ws.row_values(i) for i in range(ws.nrows)]
        else:
            import openpyxl
            wb = openpyxl.load_workbook(filepath, data_only=True)
            rows = list(wb.active.iter_rows(values_only=True))
    except Exception as e:
        logger.error('상품 엑셀 읽기 실패: %s', e)
        return []

    # 헤더 행 탐색
    header_idx = None
    for i, row in enumerate(rows[:30]):
        row_str = ' '.join(str(c or '') for c in row)
        if '상품번호' in row_str and '상품명' in row_str:
            header_idx = i
            break
    if header_idx is None:
        return []

    headers = [str(c or '').strip() for c in rows[header_idx]]
    col = {}
    for i, h in enumerate(headers):
        if '상품번호' in h:
            col['product_no'] = i
        elif '상품명' in h:
            col['product_name'] = i
        elif '판매가' in h or '판매단가' in h:
            col['sale_price'] = i
        elif '재고' in h:
            col['stock'] = i
        elif '상태' in h or '판매상태' in h:
            col['status'] = i
        elif '판매자상품코드' in h or '셀러상품코드' in h:
            col['seller_code'] = i
        elif '카테고리' in h:
            col['category'] = i

    products = []
    for row in rows[header_idx + 1:]:
        if not row or row[col.get('product_no', 0)] in (None, ''):
            continue
        try:
            pno = parse_int(row[col.get('product_no', 0)])
            if not pno:
                continue
            products.append({
                'product_no': pno,
                'product_name': str(row[col.get('product_name', 1)] or '')[:500],
                'sale_price': parse_int(row[col.get('sale_price', 2)] if 'sale_price' in col else 0),
                'stock_quantity': parse_int(row[col.get('stock', 3)] if 'stock' in col else 0),
                'status_type': str(row[col.get('status', 0)] or '')[:20] if 'status' in col else '',
                'seller_product_code': str(row[col.get('seller_code', 0)] or '')[:100] if 'seller_code' in col else '',
                'category_id': str(row[col.get('category', 0)] or '')[:50] if 'category' in col else '',
                'product_image_url': '',
            })
        except Exception as e:
            logger.warning('상품 행 파싱 오류: %s', e)
            continue
    return products


def _scrape_dom_page(driver):
    """현재 iframe 안의 상품 테이블 1페이지 파싱."""
    products = []
    try:
        tables = driver.find_elements(By.TAG_NAME, 'table')
    except Exception:
        return products

    target = None
    for t in tables:
        try:
            text = t.text
            if '상품번호' in text and '상품명' in text:
                target = t
                break
        except Exception:
            continue
    if not target:
        return products

    # 헤더 인덱스 추출
    try:
        ths = target.find_elements(By.XPATH, './/thead//th') or target.find_elements(By.XPATH, './/tr[1]/th')
        col_map = {}
        for i, th in enumerate(ths):
            label = (th.text or '').strip()
            if '상품번호' in label:
                col_map['product_no'] = i
            elif '상품명' in label:
                col_map['product_name'] = i
            elif '판매가' in label or '판매단가' in label:
                col_map['sale_price'] = i
            elif '재고' in label:
                col_map['stock'] = i
            elif '판매상태' in label or '상태' in label:
                col_map['status'] = i
            elif '판매자상품코드' in label or '셀러상품코드' in label:
                col_map['seller_code'] = i
        rows = target.find_elements(By.XPATH, './/tbody/tr')
        for r in rows:
            tds = r.find_elements(By.TAG_NAME, 'td')
            if not tds:
                continue
            try:
                pno = parse_int(tds[col_map.get('product_no', 0)].text)
                if not pno:
                    continue
                img = ''
                try:
                    img_el = r.find_element(By.TAG_NAME, 'img')
                    img = img_el.get_attribute('src') or ''
                except Exception:
                    pass
                products.append({
                    'product_no': pno,
                    'product_name': (tds[col_map.get('product_name', 1)].text or '')[:500],
                    'sale_price': parse_int(tds[col_map.get('sale_price', 2)].text) if 'sale_price' in col_map else 0,
                    'stock_quantity': parse_int(tds[col_map.get('stock', 3)].text) if 'stock' in col_map else 0,
                    'status_type': (tds[col_map.get('status', 0)].text or '')[:20] if 'status' in col_map else '',
                    'seller_product_code': (tds[col_map.get('seller_code', 0)].text or '')[:100] if 'seller_code' in col_map else '',
                    'category_id': '',
                    'product_image_url': img,
                })
            except Exception:
                continue
    except Exception as e:
        logger.warning('DOM 페이지 파싱 오류: %s', e)
    return products


def _scrape_via_dom(driver, log, max_pages=50):
    """페이지네이션 따라가며 DOM 스크래핑. 다음 페이지가 없거나 max_pages 도달 시 종료."""
    seen = {}
    for page in range(1, max_pages + 1):
        _human_scroll(driver)
        rows = _scrape_dom_page(driver)
        new_in_page = 0
        for p in rows:
            if p['product_no'] in seen:
                continue
            seen[p['product_no']] = p
            new_in_page += 1
        log(f'page {page}: +{new_in_page} (누적 {len(seen)})')
        if new_in_page == 0:
            break

        # 다음 페이지 클릭
        clicked = False
        for xp in (
            '//a[contains(@class,"next") and not(contains(@class,"disabled"))]',
            '//button[contains(@class,"next") and not(@disabled)]',
            f'//a[normalize-space(text())="{page + 1}"]',
            '//a[@title="다음"]',
            '//a[contains(@onclick,"page") and contains(@onclick,"next")]',
        ):
            try:
                el = driver.find_element(By.XPATH, xp)
                driver.execute_script("arguments[0].click();", el)
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            break
        time.sleep(random.uniform(*PAGE_NAV_SLEEP))
        _human_move_idle(driver)
    return list(seen.values())


# ─────────────────────────────────────────────────────────────────────────────
# DB UPSERT
# ─────────────────────────────────────────────────────────────────────────────

def _upsert_products(account, products):
    """bulk_create + ON DUPLICATE KEY UPDATE (MySQL). 1만건도 수초."""
    from apps.cpc.models import ElevenMyProduct
    now = timezone.now()
    # 같은 파일 내 product_no 중복 제거 (마지막 값 우선)
    uniq = {}
    for p in products:
        if p.get('product_no'):
            uniq[p['product_no']] = p
    objs = [ElevenMyProduct(
        account=account, product_no=pno,
        product_name=(p.get('product_name') or '')[:500],
        sale_price=p.get('sale_price') or 0,
        stock_quantity=p.get('stock_quantity') or 0,
        status_type=(p.get('status_type') or '')[:20],
        seller_product_code=(p.get('seller_product_code') or '')[:100],
        category_id=(p.get('category_id') or '')[:50],
        product_image_url=p.get('product_image_url') or '',
        synced_at=now,
    ) for pno, p in uniq.items()]
    if not objs:
        return 0
    ElevenMyProduct.objects.bulk_create(
        objs, update_conflicts=True,
        update_fields=['product_name', 'sale_price', 'stock_quantity', 'status_type',
                       'seller_product_code', 'category_id', 'product_image_url', 'synced_at'],
        batch_size=1000)
    return len(objs)


# ─────────────────────────────────────────────────────────────────────────────
# 메인 — 계정별 1회 실행 / 전체 계정 순회
# ─────────────────────────────────────────────────────────────────────────────

def _login_for_account(driver, account, log):
    """단일 계정 로그인만 수행. 실패 시 예외. (쿠키 우선 → 일반 로그인)"""
    # 1) 쿠키 또는 일반 로그인 (eleven_crawler 인프라 재사용)
    used_cookie = _ec._try_cookie_login(driver, account)
    if used_cookie is None:
        raise Exception('Chrome 죽음(쿠키 로그인)')
    if not used_cookie:
        # 깨끗한 세션
        try:
            driver.get('https://login.11st.co.kr/auth/front/logout.tmall')
            time.sleep(0.5)
        except Exception:
            pass
        try:
            driver.get('about:blank')
            time.sleep(0.3)
            driver.delete_all_cookies()
        except Exception:
            pass

        log('로그인 시도...')
        if not _ec._do_login(driver, account.login_id, account.password_enc):
            raise Exception('로그인 실패')
        log('로그인 성공')
        _ec._save_cookies(driver, account)
    else:
        log('쿠키 재사용 (로그인 우회)')


# ─────────────────────────────────────────────────────────────────────────────
# 대량엑셀(팝업) 다운로드 방식 — sellerNo 자동탐지 → 생성요청 → 오늘 파일 완료대기 → 다운로드
# ─────────────────────────────────────────────────────────────────────────────
EXCEL_DOWNLOAD_URL = 'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={sn}'
BTN_GEN_XPATH = '//*[@id="popup-body-search"]/div[2]/button'
GEN_POLL_ROUNDS = 24       # 15s × 24 = 최대 6분 대기 (대형 카탈로그 9천개 생성 지연 대비)
GEN_POLL_INTERVAL = 15


def _accept_alert(driver, wait_s, tag=''):
    """alert 가 뜰 때까지 최대 wait_s 초 대기 후 수락. 텍스트 반환."""
    for _ in range(int(wait_s * 2)):
        try:
            a = driver.switch_to.alert
            t = a.text
            a.accept()
            time.sleep(0.4)
            return t
        except Exception:
            time.sleep(0.5)
    return None


def _grid_text(driver):
    try:
        return driver.execute_script(
            "var g=document.getElementById('popup-body-grid');return g?g.innerText:''") or ''
    except Exception:
        return ''


def _detect_seller_no(driver, log):
    """TP 쿠키의 M_N = 로그인 셀러의 sellerNo. 셀러오피스 페이지 로드 후 가장 안정적."""
    try:
        if 'soffice.11st' not in driver.current_url:
            driver.get('https://soffice.11st.co.kr/view/main')
            time.sleep(5)
    except Exception:
        pass
    for c in driver.get_cookies():
        if c['name'] == 'TP':
            m = re.search(r'M_N(?:%7C|\|)(\d{6,})', c['value'])
            if m:
                return m.group(1)
    return None


def _excel_download_today(driver, account, log):
    """대량엑셀 생성요청 → 오늘자 '파일 생성 완료' 대기 → 다운로드. 파일경로 반환."""
    sn = _detect_seller_no(driver, log)
    if not sn:
        raise Exception('sellerNo 탐지 실패 (TP쿠키 M_N 없음)')
    log(f'sellerNo={sn}')

    dl_dir = DOWNLOAD_BASE / account.login_id
    dl_dir.mkdir(parents=True, exist_ok=True)
    for f in dl_dir.glob('*'):
        try:
            f.unlink()
        except Exception:
            pass

    # 페이지 로드 — '조회할 수 없습니다'(간헐적 조회실패) 시 reload 재시도 최대 3회
    url = EXCEL_DOWNLOAD_URL.format(sn=sn)
    last_alert = None
    for attempt in range(1, 4):
        driver.get(url)
        time.sleep(random.uniform(5, 7))
        last_alert = _accept_alert(driver, 3, f'load{attempt}')
        if not (last_alert and '조회할 수 없습니다' in last_alert):
            break
        log(f'그리드 조회실패({attempt}/3) — {random.randint(6,10)}s 후 재시도')
        time.sleep(random.uniform(6, 10))
    else:
        raise Exception(f'대량엑셀 조회불가 (3회 재시도 실패): {last_alert}')
    try:
        driver.execute_cdp_cmd('Page.setDownloadBehavior',
                               {'behavior': 'allow', 'downloadPath': str(dl_dir)})
    except Exception:
        pass

    # 파일명(쿼리스트링 앞부분)의 날짜가 오늘/어제(자정 경계 대비)인 다운로드 링크를 폴링
    # 주의: S3 서명 URL의 X-Amz-Date 에 걸리지 않도록 '?' 앞 파일명만 검사
    import datetime as _dt
    _now = _dt.datetime.now()
    valid_dates = [_now.strftime('%Y%m%d'), (_now - _dt.timedelta(days=1)).strftime('%Y%m%d')]
    # 파일명에 valid_dates 중 하나가 들어간 첫 링크 반환
    find_js = (
        "var ds=arguments[0];var ls=document.querySelectorAll('#popup-body-grid a');"
        "for(var i=0;i<ls.length;i++){var h=ls[i].href||'';"
        "var fn=h.split('?')[0].split('/').pop();"
        "for(var j=0;j<ds.length;j++){if(fn.indexOf(ds[j])>=0)return h;}}return '';")
    click_js = (
        "var ds=arguments[0];var ls=document.querySelectorAll('#popup-body-grid a');"
        "for(var i=0;i<ls.length;i++){var h=ls[i].href||'';"
        "var fn=h.split('?')[0].split('/').pop();"
        "for(var j=0;j<ds.length;j++){if(fn.indexOf(ds[j])>=0){ls[i].click();return;}}}")

    # 생성요청 → 폴링 → 다운로드 → 날짜검증 을 최대 2회.
    # 11번가가 옛 생성본을 먼저 주거나(파일 오늘자 아님) 생성이 느릴 때(타임아웃)
    # 생성요청을 다시 눌러 강제 재생성한다. (대형 카탈로그 생성 지연 대비)
    last_err = None
    for gen_attempt in range(1, 3):
        # 옛 파일/이전 시도 잔재 제거 (newest 매칭이 옛 파일을 잡지 않도록)
        for f in dl_dir.glob('*'):
            try:
                f.unlink()
            except Exception:
                pass

        # 생성요청
        btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, BTN_GEN_XPATH)))
        driver.execute_script("arguments[0].click();", btn)
        atxt = _accept_alert(driver, 15, f'gen{gen_attempt}')
        log(f'파일생성요청({gen_attempt}/2): {atxt}')

        href = ''
        for i in range(GEN_POLL_ROUNDS):
            time.sleep(GEN_POLL_INTERVAL)
            _accept_alert(driver, 2)
            try:
                driver.refresh()
                time.sleep(random.uniform(4, 6))
            except Exception:
                pass
            _accept_alert(driver, 2)
            try:
                href = driver.execute_script(find_js, valid_dates)
            except Exception:
                href = ''
            if href:
                log(f'오늘자 파일 생성완료 링크 확인 ({(i+1)*GEN_POLL_INTERVAL}s)')
                break
        if not href:
            last_err = '오늘자 파일 생성완료 미확인 (타임아웃)'
            log(f'{last_err}' + (' — 강제 재생성' if gen_attempt < 2 else ''))
            continue

        # 오늘/어제 파일명이 든 링크만 정확히 클릭 (옛 파일/서명날짜 오매칭 방지)
        driver.execute_script(click_js, valid_dates)
        _accept_alert(driver, 5, 'dl')
        fp = None
        for _ in range(90):
            files = [f for f in dl_dir.glob('*') if not f.name.endswith('.crdownload')]
            if files:
                fp = max(files, key=lambda f: f.stat().st_mtime)
                break
            time.sleep(1)
        if not fp:
            last_err = '다운로드 실패 (파일 없음)'
            log(f'{last_err}' + (' — 강제 재생성' if gen_attempt < 2 else ''))
            continue

        # 생성일자 검증 (오늘/어제 허용 — 자정 경계)
        fm = re.search(r'_(\d{8})\d{6}', fp.name)
        if fm and fm.group(1) not in valid_dates:
            last_err = f'다운로드 파일이 오늘자 아님 ({fm.group(1)})'
            log(f'{last_err}' + (' — 강제 재생성' if gen_attempt < 2 else ''))
            continue

        log(f'다운로드: {fp.name} ({fp.stat().st_size}b)')
        return fp

    raise Exception(last_err or '대량엑셀 다운로드 실패')


def _extract_and_parse(fp, log):
    """zip(알집) 해제 → 내부 엑셀/CSV 파싱."""
    fp = Path(fp)
    target = fp
    if zipfile.is_zipfile(fp):
        out = fp.parent
        with zipfile.ZipFile(fp) as z:
            names = z.namelist()
            z.extractall(out)
        inner = [out / n for n in names if n.lower().endswith(('.xls', '.xlsx', '.csv'))]
        if inner:
            target = inner[0]
    return _parse_excel(target)


def _run_for_account(driver, account, log):
    """단일 계정 처리(대량엑셀 방식). 성공 시 (upserted, total), 실패 시 예외.
    (로그인은 _login_for_account 로 분리 — 호출자가 접속 재시도를 담당)"""
    try:
        fp = _excel_download_today(driver, account, log)
    except Exception as e:
        # 세션 만료로 '조회불가' 시 → 쿠키 무효화 후 새 로그인(OTP) → 1회 재시도 (self-heal)
        if '조회불가' in str(e):
            from apps.cpc.models import CrawlerAccount
            log('조회불가 → 세션만료 추정, 쿠키 무효화 후 새 로그인 재시도')
            try:
                CrawlerAccount.objects.filter(login_id=account.login_id, platform='11st').update(cookie_data='')
                account.cookie_data = ''
                driver.delete_all_cookies()
            except Exception:
                pass
            _login_for_account(driver, account, log)   # 쿠키없음 → 풀로그인+OTP+쿠키저장
            fp = _excel_download_today(driver, account, log)
        else:
            raise
    products = _extract_and_parse(fp, log)
    log(f'파싱: {len(products)}건')
    if not products:
        raise Exception('수집된 상품 0건')
    upserted = _upsert_products(account, products)
    return upserted, len(products)


def run_all_accounts(log_fn=None, account_filter=None, only_no_api_key=True, force=False):
    """11번가 셀러오피스 '내 상품' Selenium 크롤러 일괄 실행.
    only_no_api_key=True (기본) — api_key 가 없는 계정만 대상 (OpenAPI 동기화와 보완).
    force=True 면 신선도(최근 수집) 스킵 무시."""
    from apps.cpc.models import CrawlerAccount, CrawlerLog
    from apps.cpc import eleven_block_guard as guard
    from django.db.models import Max
    from apps.cpc.models import ElevenMyProduct

    def emit(msg):
        logger.info(msg)
        if log_fn:
            log_fn(msg)

    if guard.guard_and_skip('product crawler'):
        emit('⛔ 11번가 글로벌 차단 모드 — product 크롤러 스킵')
        return {'collected': 0, 'failed': 0, 'aborted_due_to_global_block': True}

    qs = CrawlerAccount.objects.filter(platform='11st', is_active=True)
    if only_no_api_key:
        qs = qs.filter(api_key='')
    accounts = list(qs)
    if account_filter:
        accounts = [a for a in accounts if a.login_id in account_filter]
    # 등록상품 0개(빈 계정) — 11번가 대량엑셀이 생성되지 않아 제외 (광고비/세무 크롤은 정상 대상)
    accounts = [a for a in accounts if a.login_id not in PRODUCT_EXCLUDE]

    if not accounts:
        emit('대상 계정 없음')
        return {'collected': 0, 'failed': 0}

    # 신선도 필터
    last_synced_map = {
        x['account_id']: x['m']
        for x in ElevenMyProduct.objects.filter(account_id__in=[a.id for a in accounts])
            .values('account_id').annotate(m=Max('synced_at'))
    }
    fresh, skipped_recent = [], []
    for a in accounts:
        if not force and guard.is_recently_synced(last_synced_map.get(a.id), hours=SKIP_RECENT_HOURS) \
                and a.crawling_status == '정상':
            skipped_recent.append(a.login_id)
        else:
            fresh.append(a)
    accounts = fresh
    total = len(accounts)
    if skipped_recent:
        emit(f'최근 {SKIP_RECENT_HOURS}h 내 성공 {len(skipped_recent)}계정 스킵, 대상 {total}계정')

    # 계정 순서 무작위 — 동일 패턴 차단 회피
    random.shuffle(accounts)

    collected = 0
    failed = 0
    consecutive_block = 0
    aborted = False
    driver = None

    def _safe_quit(d):
        if not d:
            return
        try:
            d.quit()
        except Exception:
            pass

    def _new_driver():
        _kill_stale_chrome()
        time.sleep(1)
        return create_driver(download_dir=str(DOWNLOAD_BASE))

    def _is_dead(e):
        s = str(e)
        return any(k in s for k in ('Connection refused', 'NewConnectionError',
                                     'invalid session id', 'chrome not reachable',
                                     'session deleted', 'disconnected'))

    try:
        driver = _new_driver()

        for idx, account in enumerate(accounts, 1):
            if guard.guard_and_skip(f'product[{account.login_id}]'):
                aborted = True
                break
            if account.crawling_status in ('차단됨', '실패'):
                emit(f'[11st:{account.login_id}] {account.crawling_status} - 건너뜀')
                continue

            login_id = account.login_id

            def log(msg, _lid=login_id):
                m = f'[11st:{_lid}] {msg}'
                logger.info(m)
                if log_fn:
                    log_fn(m)

            # 매 계정마다 driver 재생성 (안정성 + 핑거프린트 갱신)
            if idx > 1:
                _safe_quit(driver)
                driver = _new_driver()

            # ── 접속(로그인) 단계: 최대 3회 시도. 3회 실패 시 중지→다음 계정 ──
            logged_in = False
            for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
                if guard.guard_and_skip(f'product[{login_id}] 접속'):
                    aborted = True
                    break
                try:
                    if driver is None:
                        driver = _new_driver()
                    try:
                        driver.get('about:blank')
                        time.sleep(0.3)
                        driver.delete_all_cookies()
                    except Exception:
                        pass
                    log(f'접속 시도 {attempt}/{MAX_CONNECT_ATTEMPTS}...')
                    _login_for_account(driver, account, log)
                    logged_in = True
                    break
                except Exception as le:
                    log(f'접속 실패 {attempt}/{MAX_CONNECT_ATTEMPTS}: {str(le)[:120]}')
                    if guard.is_block_signal(le):
                        consecutive_block += 1
                        if consecutive_block >= CIRCUIT_BREAKER_THRESHOLD:
                            guard.report_signal(le, source='product crawler')
                            aborted = True
                            log('⛔ circuit breaker 발동 — 중단')
                            break
                    if _is_dead(le):
                        _safe_quit(driver)
                        driver = None
                    if attempt < MAX_CONNECT_ATTEMPTS:
                        time.sleep(random.uniform(2.0, 4.0))

            if aborted:
                break

            if not logged_in:
                # ── 접속 3회 실패 → 반드시 중지하고 다음 계정으로 ──
                account.fail_count += 1
                account.mark_connect_failed()
                if account.fail_count >= 30 and account.crawling_status != '실패':
                    account.crawling_status = '차단됨'
                account.save()
                failed += 1
                CrawlerLog.objects.create(
                    platform='11st', level='error',
                    message=f'[product] 접속 {MAX_CONNECT_ATTEMPTS}회 실패 → 중지(다음 계정), 상태={account.crawling_status}',
                    account_id=login_id,
                )
                log(f'⛔ 접속 {MAX_CONNECT_ATTEMPTS}회 실패 — 다음 계정 (상태={account.crawling_status})')
                try:
                    # 일시적 실패는 보류, 연속 실패(회복 안 됨)만 알림 (1일 1회)
                    guard.notify_failure(login_id, 'connect',
                        f'접속 {MAX_CONNECT_ATTEMPTS}회 연속 실패 (상태: {account.crawling_status})',
                        account.seller_name)
                except Exception:
                    pass
                if idx < total:
                    time.sleep(random.uniform(*INTER_ACCOUNT_SLEEP))
                continue

            # ── 접속 성공 → 상품 수집 ──
            consecutive_block = 0
            account.reset_connect_fail()
            try:
                upserted, total_found = _run_for_account(driver, account, log)
                account.fail_count = 0
                account.crawling_status = '정상'
                account.last_crawled_at = timezone.now()
                account.save()
                collected += 1
                CrawlerLog.objects.create(
                    platform='11st', level='success',
                    message=f'[product] {upserted}/{total_found}건 동기화',
                    account_id=login_id,
                )
                guard.notify_success(login_id, 'product')   # 연속실패 카운터 리셋
                log(f'완료 — {upserted}건 UPSERT (수집 {total_found})')

            except Exception as e:
                account.fail_count += 1
                if account.fail_count >= 30:
                    account.crawling_status = '차단됨'
                account.save()
                failed += 1
                CrawlerLog.objects.create(
                    platform='11st', level='error',
                    message=f'[product] {e}',
                    account_id=login_id,
                )
                log(f'수집 실패: {e}')
                try:
                    # 일시적 실패는 보류, 연속 실패(회복 안 됨)만 알림 (1일 1회)
                    guard.notify_failure(login_id, 'product', e, account.seller_name)
                except Exception:
                    pass

                if guard.is_block_signal(e):
                    consecutive_block += 1
                    log(f'차단신호 누적 {consecutive_block}/{CIRCUIT_BREAKER_THRESHOLD}')
                    if consecutive_block >= CIRCUIT_BREAKER_THRESHOLD:
                        guard.report_signal(e, source='product crawler')
                        aborted = True
                        log('⛔ circuit breaker 발동 — 중단')
                        break

                if _is_dead(e):
                    _safe_quit(driver)
                    driver = None
                    try:
                        driver = _new_driver()
                    except Exception as e2:
                        logger.error('driver 재생성 실패: %s', e2)
                        continue

            # 다음 계정까지 사람처럼 대기
            if idx < total:
                wait = random.uniform(*INTER_ACCOUNT_SLEEP)
                emit(f'다음 계정까지 {wait:.1f}s 대기')
                time.sleep(wait)

    finally:
        _safe_quit(driver)
        stop_display()

    summary = f'11번가 상품 크롤러 완료: 성공={collected} 실패={failed}'
    if aborted:
        summary += ' (차단신호로 조기 중단)'
    emit(summary)

    return {
        'collected': collected,
        'failed': failed,
        'aborted_due_to_block': aborted,
        'skipped_recent': len(skipped_recent),
    }

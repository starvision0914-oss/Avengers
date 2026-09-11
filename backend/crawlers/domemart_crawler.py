"""도매마트(domemart.co.kr) L코드 판매상태(판매중/품절) 조회.
로그인+검색을 단일 브라우저 세션으로 유지(세션이 스크립트 재실행 간엔 유지 안 됨 확인됨).
사람이 쓰는 속도로 코드 하나씩 조회(랜덤 지연) — 대량 벌크조회 기능 없음.
"""
import logging
import random
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawlers.browser import create_driver

logger = logging.getLogger(__name__)

LOGIN_URL = 'https://www.domemart.co.kr/shop/login.php'
HOME_URL = 'http://www.domemart.co.kr/shop/index.php'
SEARCH_XPATH = '/html/body/div[4]/div/div[1]/div/div[2]/div/table/tbody/tr/td[2]/form/table/tbody/tr/td[2]/input'
LOGIN_ID = 'rejoice888'
LOGIN_PW = '@dlwodbs0'

_COUNT_RE = re.compile(r'총\s*([0-9,]+)개의\s*상품')
_PRICE_RE = re.compile(r'([0-9][0-9,]*)\s*원')


def is_logged_out(driver):
    return 'login.php' in driver.current_url


def do_login(driver):
    # user_data_dir(/tmp/domemart_profile_run)가 영속 프로필이라 이전 세션 쿠키가 남아있으면
    # login.php 접속 시 곧바로 index.php로 리다이렉트됨(이미 로그인된 상태) — 이 경우 로그인폼
    # 자체가 없는 게 정상이라 "못 찾음" 실패가 아니라 성공으로 봐야 함(2026-08-24 실측 확인:
    # 브라우저 강제종료 후 재시작 때 이 상태였는데 실패로 오판해 3회 재시도 후 죽었음).
    driver.get(LOGIN_URL)
    time.sleep(1.5)
    if 'login.php' not in driver.current_url:
        logger.info(f'[domemart] 이미 로그인된 세션 감지(url={driver.current_url}) — 로그인 생략')
        return

    mb_id = None
    for attempt in range(3):
        if attempt > 0:
            driver.get(LOGIN_URL)
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, 'MB_ID')))
            mb_id = driver.find_element(By.NAME, 'MB_ID')
            break
        except Exception as e:
            logger.info(f'[domemart] 로그인폼 로딩 실패(시도 {attempt+1}/3) url={driver.current_url}: {e}')
            time.sleep(2)
    if mb_id is None:
        raise Exception(f'로그인폼 로딩 실패(3회 재시도 소진), url={driver.current_url}')
    mb_id.clear()
    mb_id.send_keys(LOGIN_ID)
    pw = driver.find_element(By.NAME, 'MB_PW')
    pw.clear()
    pw.send_keys(LOGIN_PW)
    pw.send_keys(Keys.RETURN)
    time.sleep(3)
    try:
        driver.switch_to.alert.accept()
    except NoAlertPresentException:
        pass


def check_code(driver, code, retries=2):
    """반환: {'code','count','has_soldout_word'} 또는 {'code','error':True}
    검색창(mall_keyword)은 검색결과 페이지(mall.php)에도 그대로 남아있어(실측 2026-08-22)
    매번 홈으로 돌아갈 필요 없이 결과 페이지에서 바로 이어서 검색 가능 — 최초 1회/재로그인 후에만 홈 이동."""
    for attempt in range(retries):
        try:
            fields = driver.find_elements(By.NAME, 'mall_keyword')
            if not fields or is_logged_out(driver):
                if is_logged_out(driver):
                    logger.info('로그아웃 감지 — 재로그인')
                    do_login(driver)
                driver.get(HOME_URL)
                time.sleep(random.uniform(0.8, 1.5))
                fields = driver.find_elements(By.NAME, 'mall_keyword')
            el = fields[0]
            el.clear()
            el.send_keys(code)
            el.send_keys(Keys.RETURN)
            # staleness_of: 옛 검색창 DOM이 사라지는(=새 페이지로 실제 전환된) 순간을 감지.
            # page_source 길이비교보다 가볍고(전체 HTML 전송 불필요) 우연히 길이가 같아
            # 오탐할 위험도 없음 — 서버렌더링(mall.php)이라 전환 즉시 새 본문도 이미 완성돼있음.
            # 검증(2026-08-22): 여러 코드에서 count/품절 값 fast=safe 완전 일치 확인.
            try:
                WebDriverWait(driver, 3, poll_frequency=0.1).until(EC.staleness_of(el))
            except Exception:
                pass
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            if is_logged_out(driver) or ('아이디' in body_text[:50] and '비밀번호' in body_text[:80]):
                logger.info('%s: 검색중 로그아웃됨 — 재시도', code)
                do_login(driver)
                continue
            m = _COUNT_RE.search(body_text)
            count = int(m.group(1).replace(',', '')) if m else None
            has_soldout_word = '품절' in body_text
            price = None
            if count:
                # 상품명 링크(a.em2) 바로 다음에 오는 <b>가 판매가(단가) — 같은 결과페이지에서
                # 별도 페이지이동 없이 함께 추출(2026-08-26 실측: 배송비 안내문구 "4,230 원"과
                # 혼동 방지 위해 상품명 링크 기준 상대위치로 특정).
                try:
                    price_el = driver.find_element(
                        By.XPATH, "(//a[@class='em2'])[1]/following::b[1]")
                    pm = _PRICE_RE.search(price_el.text or '')
                    if pm:
                        price = int(pm.group(1).replace(',', ''))
                except Exception:
                    pass
            return {'code': code, 'count': count, 'has_soldout_word': has_soldout_word, 'price': price}
        except Exception as e:
            logger.warning('%s: 오류(%d/%d) %s', code, attempt + 1, retries, str(e)[:100])
            time.sleep(2)
    return {'code': code, 'count': None, 'error': True}


def result_to_status(result):
    """check_code() 결과 → 'in_stock'/'soldout'/'not_found'"""
    if result.get('error'):
        return None
    count = result.get('count')
    if not count:
        return 'not_found'
    if result.get('has_soldout_word'):
        return 'soldout'
    return 'in_stock'


def new_driver(user_data_dir='/tmp/domemart_profile_run'):
    return create_driver(user_data_dir=user_data_dir, kill_existing=False)


ORDER_LIST_URL = 'http://www.domemart.co.kr/shop/mall.php?module=order&xque=od_list'
_RESULT_COUNT_RE = re.compile(r'검색결과\s*:\s*([\d,]+)\s*건')

# 오너클랜 화면(order_stats 8종)에 맞춘 근접 매핑 — 도매마트 주문상태(ct_flag_banpum)가 더
# 세분화돼 있어 완전히 1:1은 아님(2026-09-11 실측, 클래스 설명은 models.DomemartAccountInfo 참고).
# 값이 리스트인 항목(반품/교환 요청)은 여러 코드의 건수를 합산.
ORDER_STAT_CODE_MAP = {
    '배송중': ['15'],
    '결제완료': ['12'],       # 입금확인
    '배송완료': ['16'],
    '배송준비': ['13'],       # 배송준비중
    '주문취소': ['39'],       # 취소완료
    '취소요청': ['31'],       # 취소요청(접수)
    '반품/교환 요청': ['41', '51'],   # 반품요청(접수)+교환요청(접수)
    '반품/교환 진행': ['42'],  # 반품보류(대기)
}


def _order_count(driver, code):
    driver.get(f'{ORDER_LIST_URL}&ct_flag_banpum={code}')
    time.sleep(1.2)
    body = driver.find_element(By.TAG_NAME, 'body').text
    m = _RESULT_COUNT_RE.search(body)
    return int(m.group(1).replace(',', '')) if m else 0


def crawl_account_info(driver, log_fn=None):
    """예치금(적립금) 잔액 + 주문상태별 건수를 조회해 DomemartAccountInfo에 저장.
    반환: {'balance':int, 'order_stats':dict}"""
    from apps.cpc.models import DomemartAccountInfo
    from django.utils import timezone

    def log(m):
        logger.info(f'[domemart-info] {m}')
        if log_fn:
            log_fn(f'[domemart-info] {m}')

    do_login(driver)
    time.sleep(1)

    driver.get(HOME_URL)
    time.sleep(1.5)
    balance = 0
    try:
        el = driver.find_element(By.XPATH, "//a[contains(@href,'cash_history')]//b")
        bm = _PRICE_RE.search(el.text or '')
        if bm:
            balance = int(bm.group(1).replace(',', ''))
    except Exception as e:
        log(f'예치금 조회 실패: {e}')
    log(f'예치금 {balance:,}원')

    order_stats = {}
    for label, codes in ORDER_STAT_CODE_MAP.items():
        try:
            total = sum(_order_count(driver, c) for c in codes)
        except Exception as e:
            log(f'{label} 조회 실패: {e}')
            total = 0
        order_stats[label] = str(total)
        log(f'{label}: {total}건')

    DomemartAccountInfo.objects.update_or_create(
        login_id=LOGIN_ID,
        defaults={'balance': balance, 'order_stats': order_stats, 'info_synced_at': timezone.now()},
    )
    return {'balance': balance, 'order_stats': order_stats}


ORDER_LIST_1M_URL = f'{ORDER_LIST_URL}&q_date_type=m1'
INVOICE_COLUMNS = ['받는분휴대폰', '배송사', '송장번호']   # 원본(항목전체 양식) S/AC/AD열


def crawl_invoice_download(driver, download_dir, log_fn=None):
    """도매마트 주문/배송조회(1개월) → 엑셀다운로드('항목전체' 양식) → S/AC/AD(받는분휴대폰/배송사/
    송장번호)만 추출해 media/domemart_order_files/에 저장 + DomemartOrderFile 기록.
    도매마트 다운로드는 실제로는 .xls 확장자의 HTML 테이블이라 pandas.read_html로 파싱한다
    (2026-09-11 실측 — xlrd/openpyxl 둘 다 진짜 바이너리가 아니라서 못 읽음).
    반환: {'ok':bool, 'row_count':int, 'file_path':str} 또는 {'ok':False, 'error':str}"""
    import glob
    import os
    import pandas as pd
    from django.conf import settings
    from django.utils import timezone
    from apps.cpc.models import DomemartOrderFile

    def log(m):
        logger.info(f'[domemart-invoice] {m}')
        if log_fn:
            log_fn(f'[domemart-invoice] {m}')

    do_login(driver)
    time.sleep(1)

    os.makedirs(download_dir, exist_ok=True)
    for f in glob.glob(download_dir + '/*'):
        try: os.remove(f)
        except Exception: pass

    driver.get(ORDER_LIST_1M_URL)
    time.sleep(2)
    try:
        driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': download_dir})
    except Exception as e:
        log(f'다운로드 경로 설정 실패: {e}')

    try:
        driver.execute_script("document.getElementById('list_check_excel0').checked = true;")
        driver.execute_script("multiDown('excel_od_list','excel');")
    except Exception as e:
        return {'ok': False, 'error': f'다운로드 트리거 실패: {e}'}

    fp = None
    for _ in range(20):
        time.sleep(1)
        files = [f for f in glob.glob(download_dir + '/*.xls') if not f.endswith('.crdownload')]
        if files:
            fp = files[0]
            break
    if not fp:
        return {'ok': False, 'error': '다운로드 파일을 찾지 못함(20초 대기)'}

    try:
        tables = pd.read_html(fp)
        df = tables[0]
    except Exception as e:
        return {'ok': False, 'error': f'엑셀 파싱 실패: {e}'}

    missing = [c for c in INVOICE_COLUMNS if c not in df.columns]
    if missing:
        return {'ok': False, 'error': f'예상 컬럼 없음(사이트 양식 변경?): {missing}'}
    trimmed = df[INVOICE_COLUMNS].copy()
    # 송장번호가 float(예: 6.002791e+11)로 읽히는 문제 보정 — 원래 숫자문자열 그대로.
    trimmed['송장번호'] = trimmed['송장번호'].apply(
        lambda v: '' if pd.isna(v) else (str(int(v)) if isinstance(v, float) else str(v)))
    trimmed = trimmed.dropna(how='all')

    storage_dir = os.path.join(settings.BASE_DIR, 'media', 'domemart_order_files')
    os.makedirs(storage_dir, exist_ok=True)
    now = timezone.now()
    filename = f'{LOGIN_ID}_invoice_{now:%Y%m%d_%H%M%S}.csv'
    out_path = os.path.join(storage_dir, filename)
    # xlsx/xls 모두 "파일 형식과 확장자가 일치하지 않습니다" 같은 확인창이 뜰 수 있어,
    # 그런 검사 자체가 없는 순수 텍스트 CSV로 저장한다. utf-8-sig(BOM)로 저장해야
    # 엑셀에서 더블클릭만으로 한글이 깨지지 않고 바로 열린다.
    trimmed.to_csv(out_path, index=False, encoding='utf-8-sig')

    rec = DomemartOrderFile.objects.create(
        login_id=LOGIN_ID, filename=filename, file_path=out_path,
        file_size=os.path.getsize(out_path), row_count=len(trimmed))
    log(f'저장 완료: {filename} ({len(trimmed)}행)')

    # 보관 개수 제한(2026-09-11 사용자 요청): 최신 2개만 남기고 그 이전은 파일+DB 모두 삭제.
    KEEP = 2
    old = DomemartOrderFile.objects.order_by('-downloaded_at')[KEEP:]
    for f in old:
        try:
            if os.path.isfile(f.file_path):
                os.remove(f.file_path)
        except Exception:
            pass
        f.delete()
        log(f'보관 {KEEP}개 초과분 삭제: {f.filename}')

    return {'ok': True, 'row_count': len(trimmed), 'file_path': out_path, 'id': rec.id}

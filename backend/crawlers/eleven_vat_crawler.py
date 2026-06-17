"""11번가 부가세(매출) 자료 크롤러 — 셀러오피스 부가세신고내역(view/30476).

기존 eleven_crawler 의 로그인/쿠키/팝업 인프라를 재사용한다.
부가세신고내역 표(월별 과세매출 + 결제수단)를 파싱해 TaxVatMonthly 에 저장.
크롤 원칙: 사람처럼 페이싱 + 계정당 로그인 3회 실패 시 다음 계정 진행 (IP차단 방지).
"""
import re
import time
import random
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

logger = logging.getLogger('crawler')

VAT_URL = "https://soffice.11st.co.kr/view/30476"   # 부가세신고내역
MAX_CONNECT_ATTEMPTS = 3                              # 계정당 로그인 3회 실패 시 다음 계정


def _pint(text):
    c = re.sub(r'[^\d\-]', '', (text or '').strip())
    return int(c) if c and c != '-' else 0


def _enter_vat_page(driver, log):
    """부가세신고내역 페이지 진입 (iframe 내부에 검색 폼)."""
    from .eleven_crawler import _dismiss_dom_modals
    driver.switch_to.default_content()
    driver.get(VAT_URL)
    time.sleep(5)
    _dismiss_dom_modals(driver)
    # iframe 탐색
    for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            if iframe.is_displayed():
                driver.switch_to.frame(iframe)
                if driver.find_elements(By.ID, "searchStartMonth"):
                    return True
                driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()
    if driver.find_elements(By.ID, "searchStartMonth"):
        return True
    log("부가세 페이지 접근 실패")
    return False


def _set_period_and_search(driver, start_ym, end_ym, log):
    try:
        Select(driver.find_element(By.ID, "searchStartYear")).select_by_value(start_ym[:4]); time.sleep(0.3)
        Select(driver.find_element(By.ID, "searchStartMonth")).select_by_value(start_ym[4:]); time.sleep(0.3)
        Select(driver.find_element(By.ID, "searchEndYear")).select_by_value(end_ym[:4]); time.sleep(0.3)
        Select(driver.find_element(By.ID, "searchEndMonth")).select_by_value(end_ym[4:]); time.sleep(0.5)
    except Exception as e:
        log(f"기간 설정 실패: {e}")
        return False
    try:
        btn = driver.find_element(By.ID, "btnSearch")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(8)
        return True
    except Exception as e:
        log(f"검색 버튼 실패: {e}")
        return False


def _parse_vat_table(driver, log):
    """table[1] 파싱. 컬럼: 기간/과세매출/신용카드/현금영수증/지출증빙/휴대폰/기타/부가수수료/면세/영세."""
    rows = []
    tables = driver.find_elements(By.TAG_NAME, "table")
    if len(tables) < 2:
        log("데이터 테이블 없음")
        return rows
    for tr in tables[1].find_elements(By.TAG_NAME, "tr"):
        tds = tr.find_elements(By.TAG_NAME, "td")
        if len(tds) < 7:
            continue
        period = tds[0].text.strip()
        if '합계' in period:
            continue
        m = re.search(r'(\d{4})[-./년\s]*(\d{1,2})', period)
        if not m:
            continue
        # 실제 컬럼: 0기간 1과세매출 2신용카드 3현금 4휴대폰 5기타 6부가수수료 7다운로드 8면세 9영세
        rows.append({
            'year': int(m.group(1)), 'month': int(m.group(2)),
            'taxable_sales': _pint(tds[1].text),
            'credit_card': _pint(tds[2].text),
            'cash_receipt': _pint(tds[3].text),    # 현금
            'mobile': _pint(tds[4].text),          # 휴대폰
            'etc_amount': _pint(tds[5].text),      # 기타
            'extra_fee': _pint(tds[6].text),       # 부가수수료
            'expense_proof': 0,
            'tax_free_sales': _pint(tds[8].text) if len(tds) > 8 else 0,
            'zero_rate_sales': _pint(tds[9].text) if len(tds) > 9 else 0,
        })
    return rows


def _save_rows(account, rows):
    """TaxVatMonthly delete-insert (login_id, year-month 기준 idempotent)."""
    from apps.cpc.models import TaxVatMonthly, TaxAccountMap
    if not rows:
        return 0
    amap = TaxAccountMap.objects.filter(platform='11st', login_id=account.login_id).first()
    biz = amap.business if amap else None
    objs = []
    for r in rows:
        objs.append(TaxVatMonthly(
            business=biz, platform='11st', login_id=account.login_id,
            seller_name=account.seller_name or account.login_id,
            year=r['year'], month=r['month'],
            taxable_sales=r['taxable_sales'], tax_free_sales=r.get('tax_free_sales', 0),
            zero_rate_sales=r.get('zero_rate_sales', 0),
            credit_card=r['credit_card'], cash_receipt=r['cash_receipt'],
            expense_proof=r['expense_proof'], mobile=r['mobile'],
            etc_amount=r['etc_amount'], extra_fee=r.get('extra_fee', 0),
        ))
    yms = {(r['year'], r['month']) for r in rows}
    for (y, mo) in yms:
        TaxVatMonthly.objects.filter(platform='11st', login_id=account.login_id, year=y, month=mo).delete()
    TaxVatMonthly.objects.bulk_create(objs, batch_size=200)
    return len(objs)


def crawl_one_vat(account, start_ym, end_ym, log_fn=None, save=True):
    """1계정 부가세신고내역 수집. 반환: rows(list) 또는 None(로그인 실패)."""
    from .browser import create_driver, stop_display
    from .eleven_crawler import _try_cookie_login, _do_login, _save_cookies
    lid = account.login_id
    log = log_fn or (lambda m: logger.info(f'[11st-vat:{lid}] {m}'))

    driver = None
    try:
        for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
            driver = create_driver()
            try:
                ok = _try_cookie_login(driver, account)
                if ok is True:
                    log("쿠키 로그인 성공")
                else:
                    log(f"로그인 시도 {attempt}/{MAX_CONNECT_ATTEMPTS}...")
                    ok = _do_login(driver, lid, account.password_enc)
                    if ok:
                        _save_cookies(driver, account)
                if ok:
                    break
            except Exception as e:
                log(f"로그인 오류: {e}")
            # 실패 → driver 정리 후 재시도
            try:
                driver.quit()
            except Exception:
                pass
            driver = None
            if attempt < MAX_CONNECT_ATTEMPTS:
                time.sleep(random.uniform(3, 6))
        else:
            log(f"{MAX_CONNECT_ATTEMPTS}회 로그인 실패 — 다음 계정")
            return None

        if not _enter_vat_page(driver, log):
            return None
        if not _set_period_and_search(driver, start_ym, end_ym, log):
            return None
        rows = _parse_vat_table(driver, log)
        log(f"부가세 {len(rows)}개월 수집 (과세매출합 {sum(r['taxable_sales'] for r in rows):,})")
        if save:
            n = _save_rows(account, rows)
            log(f"{n}건 저장 완료")
        return rows
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        stop_display()


def run_vat_accounts(account_filter=None, start_ym=None, end_ym=None, log_fn=None, save=True):
    """11번가 부가세 전 계정 수집 (사람처럼 페이싱, 3회 실패 시 다음 계정)."""
    from apps.cpc.models import CrawlerAccount
    from django.utils import timezone
    log = log_fn or (lambda m: logger.info(m))

    now = timezone.localtime()
    start_ym = start_ym or f"{now.year}01"
    end_ym = end_ym or now.strftime("%Y%m")

    accounts = list(CrawlerAccount.objects.filter(platform='11st', is_active=True)
                    .exclude(crawling_status__in=['차단됨', '실패']).order_by('display_order', 'login_id'))
    if account_filter:
        accounts = [a for a in accounts if a.login_id in account_filter]
    else:
        accounts = [a for a in accounts if a.api_key]   # 기본: 광고비 49계정

    log(f"11번가 부가세 수집 시작 — {len(accounts)}계정, {start_ym}~{end_ym}")
    collected, failed = 0, 0
    for i, acct in enumerate(accounts, 1):
        log(f"[{i}/{len(accounts)}] {acct.login_id} ({acct.seller_name})")
        try:
            rows = crawl_one_vat(acct, start_ym, end_ym, log_fn=log, save=save)
            if rows is None:
                failed += 1
            else:
                collected += 1
        except Exception as e:
            failed += 1
            log(f"{acct.login_id} 오류: {e}")
        if i < len(accounts):
            time.sleep(random.uniform(6, 11))   # 계정 간 사람처럼 대기
    result = {'collected': collected, 'failed': failed, 'total': len(accounts)}
    log(f"완료: {result}")
    return result

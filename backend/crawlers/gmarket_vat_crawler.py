"""지마켓 ESM 부가세 매출자료 크롤러 — www.esmplus.com/Home/v2/vat-list

gmarket_cost_crawler.py 의 로그인/쿠키 인프라를 재사용.
마스터 계정으로 로그인 → 복수아이디 드롭다운 전부 수집 → TaxVatMonthly(platform='gmarket') 저장.
크롤 원칙: 사람처럼 페이싱 + 계정당 3회 실패 시 다음 계정 진행 (IP차단 방지).
"""
import re
import time
import random
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger('crawler')

VAT_URL = "https://www.esmplus.com/Home/v2/vat-list"
MAX_CONNECT_ATTEMPTS = 3


def _pint(text):
    c = re.sub(r'[^\d\-]', '', (text or '').strip())
    return int(c) if c and c != '-' else 0


def _enter_vat_iframe(driver, log):
    """VAT 페이지 진입 후 iframe 탐색. 'vat' src 우선, 없으면 첫 번째 실 iframe."""
    driver.switch_to.default_content()
    driver.get(VAT_URL)
    time.sleep(5)

    for attempt in range(5):
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = (iframe.get_attribute("src") or "").lower()
            if 'vat' in src:
                driver.switch_to.frame(iframe)
                time.sleep(2)
                log("VAT iframe 진입")
                return True
        # vat src 없으면 첫 번째 실 iframe 시도
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            if src and 'about:blank' not in src and 'javascript:' not in src:
                driver.switch_to.frame(iframe)
                time.sleep(2)
                if driver.find_elements(By.ID, "gmktSearchSDT"):
                    log("VAT iframe 진입 (첫 실 iframe)")
                    return True
                driver.switch_to.default_content()
        if attempt < 4:
            time.sleep(2)
    log("VAT iframe 진입 실패")
    return False


def _click_gmarket_tab(driver, log):
    try:
        tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="gmktTab"]/a'))
        )
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(2)
        return True
    except Exception as e:
        log(f"지마켓 탭 클릭 실패: {e}")
        return False


def _get_seller_ids(driver, login_id):
    """복수 셀러ID 드롭다운 목록 반환. 없으면 [(login_id, login_id)]."""
    try:
        select_el = driver.find_element(By.ID, "introSelectSellerId")
        opts = [(o.get_attribute("value"), o.text.strip())
                for o in select_el.find_elements(By.TAG_NAME, "option")
                if o.get_attribute("value")]
        return opts if opts else [(login_id, login_id)]
    except NoSuchElementException:
        return [(login_id, login_id)]


def _select_seller(driver, seller_id):
    try:
        Select(driver.find_element(By.ID, "introSelectSellerId")).select_by_value(seller_id)
        time.sleep(1)
        return True
    except Exception:
        return False


def _set_period(driver, start_ym, end_ym, log):
    """기간 select 설정. ESM VAT는 YYYYMM01 형식."""
    def _sel(el_id, val):
        try:
            sel = Select(driver.find_element(By.ID, el_id))
            try:
                sel.select_by_value(val + "01")
            except Exception:
                sel.select_by_value(val)
            return True
        except Exception as e:
            log(f"{el_id} 설정 실패: {e}")
            return False
    ok = _sel("gmktSearchSDT", start_ym)
    ok = _sel("gmktSearchEDT", end_ym) and ok
    time.sleep(0.5)
    return ok


def _search(driver, log):
    try:
        driver.execute_script("arguments[0].click();",
                               driver.find_element(By.ID, "btnSearch"))
        time.sleep(6)
    except Exception as e:
        log(f"검색 버튼 오류: {e}")
        return False
    try:
        alert = driver.switch_to.alert
        msg = alert.text
        alert.accept()
        log(f"검색 alert: {msg}")
        return False
    except Exception:
        return True


def _parse_vat_table(driver, log):
    """매출내역 table[1] 파싱.
    컬럼: 기간 / 총매출 / 신용카드 / 현금 / 모바일 / 기타카드 / 선불 / 쿠폰"""
    rows = []
    tables = driver.find_elements(By.TAG_NAME, "table")
    if len(tables) < 2:
        log("데이터 테이블 없음")
        return rows
    for tr in tables[1].find_elements(By.TAG_NAME, "tr"):
        tds = tr.find_elements(By.TAG_NAME, "td")
        if len(tds) < 4:
            continue
        period = tds[0].text.strip()
        if '합계' in period or not re.search(r'\d{4}', period):
            continue
        m = re.search(r'(\d{4}).*?(\d{1,2})', period)
        if not m:
            continue
        rows.append({
            'year': int(m.group(1)), 'month': int(m.group(2)),
            'total_sales': _pint(tds[1].text) if len(tds) > 1 else 0,
            'credit_card': _pint(tds[2].text) if len(tds) > 2 else 0,
            'cash':        _pint(tds[3].text) if len(tds) > 3 else 0,
            'mobile':      _pint(tds[4].text) if len(tds) > 4 else 0,
            'etc_card':    _pint(tds[5].text) if len(tds) > 5 else 0,
            'prepaid':     _pint(tds[6].text) if len(tds) > 6 else 0,
            'coupon':      _pint(tds[7].text) if len(tds) > 7 else 0,
        })
    return rows


def _save_rows(seller_id, seller_label, rows, log):
    """TaxVatMonthly에 저장. total_sales → taxable_sales."""
    from apps.cpc.models import TaxVatMonthly, CrawlerAccount
    if not rows:
        return 0
    acc = CrawlerAccount.objects.filter(platform='gmarket', login_id=seller_id).first()
    seller_name = (acc.seller_name if acc else None) or seller_label or seller_id
    objs = [
        TaxVatMonthly(
            platform='gmarket', login_id=seller_id, seller_name=seller_name,
            year=r['year'], month=r['month'],
            taxable_sales=r['total_sales'],
            credit_card=r['credit_card'],
            cash_receipt=r['cash'],
            mobile=r['mobile'],
            etc_amount=r['etc_card'] + r['prepaid'] + r['coupon'],
        )
        for r in rows
    ]
    yms = {(r['year'], r['month']) for r in rows}
    for y, mo in yms:
        TaxVatMonthly.objects.filter(platform='gmarket', login_id=seller_id,
                                     year=y, month=mo).delete()
    TaxVatMonthly.objects.bulk_create(objs, batch_size=200)
    log(f"[{seller_id}] {len(objs)}건 저장 (총매출합 {sum(r['total_sales'] for r in rows):,})")
    return len(objs)


def crawl_one_vat(account, start_ym, end_ym, log_fn=None, save=True):
    """1마스터계정 지마켓 부가세 수집. 반환: True(성공)/False(실패)."""
    from .browser import create_driver, stop_display
    from .gmarket_cost_crawler import _try_cookie_login, _esm_login, _save_cookies
    lid = account.login_id
    log = log_fn or (lambda m: logger.info(f'[gmarket-vat:{lid}] {m}'))

    driver = None
    try:
        for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
            driver = create_driver()
            try:
                ok = _try_cookie_login(driver, account)
                if ok:
                    log("쿠키 로그인 성공")
                else:
                    log(f"로그인 시도 {attempt}/{MAX_CONNECT_ATTEMPTS}...")
                    ok = _esm_login(driver, lid, account.password_enc)
                    if ok:
                        _save_cookies(driver, account)
                if ok:
                    break
            except Exception as e:
                log(f"로그인 오류: {e}")
            try:
                driver.quit()
            except Exception:
                pass
            driver = None
            if attempt < MAX_CONNECT_ATTEMPTS:
                time.sleep(random.uniform(3, 6))
        else:
            log(f"{MAX_CONNECT_ATTEMPTS}회 로그인 실패 — 다음 계정")
            return False

        if not _enter_vat_iframe(driver, log):
            return False
        if not _click_gmarket_tab(driver, log):
            return False

        sellers = _get_seller_ids(driver, lid)
        log(f"수집 대상 셀러: {[s[0] for s in sellers]}")

        for seller_id, seller_label in sellers:
            if len(sellers) > 1:
                if not _select_seller(driver, seller_id):
                    log(f"[{seller_id}] 셀러 선택 실패 — 스킵")
                    continue

            if not _set_period(driver, start_ym, end_ym, log):
                log(f"[{seller_id}] 기간 설정 실패")
                continue

            if not _search(driver, log):
                log(f"[{seller_id}] 조회 실패")
                continue

            rows = _parse_vat_table(driver, log)
            log(f"[{seller_id}] {len(rows)}개월 수집")

            if save and rows:
                _save_rows(seller_id, seller_label, rows, log)

            if len(sellers) > 1:
                time.sleep(random.uniform(2, 4))

        return True
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        stop_display()


def run_vat_accounts(account_filter=None, start_ym=None, end_ym=None, log_fn=None, save=True):
    """지마켓 부가세 마스터계정 전부 수집 (사람처럼 페이싱, 3회 실패 시 다음 계정)."""
    from apps.cpc.models import CrawlerAccount
    from django.db.models import Q
    from django.utils import timezone
    log = log_fn or (lambda m: logger.info(m))

    now = timezone.localtime()
    start_ym = start_ym or f"{now.year}01"
    end_ym = end_ym or now.strftime("%Y%m")

    # 마스터계정만 (gmarket_origin_id 없거나 빈 계정)
    accounts = list(
        CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
        .filter(Q(gmarket_origin_id__isnull=True) | Q(gmarket_origin_id=''))
        .order_by('display_order', 'login_id')
    )
    if account_filter:
        accounts = [a for a in accounts if a.login_id in account_filter]

    log(f"지마켓 부가세 수집 시작 — {len(accounts)}마스터계정, {start_ym}~{end_ym}")
    ok, failed = 0, 0
    for i, acct in enumerate(accounts, 1):
        log(f"[{i}/{len(accounts)}] {acct.login_id} ({acct.seller_name})")
        try:
            success = crawl_one_vat(acct, start_ym, end_ym, log_fn=log, save=save)
            if success:
                ok += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            log(f"{acct.login_id} 오류: {e}")
        if i < len(accounts):
            time.sleep(random.uniform(8, 14))

    result = {'ok': ok, 'failed': failed, 'total': len(accounts)}
    log(f"완료: {result}")
    return result

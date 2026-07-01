"""스마트스토어 부가세 매출자료 크롤러 — 정산관리 > 부가세신고내역.

smartstore_crawler.py 의 로그인 인프라(login_smartstore, switch_store)를 재사용.
ai100(betona1/ai100) smartstore_vat.py를 참고했으나, 실제 라이브 페이지는 구버전(#/naverpay/... 해시라우트
+ iframe #__delegate)에서 신버전(직결 페이지, iframe 없음)으로 바뀌어 실측 후 재작성함
(2026-07-01 실측: rejoice999 계정으로 로그인 후 페이지 구조 확인).
크롤 원칙: 사람처럼 페이싱 + 계정당 로그인 1회, 반기 단위로 기간 조회.
"""
import re
import time
import random
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

logger = logging.getLogger('crawler')

VAT_PAGE = "https://sell.smartstore.naver.com/e/v3/settlemgt/vatdeclaration"


def _pint(text):
    c = re.sub(r'[^\d\-]', '', (text or '').strip())
    return int(c) if c and c != '-' else 0


def _get_quarter_value(start_ym, end_ym):
    """YYYYMM 범위 → 분기/반기 select option value (1~4분기, 5=상반기, 6=하반기)."""
    sm, em = int(start_ym[4:]), int(end_ym[4:])
    mapping = {(1, 3): "1", (4, 6): "2", (7, 9): "3", (10, 12): "4", (1, 6): "5", (7, 12): "6"}
    return mapping.get((sm, em)) or ("5" if sm <= 6 else "6")


def _half_year_chunks(start_ym, end_ym):
    """start_ym~end_ym을 연도별 상/하반기(YYYYMM~YYYYMM) 단위로 쪼갠다."""
    sy, sm = int(start_ym[:4]), int(start_ym[4:])
    ey, em = int(end_ym[:4]), int(end_ym[4:])
    chunks = []
    for y in range(sy, ey + 1):
        for h_start, h_end in ((1, 6), (7, 12)):
            c_start = max(h_start, sm) if y == sy else h_start
            c_end = min(h_end, em) if y == ey else h_end
            if c_start <= c_end:
                chunks.append((f"{y}{c_start:02d}", f"{y}{c_end:02d}"))
    return chunks


def _enter_vat_page(driver, log):
    """부가세신고내역 페이지 진입 (iframe 없는 직결 페이지)."""
    driver.get(VAT_PAGE)
    time.sleep(5)
    if driver.find_elements(By.TAG_NAME, "select") and driver.find_elements(By.TAG_NAME, "table"):
        return True
    log(f"부가세 페이지 진입 실패 (URL: {driver.current_url})")
    return False


def _set_period_and_search(driver, start_ym, end_ym, log):
    quarter_val = _get_quarter_value(start_ym, end_ym)
    try:
        selects = driver.find_elements(By.TAG_NAME, "select")
        if not selects:
            log("기간 select 없음")
            return False
        Select(selects[0]).select_by_value(quarter_val)
        time.sleep(1)
    except Exception as e:
        log(f"기간 선택 실패: {e}")
        return False
    try:
        clicked = False
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            if btn.text.strip() == '검색':
                driver.execute_script("arguments[0].click();", btn)
                clicked = True
                break
        if not clicked:
            log("검색 버튼 못 찾음")
            return False
        time.sleep(5)
        return True
    except Exception as e:
        log(f"검색 클릭 실패: {e}")
        return False


def _parse_vat_table(driver, start_ym, end_ym, log):
    """table[0](월별내역) 파싱.
    컬럼(실측, 2026-07-01): 기간/과세매출금액/면세매출금액/신용카드매출전표/현금영수증/소득공제/지출증빙/발행제외(스킵)."""
    rows = []
    tables = driver.find_elements(By.TAG_NAME, "table")
    if not tables:
        log("데이터 테이블 없음")
        return rows
    start_y, start_m = int(start_ym[:4]), int(start_ym[4:])
    end_y, end_m = int(end_ym[:4]), int(end_ym[4:])
    for tr in tables[0].find_elements(By.TAG_NAME, "tr"):
        tds = tr.find_elements(By.TAG_NAME, "td")
        if len(tds) < 8:
            continue
        period = tds[0].text.strip()
        if '합계' in period:
            continue
        m = re.match(r'(\d{4})\.(\d{2})', period)
        if not m:
            continue
        year, month = int(m.group(1)), int(m.group(2))
        if (year, month) < (start_y, start_m) or (year, month) > (end_y, end_m):
            continue
        rows.append({
            'year': year, 'month': month,
            'taxable_sales': _pint(tds[1].text),
            'tax_free_sales': _pint(tds[2].text),
            'credit_card': _pint(tds[3].text),
            'cash_receipt': _pint(tds[4].text),
            'expense_proof': _pint(tds[6].text),
            'etc_amount': _pint(tds[5].text),  # 소득공제 (발행제외 tds[7]는 미저장)
        })
        log(f"  {period}: 과세={rows[-1]['taxable_sales']:,} 신카={rows[-1]['credit_card']:,}")
    return rows


def _save_rows(account, rows):
    """TaxVatMonthly delete-insert (login_id, year-month 기준 idempotent)."""
    from apps.cpc.models import TaxVatMonthly, TaxAccountMap
    if not rows:
        return 0
    amap = TaxAccountMap.objects.filter(platform='smartstore', login_id=account.login_id).first()
    biz = amap.business if amap else None
    seller_name = account.display_name or account.store_name or account.login_id
    objs = [
        TaxVatMonthly(
            business=biz, platform='smartstore', login_id=account.login_id,
            seller_name=seller_name, year=r['year'], month=r['month'],
            taxable_sales=r['taxable_sales'], tax_free_sales=r['tax_free_sales'],
            credit_card=r['credit_card'], cash_receipt=r['cash_receipt'],
            expense_proof=r['expense_proof'], etc_amount=r['etc_amount'],
        )
        for r in rows
    ]
    yms = {(r['year'], r['month']) for r in rows}
    for y, mo in yms:
        TaxVatMonthly.objects.filter(platform='smartstore', login_id=account.login_id, year=y, month=mo).delete()
    TaxVatMonthly.objects.bulk_create(objs, batch_size=200)
    return len(objs)


def crawl_one_vat(account, start_ym, end_ym, log_fn=None, save=True):
    """1계정 부가세신고내역 수집. 반환: rows(list) 또는 None(로그인/비번 없음)."""
    from .browser import create_driver, stop_display
    from .smartstore_crawler import login_smartstore, switch_store
    lid = account.login_id
    log = log_fn or (lambda m: logger.info(f'[smartstore-vat:{lid}] {m}'))

    if not account.login_pw:
        log("비밀번호 없음 — 건너뜀")
        return None

    driver = None
    try:
        driver = create_driver()
        if not login_smartstore(driver, lid, account.login_pw, log):
            log("로그인 실패")
            return None
        if account.store_slug:
            switch_store(driver, account.store_slug, log)

        all_rows = []
        for chunk_start, chunk_end in _half_year_chunks(start_ym, end_ym):
            if not _enter_vat_page(driver, log):
                continue
            if not _set_period_and_search(driver, chunk_start, chunk_end, log):
                continue
            rows = _parse_vat_table(driver, chunk_start, chunk_end, log)
            all_rows.extend(rows)
            time.sleep(random.uniform(1.5, 3))

        log(f"부가세 {len(all_rows)}개월 수집 (과세매출합 {sum(r['taxable_sales'] for r in all_rows):,})")
        if save:
            n = _save_rows(account, all_rows)
            log(f"{n}건 저장 완료")
        return all_rows
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        stop_display()


def run_vat_accounts(account_filter=None, start_ym=None, end_ym=None, log_fn=None, save=True):
    """스마트스토어 부가세 전 계정 수집 (사람처럼 페이싱)."""
    from apps.smartstore.models import SmartStoreAccount
    from django.utils import timezone
    log = log_fn or (lambda m: logger.info(m))

    now = timezone.localtime()
    start_ym = start_ym or f"{now.year}01"
    end_ym = end_ym or now.strftime("%Y%m")

    accounts = list(
        SmartStoreAccount.objects.filter(is_active=True).exclude(login_pw='')
        .order_by('display_order', 'id')
    )
    if account_filter:
        accounts = [a for a in accounts if a.login_id in account_filter]

    log(f"스마트스토어 부가세 수집 시작 — {len(accounts)}계정, {start_ym}~{end_ym}")
    collected, failed = 0, 0
    for i, acct in enumerate(accounts, 1):
        log(f"[{i}/{len(accounts)}] {acct.login_id} ({acct.display_name})")
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
            time.sleep(random.uniform(6, 11))

    result = {'collected': collected, 'failed': failed, 'total': len(accounts)}
    log(f"완료: {result}")
    return result

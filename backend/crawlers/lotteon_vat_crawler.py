"""롯데온 부가세신고자료 수집 — 판매자센터(store.lotteon.com) 정산관리 > 부가세신고자료조회 내부 API.

흐름(실측 검증 2026-07-10, rejoice234):
  1. store.lotteon.com 로그인 → "정산관리 > 부가세신고자료조회" 메뉴 진입 후 조회버튼을 눌러 발생하는
     XHR에서 Bearer 토큰을 추출. 토큰은 메뉴(화면) 단위로 스코프가 걸려있어 — 상품관리 메뉴에서 딴
     토큰으로 이 API를 호출하면 401(실측 확인, lotteon_product_crawler._login_and_get_token 재사용 불가) —
     반드시 이 화면에서 직접 토큰을 발급받아야 함.
  2. soapi.lotteon.com/settle/v1/so/vatPayment/selectVatPaymentList 를 requests로 GET
     (trNo=계정 seller_no, salesTypCd=all, fromDate/toDate=YYYYMMDD)
  3. 응답 필드(실측): pyYm(YYYYMM), salesTypCd/salesTypCdText(매출유형: "A"=중개 등),
     salesAmt(매출금액), csrcAmt(현금영수증), ccrdAmt(신용카드), mphnAmt(휴대폰), etcAmt(기타).
     11번가/지마켓/스마트스토어와 달리 과세/면세/영세 구분은 제공하지 않음 — salesAmt 합계를
     taxable_sales에 저장(tax_free/zero_rate는 0).
  4. 매출유형이 계정에 따라 복수(중개/직매입 등)일 수 있어 월별로 합산 후 TaxVatMonthly(platform='lotteon')
     저장 — 모델이 (platform, login_id, year, month) unique라 월당 1행만 허용.

안전: eleven_block_guard 통합 락(preflight), platform='lotteon'.
"""
import calendar
import logging
import random
import time

import requests
from django.utils import timezone

logger = logging.getLogger('crawler')

VAT_API_URL = 'https://soapi.lotteon.com/settle/v1/so/vatPayment/selectVatPaymentList'
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def _find_fill(driver, selectors, value):
    from selenium.webdriver.common.by import By
    for sel in selectors:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            els[0].clear()
            els[0].send_keys(value)
            return True
    return False


def _find_click(driver, selectors):
    from selenium.webdriver.common.by import By
    for sel in selectors:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            try:
                els[0].click()
            except Exception:
                driver.execute_script("arguments[0].click();", els[0])
            return True
    return False


def _login_and_get_vat_token(account, log_fn=None):
    """부가세신고자료조회 화면에 직접 진입해 그 화면 전용 Bearer 토큰을 반환.
    2FA 요구 시 None(사람 개입 필요 — 자동 처리하지 않음)."""
    import json
    import os
    import time
    os.environ.setdefault('DISPLAY', ':99')
    from crawlers.browser import create_driver

    profile_dir = f'/tmp/lotteon_profiles/{account.login_id}'
    for fn in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        try:
            os.remove(f'{profile_dir}/{fn}')
        except OSError:
            pass

    driver = create_driver(user_data_dir=profile_dir, kill_existing=False, enable_perf_log=True)
    try:
        driver.get('https://store.lotteon.com')
        time.sleep(3)
        if 'login' in driver.current_url.lower():
            _find_fill(driver, ['input[placeholder="사용자ID"]'], account.login_id)
            _find_fill(driver, ['input[type="password"]'], account.login_pw)
            _find_click(driver, ['.btn_login'])
            time.sleep(3)
            if 'login' in driver.current_url.lower():
                _log(log_fn, f'[lotteon-vat:{account.login_id}] 2FA 요구 — 자동화 불가, 스킵')
                return None

        driver.execute_script("""
            document.querySelectorAll('.w2window_close, [class*="btn_close"]').forEach(function(b){ try { b.click(); } catch(e){} });
            document.querySelectorAll('[class*="dim"], [class*="layer_dim"], .w2window').forEach(function(d){ try { d.remove(); } catch(e){} });
        """)
        time.sleep(1)

        # 정산관리 > 부가세신고자료조회
        driver.execute_script("""
            var el = document.getElementById('mf_wfm_menuBox_gen_1stMenu_5_btn_1stMenu');
            if (el) el.click();
        """)
        time.sleep(1.5)
        driver.execute_script("""
            var el = document.getElementById('mf_wfm_menuBox_gen_1stMenu_5_gen_2ndMenu_2_btn_2ndMenu');
            if (el) el.click();
        """)
        time.sleep(3)
        # "열려있는 모든 메뉴탭을 닫으시겠습니까?" 팝업 — 취소(현재 탭 유지)
        _find_click(driver, ['.dialog-block-buttons input[value="취소"]'])
        time.sleep(1.5)

        driver.get_log('performance')  # 버퍼 비움
        clicked = _find_click(driver, ['#mf_tac_layout_contents_ML000001776_body_btn_search'])
        if not clicked:
            _log(log_fn, f'[lotteon-vat:{account.login_id}] 조회버튼 못 찾음 — 화면 구조 변경 의심')
            return None
        time.sleep(3)

        token = None
        for entry in driver.get_log('performance'):
            try:
                msg = json.loads(entry['message'])['message']
                if msg.get('method') == 'Network.requestWillBeSent':
                    h = msg['params']['request'].get('headers', {})
                    if 'Authorization' in h:
                        token = h['Authorization']
            except Exception:
                pass
        if token:
            _log(log_fn, f'[lotteon-vat:{account.login_id}] 부가세 화면 토큰 확보')
        else:
            _log(log_fn, f'[lotteon-vat:{account.login_id}] 토큰 추출 실패')
        return token
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def _pnum(v):
    try:
        return int(round(float(v or 0)))
    except (TypeError, ValueError):
        return 0


def _fetch_vat_rows(token, tr_no, start_ym, end_ym, log_fn=None):
    last_day = calendar.monthrange(int(end_ym[:4]), int(end_ym[4:6]))[1]
    headers = {
        'Authorization': token,
        'Accept': 'application/json',
        'Referer': 'https://store.lotteon.com/',
        'User-Agent': _UA,
    }
    params = {
        'fromDate': f'{start_ym}01',
        'toDate': f'{end_ym}{last_day:02d}',
        'salesTypCd': 'all',
        'trNo': tr_no,
        'salesTypCdDtl': '',
        'seStdYm': '',
        'pageNo': 1,
        'rowsPerPage': 200,
    }
    resp = requests.get(VAT_API_URL, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get('returnCode') != 'SUCCESS':
        _log(log_fn, f'API 오류: {data.get("message")}')
        return []
    return data.get('data') or []


def _upsert_vat(account, rows, log_fn=None):
    from apps.cpc.models import TaxAccountMap, TaxVatMonthly
    if not rows:
        return 0

    monthly = {}
    for r in rows:
        ym = r.get('pyYm') or ''
        if len(ym) != 6:
            continue
        y, mo = int(ym[:4]), int(ym[4:6])
        agg = monthly.setdefault((y, mo), {
            'taxable_sales': 0, 'credit_card': 0, 'cash_receipt': 0,
            'mobile': 0, 'etc_amount': 0,
        })
        agg['taxable_sales'] += _pnum(r.get('salesAmt'))
        agg['credit_card'] += _pnum(r.get('ccrdAmt'))
        agg['cash_receipt'] += _pnum(r.get('csrcAmt'))
        agg['mobile'] += _pnum(r.get('mphnAmt'))
        agg['etc_amount'] += _pnum(r.get('etcAmt'))

    amap = TaxAccountMap.objects.filter(platform='lotteon', login_id=account.login_id).first()
    biz = amap.business if amap else None
    seller_name = account.store_name or account.login_id

    objs = [
        TaxVatMonthly(business=biz, platform='lotteon', login_id=account.login_id,
                       seller_name=seller_name, year=y, month=mo, **agg)
        for (y, mo), agg in monthly.items()
    ]
    for (y, mo) in monthly:
        TaxVatMonthly.objects.filter(platform='lotteon', login_id=account.login_id, year=y, month=mo).delete()
    TaxVatMonthly.objects.bulk_create(objs, batch_size=200)
    return len(objs)


def crawl_one_vat(account, start_ym, end_ym, log_fn=None, save=True):
    """1계정 부가세 수집. 반환: 저장(또는 조회)건수(int) / None(실패)."""
    lid = account.login_id
    if not account.seller_no:
        _log(log_fn, f'[lotteon-vat:{lid}] seller_no(trNo) 미설정 — 스킵')
        return None

    token = _login_and_get_vat_token(account, log_fn)
    if not token:
        _log(log_fn, f'[lotteon-vat:{lid}] 토큰 확보 실패(2FA 등) — 스킵')
        return None

    rows = _fetch_vat_rows(token, account.seller_no, start_ym, end_ym, log_fn)
    _log(log_fn, f'[lotteon-vat:{lid}] {len(rows)}행 수신')
    if not save:
        return len(rows)
    saved = _upsert_vat(account, rows, log_fn)
    _log(log_fn, f'[lotteon-vat:{lid}] {saved}개월 저장')
    return saved


def run_vat_accounts(account_filter=None, start_ym=None, end_ym=None, log_fn=None, save=True):
    """롯데온 부가세 전 계정 수집 (계정별 순차, 사람처럼 페이싱)."""
    from apps.cpc import eleven_block_guard as guard
    from apps.lotteon.models import LotteonAccount

    now = timezone.localtime()
    start_ym = start_ym or f'{now.year}01'
    end_ym = end_ym or now.strftime('%Y%m')

    ok, reason = guard.preflight('롯데온부가세수집', platform='lotteon')
    if not ok:
        _log(log_fn, f'사전점검 실패 — {reason}')
        return {'error': reason}

    try:
        accounts = list(LotteonAccount.objects.filter(is_active=True).order_by('display_order', 'id'))
        if account_filter:
            accounts = [a for a in accounts if a.login_id in account_filter]

        _log(log_fn, f'롯데온 부가세 수집 시작 — {len(accounts)}계정, {start_ym}~{end_ym}')
        collected, failed = 0, 0
        for i, acct in enumerate(accounts, 1):
            _log(log_fn, f'[{i}/{len(accounts)}] {acct.login_id} ({acct.store_name})')
            try:
                saved = crawl_one_vat(acct, start_ym, end_ym, log_fn=log_fn, save=save)
                if saved is None:
                    failed += 1
                else:
                    collected += 1
            except Exception as e:
                failed += 1
                _log(log_fn, f'{acct.login_id} 오류: {e}')
            if i < len(accounts):
                time.sleep(random.uniform(6, 11))
        result = {'collected': collected, 'failed': failed, 'total': len(accounts)}
        _log(log_fn, f'완료: {result}')
        return result
    finally:
        guard.release_global_lock(platform='lotteon')

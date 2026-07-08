"""롯데온 광고비/상품별광고비 수집 — 광고주센터(ad.lotteon.com) 클릭광고+스마트매출업 리포트.

store.lotteon.com(상품)과 달리 ad.lotteon.com은 Bearer 토큰이 아니라 **세션 쿠키** 인증이라
(실측 확인 2026-07-08: Authorization 헤더 없음, credentials 쿠키만) 브라우저를 계속 띄운 채
in-page fetch()로 호출한다(지마켓 크롤러와 동일 패턴).

흐름:
  1. store.lotteon.com 로그인 → "광고주센터" 클릭 → 새 창(ad.lotteon.com) 전환
     (SSO 토큰 핸드오프: soapi.../selleroffice/auto/SO/adVertEncriptToken)
  2. 날짜범위로 계정 레벨 일자별 리포트를 in-page fetch (클릭광고 + 스마트매출업 둘 다) → LotteonAdCost
  3. 상품별 리포트는 일 단위로 페이지네이션 호출 → LotteonProductAdCost

필드명 실측 확인(2026-07-08, tmxkql111/tmxkql222 — 2026년 6월 실제 광고집행 데이터로 검증):
  일자별 리포트 응답 필드는 sort 파라미터(BASIC_DATE 같은 대문자 스네이크=DB컬럼명)와 다르게
  camelCase다: basicDate, impCnt, clickCnt, adspend, sellQt(구매전환수), sellCost(구매전환금액),
  ctr, avgCpc, cvr, roas, cps. 예) {"basicDate":"20260627","impCnt":247,"clickCnt":5,"adspend":550,...}
  → LotteonAdCost는 이 필드명으로 매핑, 실데이터로 검증 완료.

  상품별 리포트(advSadRptItem)도 실데이터로 검증 완료(2026-06, tmxkql222 11,831건) — 필드는
  sellerItemNo, sellerItemName, categoryName, impCnt, clickCnt, adspend, sellQt, sellCost, ctr,
  avgImpRank, avgCpc, cvr, cps, roas. 상품별 cost 합계(275,297)가 같은 기간 일자별 합계와 정확히
  일치해 cost/click/impression 매핑 정확성 확인. advClickRptItem(클릭광고 상품별)은 3계정 모두
  클릭광고 미등록이라 실데이터로는 미검증(같은 엔진이라 동일 필드명일 것으로 추정, raw_json 보존).

안전: eleven_block_guard 통합 락(preflight), platform='lotteon'.
"""
import json
import logging
import time

from django.utils import timezone

logger = logging.getLogger('crawler')

MAIN_URL = 'https://store.lotteon.com'
CLICK_DAY_URL = 'https://ad.lotteon.com/advRpt/advClickRptDay/loadList'
CLICK_ITEM_URL = 'https://ad.lotteon.com/advRpt/advClickRptItem/loadList'
SAD_DAY_URL = 'https://ad.lotteon.com/advRpt/advSadRptDay/loadList'
SAD_ITEM_URL = 'https://ad.lotteon.com/advRpt/advSadRptItem/loadList'
ITEM_PAGE_SIZE = 200


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


# in-page fetch — ad.lotteon.com 내에서 실행되어야 세션 쿠키가 자동으로 실림.
_FETCH_JS = (
    "var cb=arguments[arguments.length-1];var url=arguments[0];var body=arguments[1];"
    "fetch(url,{method:'POST',credentials:'include',"
    "headers:{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',"
    "'X-Requested-With':'XMLHttpRequest'},body:body})"
    ".then(function(r){return r.text();}).then(function(t){cb(t);}).catch(function(e){cb('ERR:'+e);});"
)


def _login_and_open_adcenter(account, log_fn=None):
    """로그인 후 광고주센터(ad.lotteon.com) 창으로 전환한 driver를 반환. 2FA 필요 시 None."""
    import os
    os.environ.setdefault('DISPLAY', ':99')
    from crawlers.browser import create_driver

    profile_dir = f'/tmp/lotteon_profiles/{account.login_id}'
    for fn in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        try:
            os.remove(f'{profile_dir}/{fn}')
        except OSError:
            pass

    driver = create_driver(user_data_dir=profile_dir, kill_existing=False, enable_perf_log=False)
    driver.set_script_timeout(60)   # 대량 날짜범위 조회 시 기본 30초로는 부족(script timeout 발생 확인됨)
    driver.get(MAIN_URL)
    time.sleep(3)
    if 'login' in driver.current_url.lower():
        _find_fill(driver, ['input[placeholder="사용자ID"]'], account.login_id)
        _find_fill(driver, ['input[type="password"]'], account.login_pw)
        driver.execute_script("var b=document.querySelector('.btn_login'); if(b) b.click();")
        time.sleep(3)
        if 'login' in driver.current_url.lower():
            _log(log_fn, f'[lotteon-ad:{account.login_id}] 2FA 요구 — 자동화 불가, 스킵')
            driver.quit()
            return None

    time.sleep(1.5)
    driver.execute_script("""
        document.querySelectorAll('.w2window_close, [class*="btn_close"]').forEach(function(b){ try { b.click(); } catch(e){} });
        document.querySelectorAll('[class*="dim"], [class*="layer_dim"], .w2window').forEach(function(d){ try { d.remove(); } catch(e){} });
    """)
    time.sleep(1)

    before = driver.window_handles
    driver.execute_script("var el = document.getElementById('mf_wfm_menuBox_advenceBtn'); if (el) el.click();")
    time.sleep(4)
    after = driver.window_handles
    if len(after) > len(before):
        driver.switch_to.window([h for h in after if h not in before][0])
        time.sleep(2)

    # SSO 리다이렉트(adv/apiCommon/sso 등)가 끝나고 ad.lotteon.com/home에 안착할 때까지 대기
    for _ in range(20):
        if 'ad.lotteon.com' in driver.current_url and 'sso' not in driver.current_url.lower():
            break
        time.sleep(1)

    if 'ad.lotteon.com' not in driver.current_url:
        _log(log_fn, f'[lotteon-ad:{account.login_id}] 광고주센터 진입 실패 (URL={driver.current_url})')
        driver.quit()
        return None
    return driver


def _fetch_day_report(driver, url, start_date, end_date):
    """계정 레벨 일자별 광고 집계. start/end는 'YYYYMMDD' 문자열."""
    body = f'startDate={start_date}&endDate={end_date}&sort=BASIC_DATE,desc&page=0&size=200&isLast=true'
    raw = driver.execute_async_script(_FETCH_JS, url, body)
    if raw.startswith('ERR:'):
        raise RuntimeError(raw)
    return json.loads(raw)


def _fetch_item_report_page(driver, url, date_str, page):
    """상품별 광고 집계(단일일자, 페이지네이션). date_str='YYYYMMDD'."""
    body = (f'srchCtgrId=top&cDepth=1&startDate={date_str}&endDate={date_str}'
            f'&sort=SELLER_ITEM_NO,asc&page={page}&size={ITEM_PAGE_SIZE}&isLast=true')
    raw = driver.execute_async_script(_FETCH_JS, url, body)
    if raw.startswith('ERR:'):
        raise RuntimeError(raw)
    return json.loads(raw)


def _g(row, *keys, default=0):
    """여러 후보 키 이름으로 값 조회(필드명 안전망)."""
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return default


def _save_day_rows(account, rows, ad_type, log_fn=None):
    """실측 확인된 필드명 사용: basicDate, adspend, clickCnt, impCnt, sellQt, sellCost."""
    from apps.lotteon.models import LotteonAdCost
    saved = 0
    for r in rows:
        date_raw = _g(r, 'basicDate', 'BASIC_DATE', default=None)
        if not date_raw:
            continue
        date_str = str(date_raw)[:8]
        try:
            d = timezone.datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            continue
        LotteonAdCost.objects.update_or_create(
            account=account, date=d, ad_type=ad_type,
            defaults={
                'cost': _g(r, 'adspend', 'TOTAL_COST'),
                'click': _g(r, 'clickCnt', 'CLICK_CNT'),
                'impression': _g(r, 'impCnt', 'EXPOSURE_CNT'),
                'conversions': _g(r, 'sellQt', 'CV_CNT'),
                'conversion_amount': _g(r, 'sellCost', 'CV_AMT'),
                'raw_json': json.dumps(r, ensure_ascii=False),
            },
        )
        saved += 1
    return saved


def _save_item_rows(account, date_obj, rows, log_fn=None):
    """상품별 리포트 — camelCase 컨벤션 추정 매핑(일자별과 동일 엔진으로 추정, raw_json 안전망 병행)."""
    from apps.lotteon.models import LotteonProductAdCost
    objs = []
    for r in rows:
        item_no = str(_g(r, 'sellerItemNo', 'SELLER_ITEM_NO', default='') or '')
        if not item_no:
            continue
        objs.append(LotteonProductAdCost(
            account=account, date=date_obj, seller_item_no=item_no,
            product_name=str(_g(r, 'sellerItemName', 'sellerItemNm', default=''))[:500],
            category_name=str(_g(r, 'categoryName', 'ctgrNm', default=''))[:200],
            impressions=_g(r, 'impCnt', 'EXPOSURE_CNT'),
            clicks=_g(r, 'clickCnt', 'CLICK_CNT'),
            cost=_g(r, 'adspend', 'TOTAL_COST'),
            conversions=_g(r, 'sellQt', 'CV_CNT'),
            conversion_amount=_g(r, 'sellCost', 'CV_AMT'),
            raw_json=json.dumps(r, ensure_ascii=False),
        ))
    if not objs:
        return 0
    LotteonProductAdCost.objects.bulk_create(
        objs, update_conflicts=True,
        update_fields=['product_name', 'category_name', 'impressions', 'clicks',
                       'cost', 'conversions', 'conversion_amount', 'raw_json', 'collected_at'],
    )
    return len(objs)


def run_all_accounts(log_fn=None, account_filter=None, start_date=None, end_date=None):
    from apps.cpc import eleven_block_guard as guard
    from apps.lotteon.models import LotteonAccount
    from datetime import timedelta

    ok, reason = guard.preflight('롯데온광고비수집', platform='lotteon')
    if not ok:
        _log(log_fn, f'사전점검 실패 — {reason}')
        return {'error': reason}

    today = timezone.localdate()
    end_d = end_date or today
    start_d = start_date or (end_d - timedelta(days=6))   # 기본 최근 7일

    try:
        qs = LotteonAccount.objects.filter(is_active=True)
        if account_filter:
            qs = qs.filter(login_id__in=account_filter)

        results = []
        for account in qs:
            if not account.seller_no:
                _log(log_fn, f'[lotteon-ad:{account.login_id}] seller_no 미설정 — 스킵')
                results.append({'login_id': account.login_id, 'error': 'seller_no 미설정'})
                continue
            driver = None
            try:
                driver = _login_and_open_adcenter(account, log_fn)
                if not driver:
                    results.append({'login_id': account.login_id, 'error': '광고주센터 진입 실패(2FA 등)'})
                    continue

                # 일자별 리포트 — 서버 부하/타임아웃 방지 위해 월 단위로 나눠 호출(큰 범위 한번에 요청 시 script timeout 발생 확인됨)
                day_saved = 0
                m_start = start_d.replace(day=1)
                while m_start <= end_d:
                    if m_start.month == 12:
                        m_end = m_start.replace(year=m_start.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)
                    chunk_start = max(m_start, start_d)
                    chunk_end = min(m_end, end_d)
                    sd, ed = chunk_start.strftime('%Y%m%d'), chunk_end.strftime('%Y%m%d')
                    for label, url in (('CLICK', CLICK_DAY_URL), ('SMART_SALE', SAD_DAY_URL)):
                        data = _fetch_day_report(driver, url, sd, ed)
                        rows = (data.get('message') or {}).get('content') or []
                        day_saved += _save_day_rows(account, rows, label, log_fn)
                        time.sleep(1)
                    m_start = m_end + timedelta(days=1)

                item_saved_total = 0
                d = start_d
                while d <= end_d:
                    ds = d.strftime('%Y%m%d')
                    for url in (CLICK_ITEM_URL, SAD_ITEM_URL):
                        page = 0
                        while True:
                            data = _fetch_item_report_page(driver, url, ds, page)
                            msg = data.get('message') or {}
                            rows = msg.get('content') or []
                            if not rows:
                                break
                            item_saved_total += _save_item_rows(account, d, rows, log_fn)
                            if len(rows) < ITEM_PAGE_SIZE:
                                break
                            page += 1
                            time.sleep(0.5)
                        time.sleep(0.5)
                    d += timedelta(days=1)
                    time.sleep(0.8)   # 일자간 페이싱(사람처럼) — 장기간 크롤 시 과도한 연속호출 방지

                _log(log_fn, f'[lotteon-ad:{account.login_id}] 완료 — 일자별 {day_saved}건, 상품별 {item_saved_total}건')
                results.append({'login_id': account.login_id, 'day_saved': day_saved, 'item_saved': item_saved_total})
            except Exception as e:
                logger.exception('lotteon ad crawl error')
                _log(log_fn, f'[lotteon-ad:{account.login_id}] 오류 — {e}')
                results.append({'login_id': account.login_id, 'error': str(e)})
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
            time.sleep(3)
        return {'results': results}
    finally:
        guard.release_global_lock(platform='lotteon')

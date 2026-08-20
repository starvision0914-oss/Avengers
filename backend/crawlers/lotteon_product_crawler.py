"""롯데온 나의 상품 수집 — 판매자센터(store.lotteon.com) 세션 Bearer 토큰 방식.

흐름(실측 검증 2026-07-08, rejoice234):
  1. store.lotteon.com 로그인(쿠키 프로필 재사용 — 2FA는 최초 1회, 이후 동일기기 인식으로 스킵됨)
  2. 로그인 후 페이지가 자동으로 쏘는 XHR들의 성능로그에서 Authorization: Bearer 토큰을 추출
     (세션스코프 토큰 — Origin/Referer만 맞으면 쿠키 없이도 그대로 API 호출 가능, 실측 확인됨)
  3. 브라우저는 닫고 requests로 soapi.lotteon.com/soapi/v1/product/information/selectProductList 를
     pageNo 증가시키며 페이지네이션 호출 → 전체 상품 수집
  4. (account, pd_no) unique로 LotteonMyProduct upsert

공식 오픈API(계정별 발급된 인증키)는 soapi 내부API와 인증 스킴이 달라 별도 문서 없이는 사용 불가(403→401만
확인, 정확한 헤더 포맷 미상) — 이 크롤러는 공식 API 없이 세션 토큰만으로 동작한다.

안전: eleven_block_guard 통합 락(preflight), platform='lotteon'.
"""
import json
import logging
import time

import requests
from django.utils import timezone

logger = logging.getLogger('crawler')

MAIN_URL = 'https://store.lotteon.com'
API_URL = 'https://soapi.lotteon.com/soapi/v1/product/information/selectProductList'
PAGE_SIZE = 100
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

_BASE_PAYLOAD = {
    "spdNo": "", "pdNo": "", "epdNo": "", "spdNm": "", "pdNm": "",
    "regDttmStrt": "19900101", "regDttmEnd": "29991231",
    "slStrtDttmStrt": "", "slStrtDttmEnd": "", "sitmNo": "", "mdlNo": "",
    "trNo": "", "brdNo": "", "pdTypCd": "", "scatNo": "", "dvProcTypCd": "",
    "lfDcatNo": "", "trGrpCd": "", "ctrtTypCd": "", "slStatCd": "",
    "dpYn": "", "wimgYn": "", "dvPdTypCd": "", "prcCmprEpsrYn": "",
    "dealPdYn": "", "sensInfoAprvStatCd": "", "dvRsvDvsCd": "", "slTypCd": "",
    "prcCompDvsCd": "", "fnlAprvYn": "", "bndlYn": "", "lrtrNo": "", "cmNo": "",
    "purTrNo": "", "purLrtrNo": "", "pdAprvReqCd": "", "sitmTrNo": "",
    "sitmLrtrNo": "", "pageNo": 1, "rowsPerPage": str(PAGE_SIZE),
    "thdyPdYn": "", "stffEusePdYn": "", "slEndPerd": "", "dlcrtYn": "",
}


def _log(log_fn, m):
    logger.info(m)
    if log_fn:
        log_fn(m)


def _find_click(driver, selectors, by_css=True):
    from selenium.webdriver.common.by import By
    for sel in selectors:
        els = driver.find_elements(By.CSS_SELECTOR if by_css else By.XPATH, sel)
        if els:
            try:
                els[0].click()
            except Exception:
                driver.execute_script("arguments[0].click();", els[0])
            return True
    return False


def _find_fill(driver, selectors, value):
    from selenium.webdriver.common.by import By
    for sel in selectors:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            els[0].clear()
            els[0].send_keys(value)
            return True
    return False


def _extract_bearer_token(driver, log_fn=None):
    """로그인 후 발생하는 네트워크 로그에서 Authorization: Bearer 토큰을 추출.
    performance 로그가 비활성이면 None(호출부에서 2FA 대기 등으로 폴백 처리)."""
    try:
        logs = driver.get_log('performance')
    except Exception as e:
        _log(log_fn, f'perf 로그 조회 실패: {e}')
        return None
    for entry in logs:
        try:
            msg = json.loads(entry['message'])['message']
        except Exception:
            continue
        if msg.get('method') != 'Network.requestWillBeSent':
            continue
        headers = msg['params']['request'].get('headers', {})
        auth = headers.get('Authorization') or headers.get('authorization')
        if auth and auth.startswith('Bearer '):
            return auth[len('Bearer '):]
    return None


def _login_and_get_token(account, log_fn=None):
    """계정 프로필로 로그인(쿠키 재사용, 필요 시 폼 로그인) 후 세션 Bearer 토큰을 반환.
    2FA 요구 시 None 반환(사람 개입 필요 — 이 크롤러는 자동 처리하지 않음)."""
    import os
    os.environ.setdefault('DISPLAY', ':99')
    from crawlers.browser import create_driver

    profile_dir = f'/tmp/lotteon_profiles/{account.login_id}'
    # 이전 실행이 비정상 종료해 남긴 Singleton 락 정리
    for fn in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        p = f'{profile_dir}/{fn}'
        try:
            os.remove(p)
        except OSError:
            pass

    driver = create_driver(user_data_dir=profile_dir, kill_existing=False, enable_perf_log=True)
    try:
        driver.get(MAIN_URL)
        time.sleep(3)
        if 'login' in driver.current_url.lower():
            _find_fill(driver, ['input[placeholder="사용자ID"]'], account.login_id)
            _find_fill(driver, ['input[type="password"]'], account.login_pw)
            driver.execute_script("var b=document.querySelector('.btn_login'); if(b) b.click();")
            time.sleep(3)
            if 'login' in driver.current_url.lower():
                _log(log_fn, f'[lotteon:{account.login_id}] 2FA 요구 — 자동화 불가, 스킵')
                return None

        time.sleep(1.5)
        # 공지 팝업 등 오버레이 제거 (없어도 무해)
        driver.execute_script("""
            document.querySelectorAll('.w2window_close, [class*="btn_close"]').forEach(function(b){ try { b.click(); } catch(e){} });
            document.querySelectorAll('[class*="dim"], [class*="layer_dim"], .w2window').forEach(function(d){ try { d.remove(); } catch(e){} });
        """)
        time.sleep(1)
        driver.get_log('performance')   # 버퍼 비움

        # 상품관리 → 상품 조회/수정 진입 시 selectProductList 호출이 발생 → 그때의 Bearer를 잡음
        driver.execute_script("""
            var el = document.getElementById('mf_wfm_menuBox_gen_1stMenu_1_btn_1stMenu');
            if (el) el.click();
        """)
        time.sleep(1.5)
        driver.execute_script("""
            var el = document.getElementById('mf_wfm_menuBox_gen_1stMenu_1_gen_2ndMenu_3_btn_2ndMenu');
            if (el) el.click();
        """)
        time.sleep(4)

        token = _extract_bearer_token(driver, log_fn)
        if token:
            _log(log_fn, f'[lotteon:{account.login_id}] 세션 토큰 확보')
        else:
            _log(log_fn, f'[lotteon:{account.login_id}] 세션 토큰 추출 실패')
        return token
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def _fetch_all_products(token, tr_no, log_fn=None):
    """토큰+trNo로 전체 상품(모든 판매상태) 페이지네이션 수집."""
    headers = {
        'Content-Type': 'application/json; charset="UTF-8"',
        'Accept': 'application/json',
        'Origin': MAIN_URL,
        'Referer': f'{MAIN_URL}/',
        'User-Agent': _UA,
        'Authorization': f'Bearer {token}',
    }
    items = []
    page = 1
    while True:
        payload = dict(_BASE_PAYLOAD, trNo=tr_no, pageNo=page)
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            _log(log_fn, f'페이지 {page} 요청 실패 HTTP {resp.status_code}')
            break
        data = resp.json()
        rows = data.get('data') or []
        if not rows:
            break
        items.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.5)   # 과도한 연속호출 방지(사람같은 페이싱)
    return items


def _upsert_products(account, rows, log_fn=None):
    from apps.lotteon.models import LotteonMyProduct
    now = timezone.now()
    objs = []
    for r in rows:
        pd_no = r.get('pdNo') or r.get('spdNo')
        if not pd_no:
            continue
        objs.append(LotteonMyProduct(
            account=account,
            pd_no=str(pd_no),
            product_name=(r.get('pdNm') or '')[:500],
            sale_price=r.get('slPrc') or 0,
            status_code=r.get('slStatCd') or '',
            seller_product_code=str(r.get('epdNo') or ''),
            category_path=(r.get('dcatNmPath') or '')[:300],
            synced_at=now,
        ))
    if not objs:
        return 0
    LotteonMyProduct.objects.bulk_create(
        objs, update_conflicts=True,
        update_fields=['product_name', 'sale_price', 'status_code', 'seller_product_code', 'category_path', 'synced_at'],
    )
    return len(objs)


def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc import eleven_block_guard as guard
    from apps.lotteon.models import LotteonAccount

    ok, reason = guard.preflight('롯데온상품수집', platform='lotteon')
    if not ok:
        _log(log_fn, f'사전점검 실패 — {reason}')
        return {'error': reason}

    try:
        qs = LotteonAccount.objects.filter(is_active=True)
        if account_filter:
            qs = qs.filter(login_id__in=account_filter)

        results = []
        for account in qs:
            if not account.seller_no:
                _log(log_fn, f'[lotteon:{account.login_id}] seller_no(trNo) 미설정 — 스킵')
                results.append({'login_id': account.login_id, 'error': 'seller_no 미설정'})
                continue
            try:
                token = _login_and_get_token(account, log_fn)
                if not token:
                    results.append({'login_id': account.login_id, 'error': '토큰 확보 실패(2FA 등)'})
                    continue
                rows = _fetch_all_products(token, account.seller_no, log_fn)
                saved = _upsert_products(account, rows, log_fn)
                account.last_crawled_at = timezone.now()
                account.fail_count = 0
                account.save(update_fields=['last_crawled_at', 'fail_count'])
                _log(log_fn, f'[lotteon:{account.login_id}] 완료 — {saved}개 상품')
                results.append({'login_id': account.login_id, 'saved': saved})
            except Exception as e:
                logger.exception('lotteon crawl error')
                account.fail_count = (account.fail_count or 0) + 1
                account.save(update_fields=['fail_count'])
                _log(log_fn, f'[lotteon:{account.login_id}] 오류 — {e}')
                results.append({'login_id': account.login_id, 'error': str(e)})
            time.sleep(3)   # 계정 간 페이싱
        return {'results': results}
    finally:
        guard.release_global_lock(platform='lotteon')

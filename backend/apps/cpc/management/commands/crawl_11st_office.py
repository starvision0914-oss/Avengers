"""11번가 셀러오피스 메인 페이지 크롤러 - 14항목 수집"""
import os
import random
import sys
import time
import traceback
from datetime import datetime

# 차단 회피 보수적 페이싱
INTER_ACCOUNT_SLEEP = (30.0, 90.0)
CIRCUIT_BREAKER_THRESHOLD = 5
SKIP_RECENT_HOURS = 6
MAX_CONNECT_ATTEMPTS = 3  # 계정당 접속 최대 3회 시도, 3회 실패 시 중지→다음 계정

from django.core.management.base import BaseCommand
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Avengers backend root
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, BACKEND_ROOT)

from crawlers.browser import create_driver, stop_display
from crawlers.eleven_crawler import _do_login

from apps.cpc.models import CrawlerAccount, ElevenSellerOfficeStat
from apps.cpc import eleven_block_guard as guard

LOG_PATH = '/tmp/cron_11st_office.log'
LOCKFILE = '/tmp/avengers_crawl_chrome.lock'

XPATHS = {
    'cash':         '//*[@id="soContent"]/div[2]/div/div[4]/div[4]/div/div[2]/ul/li[1]/div[2]/a',
    'point':        '//*[@id="soContent"]/div[2]/div/div[4]/div[4]/div/div[2]/ul/li[2]/div[2]/a',
    'ad':           '//*[@id="soContent"]/div[2]/div/div[8]/div[2]/div/div[2]/div[2]/ul/li[1]/span[2]/a',
    'product_limit':'//*[@id="soContent"]/div[2]/div/div[8]/div[1]/div/div[2]/ul/li[5]/div/span[2]/a',
    'products':     '//*[@id="soContent"]/div[2]/div/div[8]/div[1]/div/div[2]/ul/li[1]/div/span[2]/a',
    'banned':       '//*[@id="soContent"]/div[2]/div/div[8]/div[1]/div/div[2]/ul/li[2]/div/span[2]/a',
    'overdue':      '//*[@id="soContent"]/div[2]/div/div[3]/div/div/div[2]/ul/li[3]/div[2]/a',
    'undelivered':  '//*[@id="soContent"]/div[2]/div/div[3]/div/div/div[2]/ul/li[4]/div[2]/a',
    'fulfillment':  '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[1]/div[2]/span[1]',
    'shipping':     '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[2]/div[2]/span[1]',
    'inquiry':      '//*[@id="soContent"]/div[2]/div/div[4]/div[1]/div/ul[1]/li[3]/div[2]/span[1]',
}
DRAFT_MENU_PARENT = '//*[@id="app"]/div/div[2]/div/div[1]/div/ul/li[2]/button'
DRAFT_MENU_ITEM = '//*[@id="app"]/div/div[2]/div/div[1]/div/ul/li[2]/ul/li[10]/a'
DRAFT_XPATH = '//*[@id="row0dataGrid"]/div[8]/div'


def _log(msg):
    line = f'[{datetime.now().strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _parse_int(text):
    if not text:
        return 0
    try:
        return int(''.join(c for c in str(text) if c.isdigit()))
    except Exception:
        return 0


def _get_text(driver, xpath, timeout=7):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return (el.text or '').strip()
    except Exception:
        return ''


def _click(driver, xpath, timeout=10):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.6)
        el.click()
        return True
    except Exception:
        return False


def _collect_one(driver, account):
    """한 계정에 대한 14개 항목 수집"""
    data = {k: 0 for k in (
        'cash', 'point', 'ad_balance', 'product_limit', 'products', 'banned',
        'available', 'overdue', 'undelivered', 'draft',
    )}
    data['fulfillment'] = data['shipping'] = data['inquiry'] = ''

    # 메인 페이지 이동 (이미 로그인된 상태)
    driver.get('https://soffice.11st.co.kr/view/main')
    time.sleep(3)

    # 스크롤 70% 아래로
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
    time.sleep(1)

    data['cash'] = _parse_int(_get_text(driver, XPATHS['cash']))
    data['point'] = _parse_int(_get_text(driver, XPATHS['point']))
    data['ad_balance'] = _parse_int(_get_text(driver, XPATHS['ad']))

    # 맨 위로
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    data['product_limit'] = _parse_int(_get_text(driver, XPATHS['product_limit']))
    data['products'] = _parse_int(_get_text(driver, XPATHS['products']))
    data['banned'] = _parse_int(_get_text(driver, XPATHS['banned']))
    data['available'] = max(data['product_limit'] - data['products'], 0)
    data['overdue'] = _parse_int(_get_text(driver, XPATHS['overdue']))
    data['undelivered'] = _parse_int(_get_text(driver, XPATHS['undelivered']))
    data['fulfillment'] = _get_text(driver, XPATHS['fulfillment'])[:50]
    data['shipping'] = _get_text(driver, XPATHS['shipping'])[:50]
    data['inquiry'] = _get_text(driver, XPATHS['inquiry'])[:50]

    # 가송장 (좌측 메뉴 → iframe)
    try:
        if _click(driver, DRAFT_MENU_PARENT, timeout=6):
            time.sleep(0.5)
            _click(driver, DRAFT_MENU_ITEM, timeout=6)
            time.sleep(2)
            iframe = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            driver.switch_to.frame(iframe)
            data['draft'] = _parse_int(_get_text(driver, DRAFT_XPATH, timeout=6))
            driver.switch_to.default_content()
    except Exception as e:
        _log(f'  [draft] 수집 실패: {e}')
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

    return data


class Command(BaseCommand):
    help = '11번가 셀러오피스 메인 페이지 14항목 수집 (잔액/상품/경고)'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', type=int, default=None)
        parser.add_argument('--all-focused', action='store_true')
        parser.add_argument('--accounts', type=str, default='', help='comma-separated ids')

    def handle(self, *args, **opts):
        # chrome lock
        if os.path.exists(LOCKFILE):
            try:
                with open(LOCKFILE) as f:
                    pid = int((f.read() or '0').strip())
                if pid:
                    try:
                        os.kill(pid, 0)
                        _log(f'다른 크롤러 실행 중 (PID={pid}) — 스킵')
                        return
                    except OSError:
                        pass
            except Exception:
                pass
        with open(LOCKFILE, 'w') as f:
            f.write(str(os.getpid()))

        try:
            # 글로벌 차단 락 확인
            if guard.guard_and_skip('office crawler'):
                _log('⛔ 11번가 글로벌 차단 모드 — office 크롤러 스킵')
                return

            qs = CrawlerAccount.objects.filter(platform='11st')
            if opts.get('account_id'):
                qs = qs.filter(id=opts['account_id'])
            elif opts.get('accounts'):
                ids = [int(x) for x in opts['accounts'].split(',') if x.strip()]
                qs = qs.filter(id__in=ids)
            elif opts.get('all_focused'):
                qs = qs.filter(is_focused=True)
            else:
                qs = qs.filter(is_focused=True)

            all_accounts = list(qs.order_by('display_order', 'login_id'))

            # 신선도 필터 — 최근 SKIP_RECENT_HOURS 시간 내 정상 수집한 계정 스킵
            # (단, --account-id 명시 시는 강제 실행)
            skipped_recent = []
            if not opts.get('account_id'):
                # 가장 최근 성공(error='') 수집 시각으로 판단
                from django.db.models import Max
                last_ok = {
                    x['account_id']: x['last_ok']
                    for x in ElevenSellerOfficeStat.objects
                        .filter(error='')
                        .values('account_id')
                        .annotate(last_ok=Max('collected_at'))
                }
                accounts = []
                for a in all_accounts:
                    if guard.is_recently_synced(last_ok.get(a.id), hours=SKIP_RECENT_HOURS):
                        skipped_recent.append(a.login_id)
                    else:
                        accounts.append(a)
            else:
                accounts = all_accounts

            total = len(accounts)
            _log(f'==== 11번가 셀러오피스 수집 시작 ({total}계정, 최근 {SKIP_RECENT_HOURS}h 스킵 {len(skipped_recent)}) ====')

            driver = None
            ok_count = 0
            fail_count = 0
            consecutive_block = 0
            aborted_due_to_block = False

            for idx, acct in enumerate(accounts, 1):
                # 매 계정 시작 전 글로벌 락 체크
                if guard.guard_and_skip(f'office[{acct.login_id}]'):
                    aborted_due_to_block = True
                    break

                if acct.crawling_status == '실패':
                    _log(f'[{idx}/{total}] {acct.login_id} 실패 상태 - 건너뜀')
                    continue

                # ── 접속(로그인) 단계: 최대 3회 시도. 3회 실패 시 중지→다음 계정 ──
                logged_in = False
                for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
                    if guard.guard_and_skip(f'office[{acct.login_id}] 접속'):
                        aborted_due_to_block = True
                        break
                    try:
                        if driver is None:
                            driver = create_driver()
                        _log(f'[{idx}/{total}] {acct.login_id} ({acct.seller_name}) - 로그인 {attempt}/{MAX_CONNECT_ATTEMPTS}...')
                        if _do_login(driver, acct.login_id, acct.password_enc or ''):
                            logged_in = True
                            break
                        raise RuntimeError('로그인 실패')
                    except Exception as le:
                        _log(f'  접속 실패 {attempt}/{MAX_CONNECT_ATTEMPTS}: {str(le)[:120]}')
                        if guard.is_block_signal(le):
                            consecutive_block += 1
                            _log(f'  차단신호 ({consecutive_block}/{CIRCUIT_BREAKER_THRESHOLD})')
                            if consecutive_block >= CIRCUIT_BREAKER_THRESHOLD:
                                guard.report_signal(le, source='office crawler')
                                aborted_due_to_block = True
                                _log('  ⛔ circuit breaker → 글로벌 락, 중단')
                                break
                        if 'invalid session id' in str(le).lower() or 'no such window' in str(le).lower():
                            try: driver.quit()
                            except Exception: pass
                            driver = None
                        if attempt < MAX_CONNECT_ATTEMPTS:
                            time.sleep(random.uniform(2.0, 4.0))

                if aborted_due_to_block:
                    break

                if not logged_in:
                    # ── 접속 3회 실패 → 반드시 중지하고 다음 계정으로 ──
                    fail_count += 1
                    acct.fail_count = (acct.fail_count or 0) + 1
                    acct.save(update_fields=['fail_count'])
                    acct.mark_connect_failed()
                    ElevenSellerOfficeStat.objects.create(
                        account=acct,
                        error=f'접속 {MAX_CONNECT_ATTEMPTS}회 실패 → 중지(다음 계정), 상태={acct.crawling_status}'[:1000])
                    _log(f'  ⛔ 접속 {MAX_CONNECT_ATTEMPTS}회 실패 — 다음 계정 (상태={acct.crawling_status})')
                    try:
                        guard._send_telegram_alert(
                            f'⚠️ [11번가 오피스 접속실패]\n계정: {acct.login_id} ({acct.seller_name})\n'
                            f'접속 {MAX_CONNECT_ATTEMPTS}회 연속 실패 → 다음 계정. 상태: {acct.crawling_status}')
                    except Exception:
                        pass
                    if idx < total:
                        time.sleep(random.uniform(*INTER_ACCOUNT_SLEEP))
                    continue

                # ── 접속 성공 → 수집 ──
                consecutive_block = 0
                acct.reset_connect_fail()
                try:
                    data = _collect_one(driver, acct)
                    ElevenSellerOfficeStat.objects.create(account=acct, **data)
                    ok_count += 1
                    _log(f'  OK cash={data["cash"]:,} point={data["point"]:,} ad={data["ad_balance"]:,} '
                         f'limit={data["product_limit"]:,} sale={data["products"]:,} '
                         f'avail={data["available"]:,} draft={data["draft"]} '
                         f'overdue={data["overdue"]} undeliv={data["undelivered"]} '
                         f'/ {data["fulfillment"]}/{data["shipping"]}/{data["inquiry"]}')
                    acct.last_crawled_at = timezone.now()
                    acct.save(update_fields=['last_crawled_at'])
                except Exception as e:
                    fail_count += 1
                    err = traceback.format_exc()[-1500:]
                    _log(f'  수집 FAIL: {e}')
                    ElevenSellerOfficeStat.objects.create(
                        account=acct, error=f'{e}\n{err}'[:5000])
                    try:
                        guard._send_telegram_alert(
                            f'⚠️ [11번가 오피스 수집오류]\n계정: {acct.login_id} ({acct.seller_name})\n{str(e)[:150]}')
                    except Exception:
                        pass

                    # 차단 신호 — circuit breaker
                    if guard.is_block_signal(e):
                        consecutive_block += 1
                        _log(f'  차단신호 ({consecutive_block}/{CIRCUIT_BREAKER_THRESHOLD})')
                        if consecutive_block >= CIRCUIT_BREAKER_THRESHOLD:
                            guard.report_signal(e, source='office crawler')
                            aborted_due_to_block = True
                            _log('  ⛔ circuit breaker → 글로벌 락, 중단')
                            break

                    # driver 죽은 경우 재생성
                    if 'invalid session id' in str(e).lower() or 'no such window' in str(e).lower():
                        try: driver.quit()
                        except Exception: pass
                        driver = None

                # 다음 계정 전에 쿠키/세션 정리
                try:
                    driver.delete_all_cookies()
                except Exception:
                    pass

                # 마지막 계정이 아니면 사람처럼 잠시 대기
                if idx < total:
                    wait = random.uniform(*INTER_ACCOUNT_SLEEP)
                    _log(f'  → 다음 계정까지 {wait:.1f}s 대기')
                    time.sleep(wait)

            if driver:
                try: driver.quit()
                except Exception: pass
            stop_display()

            suffix = ' (차단신호로 조기 중단)' if aborted_due_to_block else ''
            _log(f'==== 완료: 성공 {ok_count} / 실패 {fail_count}{suffix} ====')
        finally:
            try: os.unlink(LOCKFILE)
            except Exception: pass

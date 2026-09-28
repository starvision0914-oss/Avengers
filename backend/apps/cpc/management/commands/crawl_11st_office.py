"""11번가 셀러오피스 메인 페이지 수집 — 셀러캐시/셀러포인트/상품수/AI캠페인 상태 (전계정 일 1회 크론용).

2026-09-28 재작성: 예전엔 절대경로 XPath(개편으로 깨짐)로 값을 읽고 is_focused 계정만 대상이라
비활성/비집중 계정(예: dlrmsgh7941 — 실제 셀러포인트 100,000P인데 8/21 이후 수집이 없어 0으로 표시)이
옛값 그대로 묵었다. 이제 eleven_crawler._collect_office(라벨 기반)를 그대로 재사용하고 --all 로
비활성 포함 전계정을 돈다. 쿠키 로그인 우선(OTP 최소화), 통합 전역락(preflight) 사용.

AI캠페인 열(ai_campaign)은 메인페이지 배너 버튼 문구를 그대로 저장한다:
  '알아서 해주는 AI캠페인 시작' / '1주 무료! 지금 광고 시작' / '지금 AI캠페인 ON으로 설정 변경' 등.
"""
import random
import time
import traceback
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as ec

from apps.cpc.models import CrawlerAccount, ElevenSellerOfficeStat
from apps.cpc import eleven_block_guard as guard

LOG_PATH = '/tmp/cron_11st_office.log'
INTER_ACCOUNT_SLEEP = (5.0, 10.0)   # 광고비 크롤과 동일 페이싱
CIRCUIT_BREAKER_THRESHOLD = 5       # 연속 접속실패 5회 → 중단 + 글로벌 차단
SKIP_RECENT_HOURS = 6
MAX_CONNECT_ATTEMPTS = 3            # 계정당 접속 최대 3회, 실패 시 중지→다음 계정


def _log(msg):
    line = f'[{datetime.now().strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _safe_quit(d):
    try:
        d and d.quit()
    except Exception:
        pass


def _new_driver(kill_existing=True):
    d = create_driver(kill_existing=kill_existing)
    try:
        d.implicitly_wait(0)   # _get_text 가 명시 대기를 쓰므로 암묵대기 제거(헛대기 방지)
    except Exception:
        pass
    return d


class Command(BaseCommand):
    help = '11번가 셀러오피스 현황(캐시/포인트/상품수/AI캠페인 상태) 수집'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='비활성 포함 전계정 (기본: 활성 계정만)')
        parser.add_argument('--account-id', type=int, default=None)
        parser.add_argument('--accounts', type=str, default='', help='comma-separated login_id')
        parser.add_argument('--force', action='store_true', help='최근 수집분도 재수집')
        parser.add_argument('--scheduled', action='store_true', help='크론용: 다른 11번가 크롤이 락 잡고 있으면 대기')

    def handle(self, *args, **opts):
        ok, reason = guard.preflight('오피스현황', wait=opts['scheduled'])
        if not ok:
            _log(f'⏭️ 건너뜀 — {reason}')
            if opts['scheduled']:
                guard.notify_problem('11번가오피스현황', f'예약 수집 미실행 — {reason}')
            return

        driver = None
        try:
            qs = CrawlerAccount.objects.filter(platform='11st').exclude(crawling_status='차단됨')
            if opts['account_id']:
                qs = qs.filter(id=opts['account_id'])
            elif opts['accounts']:
                qs = qs.filter(login_id__in=[x.strip() for x in opts['accounts'].split(',') if x.strip()])
            elif not opts['all']:
                qs = qs.filter(is_active=True)
            accounts = list(qs.order_by('display_order', 'login_id'))

            explicit = bool(opts['account_id'] or opts['accounts'] or opts['force'])
            if not explicit:
                from django.db.models import Max
                last_ok = {x['account_id']: x['m'] for x in ElevenSellerOfficeStat.objects
                           .filter(error='').values('account_id').annotate(m=Max('collected_at'))}
                accounts = [a for a in accounts
                            if not guard.is_recently_synced(last_ok.get(a.id), hours=SKIP_RECENT_HOURS)]

            total = len(accounts)
            _log(f'==== 11번가 오피스현황 수집 시작 ({total}계정) ====')
            ok_count = fail_count = consec_fail = 0

            for idx, acct in enumerate(accounts, 1):
                if guard.guard_and_skip(f'office[{acct.login_id}]'):
                    _log('⛔ 글로벌 차단 모드 — 중단')
                    break
                if consec_fail >= CIRCUIT_BREAKER_THRESHOLD:
                    guard.set_blocked(30, f'오피스수집 연속 {CIRCUIT_BREAKER_THRESHOLD}회 접속실패')
                    _log('⛔ 연속 접속실패 — 글로벌 차단 설정, 중단')
                    break

                login_id = acct.login_id
                _safe_quit(driver)
                driver = _new_driver(kill_existing=(idx == 1))

                logged_in = False
                for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
                    try:
                        if attempt == 1:
                            ck = ec._try_cookie_login(driver, acct)
                            if ck:
                                logged_in = True
                                break
                        try:
                            driver.get('about:blank')
                            driver.delete_all_cookies()
                        except Exception:
                            pass
                        _log(f'[{idx}/{total}] {login_id} ({acct.seller_name}) 로그인 {attempt}/{MAX_CONNECT_ATTEMPTS}')
                        if ec._do_login(driver, login_id, acct.password_enc or ''):
                            logged_in = True
                            break
                        raise RuntimeError('로그인 실패')
                    except Exception as le:
                        _log(f'  접속 실패 {attempt}/{MAX_CONNECT_ATTEMPTS}: {str(le)[:120]}')
                        if attempt < MAX_CONNECT_ATTEMPTS:
                            time.sleep(random.uniform(2.0, 4.0))

                if not logged_in:
                    consec_fail += 1
                    fail_count += 1
                    ElevenSellerOfficeStat.objects.create(
                        account=acct, error=f'접속 {MAX_CONNECT_ATTEMPTS}회 실패 → 중지(다음 계정)'[:1000])
                    _log(f'  ⛔ 접속 {MAX_CONNECT_ATTEMPTS}회 실패 — 다음 계정')
                else:
                    consec_fail = 0
                    try:
                        ec._save_cookies(driver, acct)
                        data = ec._collect_office(driver, login_id)
                        ElevenSellerOfficeStat.objects.create(account=acct, **data)
                        acct.last_crawled_at = timezone.now()
                        acct.save(update_fields=['last_crawled_at'])
                        ok_count += 1
                        _log(f'  OK cash={data["cash"]:,} point={data["point"]:,} sale={data["products"]:,} '
                             f'limit={data["product_limit"]:,} / AI캠페인="{data["ai_campaign"]}"')
                    except Exception as e:
                        fail_count += 1
                        ElevenSellerOfficeStat.objects.create(
                            account=acct, error=f'{e}\n{traceback.format_exc()[-1500:]}'[:5000])
                        _log(f'  수집 FAIL: {str(e)[:150]}')

                if idx < total:
                    time.sleep(random.uniform(*INTER_ACCOUNT_SLEEP))

            _log(f'==== 완료: 성공 {ok_count} / 실패 {fail_count} ====')
        finally:
            _safe_quit(driver)
            try:
                stop_display()
            except Exception:
                pass
            guard.release_global_lock()

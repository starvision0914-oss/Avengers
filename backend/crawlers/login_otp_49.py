"""49개 계정 순차 로그인 + OTP 인증 해결 (광고비 다운로드 제외, 세션/쿠키 갱신)"""
import os, sys, time, random, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from crawlers.browser import create_driver, stop_display, _kill_stale_chrome
from crawlers import eleven_crawler as _ec
from crawlers.eleven_product_crawler import _login_for_account, DOWNLOAD_BASE
from apps.cpc.models import CrawlerAccount

# 인자로 계정목록(공백구분), 없으면 api 보유 49개
if len(sys.argv) > 1:
    IDS = sys.argv[1:]
else:
    IDS = list(CrawlerAccount.objects.filter(platform='11st', is_active=True)
               .exclude(api_key='').exclude(crawling_status__in=['차단됨', '실패'])
               .order_by('display_order', 'login_id').values_list('login_id', flat=True))

MAX_ATTEMPTS = 3


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def main():
    total = len(IDS)
    log(f'===== 49계정 로그인+OTP 시작 (대상 {total}개) =====')
    ok_cnt = otp_cnt = fail_cnt = 0
    for i, lid in enumerate(IDS, 1):
        a = CrawlerAccount.objects.filter(login_id=lid, platform='11st').first()
        if not a:
            log(f'[{i}/{total}] {lid} — 계정없음 건너뜀'); continue
        # 강제 새 로그인 위해 쿠키 제거
        a.cookie_data = ''
        a.save(update_fields=['cookie_data'])
        before_otp = a.last_otp_at

        def _l(msg, _lid=lid, _i=i):
            log(f'[{_i}/{total}][{_lid}] {msg}')

        logged = False
        for attempt in range(1, MAX_ATTEMPTS + 1):
            driver = None
            try:
                _kill_stale_chrome()
                time.sleep(1)
                driver = create_driver(download_dir=str(DOWNLOAD_BASE))
                _l(f'접속 시도 {attempt}/{MAX_ATTEMPTS}...')
                _login_for_account(driver, a, _l)   # 쿠키없음 → 풀로그인+OTP+쿠키저장
                logged = True
                break
            except Exception as e:
                _l(f'실패 {attempt}/{MAX_ATTEMPTS}: {str(e)[:100]}')
                time.sleep(random.uniform(2, 4))
            finally:
                if driver:
                    try: driver.quit()
                    except Exception: pass

        a.refresh_from_db()
        if logged:
            ok_cnt += 1
            did_otp = a.last_otp_at and a.last_otp_at != before_otp
            if did_otp:
                otp_cnt += 1
            _l(f'✅ 로그인성공 (OTP수행={bool(did_otp)}, OTP시각={a.last_otp_at}) '
               f'[누적 성공{ok_cnt}/실패{fail_cnt}]')
        else:
            fail_cnt += 1
            _l(f'⛔ {MAX_ATTEMPTS}회 실패 — 다음 계정 [누적 성공{ok_cnt}/실패{fail_cnt}]')

        # 사람처럼 계정간 대기
        if i < total:
            time.sleep(random.uniform(3, 7))

    log(f'===== 완료: 성공 {ok_cnt} / 실패 {fail_cnt} / OTP수행 {otp_cnt} (총 {total}) =====')
    stop_display()


if __name__ == '__main__':
    main()

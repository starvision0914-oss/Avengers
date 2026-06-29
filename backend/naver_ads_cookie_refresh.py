"""
네이버 광고센터 쿠키 자동 갱신
NAVER_ADS_AVAILABLE_USER 쿠키가 ~4시간마다 만료되므로, 크론으로 3시간마다 실행.
NID_AUT(네이버 로그인 쿠키)가 살아있는 한 QR 없이 자동 갱신됨.
"""
import os, sys, json, time, logging

os.environ['DISPLAY'] = ':99'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from crawlers.browser import create_driver

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

COOKIE_FILE = os.path.join(os.path.dirname(__file__), 'crawlers/naver_ads_cookies.json')


def _send_telegram(text: str):
    try:
        import requests as req
        from apps.cpc.models import TelegramConfig, TelegramRecipient
        cfg = TelegramConfig.objects.first()
        if cfg and cfg.bot_token:
            for r in TelegramRecipient.objects.filter(is_active=True):
                req.post(
                    f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage',
                    json={'chat_id': r.chat_id, 'text': text},
                    timeout=10,
                )
    except Exception as e:
        log.warning('텔레그램 알림 실패: %s', e)


def refresh_all():
    with open(COOKIE_FILE) as f:
        data = json.load(f)

    login_ids = list(data.keys())
    if not login_ids:
        log.warning('쿠키 파일 비어 있음')
        return

    driver = create_driver(kill_existing=False)
    try:
        for login_id in login_ids:
            cookies = data[login_id]
            if not cookies:
                log.warning('%s: 쿠키 없음, 스킵', login_id)
                continue

            try:
                # 쿠키 주입
                driver.get('https://ads.naver.com/')
                time.sleep(2)
                for c in cookies:
                    try:
                        driver.add_cookie(c)
                    except Exception:
                        pass

                # 광고센터 진입 — NID_AUT 유효하면 자동 세션 갱신
                driver.get('https://ads.naver.com/')
                time.sleep(5)

                current_url = driver.current_url
                if 'nid.naver.com' in current_url or 'nidlogin' in current_url:
                    log.warning('%s: NID_AUT 만료 — QR 재로그인 필요', login_id)
                    _send_telegram(f'[네이버광고] {login_id} 세션 만료 — QR 재로그인 필요')
                    continue

                new_cookies = driver.get_cookies()
                data[login_id] = new_cookies
                naver_ads_cookie = next((c for c in new_cookies if c['name'] == 'NAVER_ADS_AVAILABLE_USER'), None)
                log.info('%s: 쿠키 갱신 완료 (%d개, NAVER_ADS_AVAILABLE_USER=%s)',
                         login_id, len(new_cookies), '있음' if naver_ads_cookie else '없음')

            except Exception as e:
                log.error('%s: 갱신 오류 — %s', login_id, e)

            time.sleep(3)

        with open(COOKIE_FILE, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        log.info('쿠키 파일 저장 완료')

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    refresh_all()

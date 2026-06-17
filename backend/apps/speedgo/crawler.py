"""
스피드고 자동화 크롤러 — 세션 유지 방식
로그인 1회 → 세션 유지 → 작업 요청 시 실행
"""
import time
import logging
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By

logger = logging.getLogger('speedgo')

DOMEGGOOK_LOGIN_URL = 'https://domeggook.com/ssl/member/mem_loginForm.php'
SPEEDGO_URL = 'https://speedgo.domeggook.com/'

STEPS = [
    '주문수집',
    '배송상태갱신',
    '품절상품업데이트',
    '재입고상품업데이트',
    '가격변동상품업데이트',
    '마켓문의수집',
    '지재권및리콜신고상품삭제',
]


class SpeedgoSession:
    """스피드고 세션 — 싱글톤으로 유지"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._driver = None
                    cls._instance._logged_in = False
                    cls._instance._busy = False
        return cls._instance

    def _create_driver(self):
        opts = webdriver.ChromeOptions()
        opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--window-size=1920,1080')
        d = webdriver.Chrome(options=opts)
        d.set_page_load_timeout(60)
        d.implicitly_wait(5)
        return d

    def _is_alive(self):
        if not self._driver:
            return False
        try:
            _ = self._driver.current_url
            return True
        except Exception:
            return False

    def ensure_login(self, login_id=None, password=None):
        """로그인 상태 보장. 이미 로그인되어 있으면 스킵."""
        import os
        if not login_id:
            login_id = os.environ.get('DOMEGGOOK_ID', 'sns@455239')
        if not password:
            password = os.environ.get('DOMEGGOOK_PW', '@Tmxkqlwus0')

        if self._logged_in and self._is_alive():
            # 스피드고 페이지에 있는지 확인
            try:
                if 'speedgo.domeggook.com' in self._driver.current_url:
                    return True
                self._driver.get(SPEEDGO_URL)
                time.sleep(3)
                if 'speedgo.domeggook.com' in self._driver.current_url:
                    return True
            except Exception:
                pass

        # 새로 로그인
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass

        self._driver = self._create_driver()
        self._logged_in = False

        self._driver.get(DOMEGGOOK_LOGIN_URL)
        time.sleep(3)
        self._driver.find_element(By.ID, 'idInput').send_keys(login_id)
        self._driver.find_element(By.ID, 'pwInput').send_keys(password)
        self._driver.find_element(By.CSS_SELECTOR, 'form').submit()
        time.sleep(5)
        try:
            self._driver.switch_to.alert.accept()
        except Exception:
            pass

        cookies = self._driver.get_cookies()
        self._driver.get(SPEEDGO_URL)
        time.sleep(1)
        try:
            self._driver.switch_to.alert.accept()
        except Exception:
            pass
        for c in cookies:
            try:
                self._driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.domeggook.com', 'path': '/'})
            except Exception:
                pass

        self._driver.get(SPEEDGO_URL)
        time.sleep(3)
        self._logged_in = 'speedgo.domeggook.com' in self._driver.current_url
        return self._logged_in

    def click_step(self, step_name, timeout=180):
        """버튼 클릭 → alert 대기 → 결과 반환"""
        if not self._is_alive():
            raise RuntimeError('세션 끊김 — 재로그인 필요')

        # 스피드고 메인으로 이동 (버튼이 메인에 있음)
        if '/mybox/' in (self._driver.current_url or '') or 'speedgo.domeggook.com' not in (self._driver.current_url or ''):
            self._driver.get(SPEEDGO_URL)
            time.sleep(3)

        btn = self._driver.find_element(By.XPATH, f'//button[contains(text(),"{step_name}")]')
        self._driver.execute_script('arguments[0].scrollIntoView({block:"center"});', btn)
        time.sleep(0.5)
        self._driver.execute_script('arguments[0].click();', btn)

        time.sleep(3)
        try:
            alert = self._driver.switch_to.alert
            text = alert.text
            alert.accept()
            time.sleep(1)
            return text
        except Exception:
            pass

        start = time.time()
        while time.time() - start < timeout:
            try:
                alert = self._driver.switch_to.alert
                text = alert.text
                alert.accept()
                return text
            except Exception:
                pass
            time.sleep(5)

        return '완료 (타임아웃)'

    @property
    def is_busy(self):
        return self._busy

    @property
    def is_connected(self):
        return self._logged_in and self._is_alive()

    def close(self):
        """세션 종료"""
        self._logged_in = False
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None


def run_all_steps(login_id=None, password=None, log_fn=None, steps=None):
    """7단계 순차 실행. 세션 유지."""
    session = SpeedgoSession()

    if session.is_busy:
        return {'success': False, 'error': '이미 실행 중', 'results': []}

    session._busy = True
    target_steps = steps or STEPS
    results = []

    def log(msg):
        logger.info(msg)
        if log_fn:
            log_fn(msg)

    try:
        if not session.is_connected:
            log('도매매 로그인 중...')
            ok = session.ensure_login(login_id, password)
            if not ok:
                log('로그인 실패')
                return {'success': False, 'error': '로그인 실패', 'results': []}
            log('로그인 성공 → 세션 유지')
        else:
            log('기존 세션 재사용')

        for i, step in enumerate(target_steps, 1):
            log(f'[{i}/{len(target_steps)}] {step} 실행...')
            try:
                # 세션 끊겼으면 재로그인
                if not session.is_connected:
                    log('  세션 끊김 → 재로그인')
                    session.ensure_login(login_id, password)

                result_text = session.click_step(step)
                log(f'  ✔ {step}: {result_text[:100]}')
                results.append({'step': step, 'success': True, 'message': result_text})
            except Exception as e:
                log(f'  ✖ {step}: {e}')
                results.append({'step': step, 'success': False, 'message': str(e)})
            time.sleep(3)

    except Exception as e:
        log(f'오류: {e}')
        return {'success': False, 'error': str(e), 'results': results}
    finally:
        session._busy = False
        # 세션은 종료하지 않음 — 계속 유지

    log(f'전체 완료: {len([r for r in results if r["success"]])}/{len(results)} 성공')
    return {'success': True, 'results': results}


def get_session_status():
    """현재 세션 상태"""
    session = SpeedgoSession()
    return {
        'connected': session.is_connected,
        'busy': session.is_busy,
    }


def close_session():
    """세션 종료"""
    session = SpeedgoSession()
    session.close()
    return {'closed': True}


def send_telegram_report(results):
    """스피드고 결과를 텔레그램으로 발송"""
    import json
    import urllib.request
    from apps.cpc.models import TelegramConfig, TelegramRecipient

    cfg = TelegramConfig.objects.first()
    if not cfg or not cfg.bot_token:
        return

    lines = ['📦 스피드고 자동화 완료']
    for r in results:
        icon = '✔' if r['success'] else '✖'
        lines.append(f'  {icon} {r["step"]}: {r["message"][:60]}')

    text = '\n'.join(lines)
    for recipient in TelegramRecipient.objects.filter(is_active=True):
        try:
            data = json.dumps({'chat_id': recipient.chat_id, 'text': text}).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage',
                data=data, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass

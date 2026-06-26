"""
브라우저 드라이버 — 시스템 Chrome + Selenium
매 계정마다 driver를 새로 생성하는 패턴 (driver.quit 후 fresh start)
"""
import os
import random
import time
import subprocess
import logging
import glob
import shutil
import atexit
import signal

logger = logging.getLogger('crawler')

DEFAULT_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)

_VIEWPORT_CHOICES = [
    (1920, 1080), (1680, 1050), (1600, 900), (1536, 864),
    (1440, 900), (1366, 768),
]

_STEALTH_JS = r"""
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR','ko','en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
window.chrome = window.chrome || { runtime: {} };
"""

_display = None


def _ensure_display():
    global _display
    if _display is None:
        if os.environ.get('DISPLAY'):
            return
        try:
            from pyvirtualdisplay import Display
            _display = Display(visible=0, size=(1920, 1080))
            _display.start()
        except ImportError:
            try:
                from xvfbwrapper import Xvfb
                _display = Xvfb(width=1920, height=1080)
                _display.start()
            except ImportError:
                pass


def stop_display():
    global _display
    if _display is not None:
        try:
            _display.stop()
        except Exception:
            pass
        _display = None


def _reap_orphans():
    """고아(부모가 죽어 PPID=1) Xvfb/chromedriver/chrome 정리 — 크래시·timeout(SIGTERM) kill로
    남은 좀비 누적('좀비PC' = 디스플레이/메모리 고갈→크롤 실패) 방지.
    PPID==1(고아)만 죽이므로 실행중인 다른 크롤의 브라우저(부모 살아있음)는 건드리지 않음."""
    try:
        pids = [int(d) for d in os.listdir('/proc') if d.isdigit()]
    except Exception:
        return
    reaped = 0
    for pid in pids:
        try:
            with open(f'/proc/{pid}/stat') as f:
                data = f.read()
            rp = data.rindex(')')
            comm = data[data.index('(') + 1:rp]
            ppid = int(data[rp + 2:].split()[1])
        except Exception:
            continue
        if ppid != 1:
            continue                       # 고아만 — 실행중 크롤 보호
        if comm in ('Xvfb', 'chromedriver', 'chrome'):
            try:
                os.kill(pid, signal.SIGKILL)
                reaped += 1
            except Exception:
                pass
    if reaped:
        logger.info(f'[browser] 고아 프로세스 {reaped}개 정리(reap)')


_cleanup_registered = False


def _register_cleanup():
    """크롤 프로세스가 timeout(SIGTERM)/크래시로 죽어도 Xvfb를 정리하도록 등록.
    create_driver 안에서만 호출 → 웹서버(create_driver 미사용)엔 핸들러 미설치."""
    global _cleanup_registered
    if _cleanup_registered:
        return
    _cleanup_registered = True
    atexit.register(stop_display)
    _prev = signal.getsignal(signal.SIGTERM)

    def _on_term(signum, frame):
        try:
            stop_display()      # 내 Xvfb 정리 → 붙어있던 chrome도 디스플레이 잃고 종료
        except Exception:
            pass
        if callable(_prev) and _prev not in (signal.SIG_DFL, signal.SIG_IGN):
            try:
                _prev(signum, frame)
                return
            except Exception:
                pass
        raise SystemExit(143)   # atexit 실행됨

    try:
        signal.signal(signal.SIGTERM, _on_term)
    except Exception:
        pass


def _kill_stale_chrome():
    """오래된 임시 프로필만 정리. 활성 세션(최근 수정)은 보호 → 동시 크롤러 안전.
    pkill은 다른 크롤러 Chrome을 죽이므로 사용 안 함."""
    now = time.time()
    for pattern in ['/tmp/.org.chromium.*', '/tmp/.com.google.Chrome.*',
                    '/tmp/org.chromium.*', '/tmp/com.google.Chrome.*']:
        for p in glob.glob(pattern):
            try:
                # 30분 이내 수정된 프로필은 다른 크롤러가 사용 중일 수 있어 건너뜀
                if now - os.path.getmtime(p) < 1800:
                    continue
                shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass


def create_driver(download_dir=None, kill_existing=True, user_data_dir=None, enable_perf_log=False):
    """시스템 Chrome + Selenium 드라이버. kill_existing=False면 pkill 없이 생성.
    user_data_dir 지정 시 전용 프로필 사용 → 다른 크롤러의 임시정리에 안 지워짐(격리)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    _register_cleanup()      # timeout/크래시 시 Xvfb 정리 보장
    _reap_orphans()          # 이전 크롤이 남긴 고아 Xvfb/chrome 솎아내기(좀비PC 방지)
    if kill_existing:
        _kill_stale_chrome()
        stop_display()
    _ensure_display()

    dl = str(download_dir or '/tmp/avengers_downloads')
    os.makedirs(dl, exist_ok=True)

    vw, vh = random.choice(_VIEWPORT_CHOICES)

    for attempt in range(3):
        try:
            opts = Options()
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-dev-shm-usage')
            opts.add_argument('--disable-gpu')
            opts.add_argument(f'--window-size={vw},{vh}')
            opts.add_argument('--disable-extensions')
            opts.add_argument('--ignore-certificate-errors')
            opts.add_argument('--disable-blink-features=AutomationControlled')
            if user_data_dir:
                opts.add_argument(f'--user-data-dir={user_data_dir}')
            opts.add_argument('--lang=ko-KR')
            opts.add_argument(f'--user-agent={DEFAULT_UA}')
            opts.add_experimental_option('excludeSwitches', ['enable-automation'])
            opts.add_experimental_option('useAutomationExtension', False)

            prefs = {
                'download.default_directory': dl,
                'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': False,
                'intl.accept_languages': 'ko-KR,ko,en-US,en',
                'profile.default_content_setting_values.notifications': 2,
            }
            opts.add_experimental_option('prefs', prefs)
            if enable_perf_log:
                opts.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

            driver = webdriver.Chrome(options=opts)
            if enable_perf_log:
                driver.execute_cdp_cmd('Network.enable', {})
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(60)

            try:
                driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                    'behavior': 'allow', 'downloadPath': dl,
                })
            except Exception:
                pass

            try:
                driver.execute_cdp_cmd(
                    'Page.addScriptToEvaluateOnNewDocument', {'source': _STEALTH_JS}
                )
            except Exception:
                pass

            return driver

        except Exception as e:
            logger.warning(f'create_driver 실패 (attempt {attempt+1}/3): {e}')
            if attempt < 2:
                _kill_stale_chrome()
                time.sleep(3)

    raise RuntimeError('create_driver: 3회 시도 모두 실패')


def human_sleep(lo=0.6, hi=1.6):
    time.sleep(random.uniform(lo, hi))


create_headless_driver = create_driver

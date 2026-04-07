import os
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger('crawler')

_display = None

def _ensure_display():
    global _display
    if os.environ.get('DISPLAY'):
        return
    try:
        from xvfbwrapper import Xvfb
        if _display is None:
            _display = Xvfb(width=1920, height=1080)
            _display.start()
    except ImportError:
        pass

def _find_chrome_binary():
    candidates = [
        os.path.expanduser('~/.local/share/google-chrome/chrome'),
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return 'google-chrome'

def create_driver(download_dir=None):
    _ensure_display()
    chrome_bin = _find_chrome_binary()

    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.binary_location = chrome_bin
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        if download_dir:
            prefs = {
                'download.default_directory': str(download_dir),
                'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': False,
            }
            options.add_experimental_option('prefs', prefs)

        ver = None
        try:
            import subprocess
            out = subprocess.check_output([chrome_bin, '--version'], stderr=subprocess.DEVNULL).decode()
            ver = int(out.strip().split()[-1].split('.')[0])
        except Exception:
            pass

        driver = uc.Chrome(options=options, version_main=ver)
        driver.implicitly_wait(10)

        if download_dir:
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow', 'downloadPath': str(download_dir)
            })

        return driver
    except Exception as e:
        logger.warning(f'UC 드라이버 실패, 일반 드라이버 사용: {e}')
        return create_headless_driver(download_dir)

def create_headless_driver(download_dir=None):
    _ensure_display()
    chrome_bin = _find_chrome_binary()

    options = Options()
    options.binary_location = chrome_bin
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-extensions')
    options.add_argument('--ignore-certificate-errors')

    if download_dir:
        prefs = {
            'download.default_directory': str(download_dir),
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': False,
        }
        options.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)

    if download_dir:
        driver.execute_cdp_cmd('Page.setDownloadBehavior', {
            'behavior': 'allow', 'downloadPath': str(download_dir)
        })

    return driver

def stop_display():
    global _display
    if _display:
        _display.stop()
        _display = None

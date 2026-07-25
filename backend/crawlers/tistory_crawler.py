"""
티스토리 자동 발행 크롤러
- 로그인: 카카오계정 로그인(accounts.kakao.com) 경유. 최초 1회는 카카오 보안정책(기기인증/캡차)이
  뜰 수 있어 사람이 직접 통과시켜야 할 수 있음 — 이후 쿠키 재사용으로 자동화.
- 에디터: write.tistory.com 신규 글쓰기 화면. 제목 입력창 + 본문 편집영역.
  셀렉터는 미검증 상태 — 실제 테스트 계정으로 1회 라이브 검증 필요(화면 개편 시 재확인 필요).
- 안전 원칙: 기본은 항상 '임시저장'까지만. 실제 공개발행은 명시적 mode='publish' 지정 시에만.
"""
import time
import json
import logging

from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger('crawler')

TISTORY_LOGIN_URL = 'https://www.tistory.com/auth/login'
COOKIE_TTL_HOURS = 72


def _try_cookie_login(driver, account) -> bool:
    """저장된 쿠키로 로그인 시도. 성공하면 True."""
    from datetime import timedelta
    if not account.cookie_data or not account.cookie_saved_at:
        return False
    if timezone.now() - account.cookie_saved_at > timedelta(hours=COOKIE_TTL_HOURS):
        return False
    try:
        driver.get('https://www.tistory.com/')
        time.sleep(1)
        for cookie in json.loads(account.cookie_data):
            cookie.pop('sameSite', None)
            cookie.pop('expiry', None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        driver.get(f'https://{account.blog_name}.tistory.com/manage/newpost/')
        time.sleep(2)
        return _tistory_logged_in(driver)
    except Exception:
        return False


def _tistory_logged_in(driver) -> bool:
    """글쓰기 관리 화면(manage/newpost) 도달 여부로 판단 — 로그인 안 됐으면 로그인 페이지로 리다이렉트됨.
    (미검증, 화면 변경시 재확인 필요)"""
    try:
        url = driver.current_url
        return 'manage' in url and 'auth/login' not in url
    except Exception:
        return False


def _save_cookies(driver, account):
    try:
        account.cookie_data = json.dumps(driver.get_cookies())
        account.cookie_saved_at = timezone.now()
        account.save(update_fields=['cookie_data', 'cookie_saved_at'])
    except Exception:
        pass


def login_kakao(driver, login_id: str, login_pw: str, log_fn=None) -> bool:
    """카카오계정으로 티스토리 로그인.
    최초 로그인 시 카카오 보안정책(기기인증 등)이 뜨면 자동 통과가 안 될 수 있음 —
    이 경우 False를 반환하고 로그 남김. 사람이 1회 수동으로 통과시킨 뒤 쿠키를 저장해두면
    이후엔 _try_cookie_login으로 자동 처리 가능(2026-07 지마켓 캡차 대응과 동일한 패턴)."""
    def log(msg):
        logger.info(f'[tistory] {msg}')
        if log_fn:
            log_fn(msg)

    driver.get(TISTORY_LOGIN_URL)
    time.sleep(2)
    try:
        kakao_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.link_kakao_id"))
        )
        kakao_btn.click()
    except TimeoutException:
        log('카카오 로그인 버튼을 찾지 못함(화면 개편 가능성)')
        return False
    time.sleep(2)

    try:
        id_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='loginId']"))
        )
        pw_input = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        id_input.clear()
        id_input.send_keys(login_id)
        pw_input.clear()
        pw_input.send_keys(login_pw)
        pw_input.send_keys(Keys.RETURN)
    except (TimeoutException, NoSuchElementException):
        log('카카오 로그인 입력폼을 찾지 못함')
        return False

    time.sleep(3)
    # 카카오 보안정책(기기인증/2단계인증) 화면이 뜰 수 있음 — 자동 처리 불가, 사람 개입 필요
    if 'accounts.kakao.com' in driver.current_url:
        log('⚠️ 카카오 추가 인증 화면 감지 — 자동 로그인 실패, 수동 개입 필요')
        return False

    time.sleep(2)
    return _tistory_logged_in(driver)


def ensure_login(driver, account, log_fn=None) -> bool:
    if _try_cookie_login(driver, account):
        if log_fn:
            log_fn('쿠키 로그인 성공')
        return True
    ok = login_kakao(driver, account.login_id, account.login_pw, log_fn=log_fn)
    if ok:
        _save_cookies(driver, account)
    return ok


def _set_title(driver, title: str, log_fn=None):
    """제목 입력. id=post-title-inp 우선 시도, 실패시 라벨/placeholder 기반 폴백.
    (미검증, 화면 변경시 재확인 필요)"""
    selectors = [
        (By.ID, 'post-title-inp'),
        (By.CSS_SELECTOR, "textarea[placeholder*='제목']"),
        (By.CSS_SELECTOR, "input[placeholder*='제목']"),
    ]
    for by, sel in selectors:
        try:
            el = WebDriverWait(driver, 8).until(EC.presence_of_element_located((by, sel)))
            el.click()
            el.send_keys(title)
            return True
        except (TimeoutException, NoSuchElementException):
            continue
    if log_fn:
        log_fn('⚠️ 제목 입력창을 찾지 못함')
    return False


def _set_content(driver, content: str, log_fn=None):
    """본문 입력. 기본(WYSIWYG) 에디터의 contenteditable 영역에 직접 타이핑.
    줄바꿈은 Shift+Enter로 처리(문단 분리 방지). (미검증, 화면 변경시 재확인 필요)"""
    selectors = [
        (By.CSS_SELECTOR, "div.CodeMirror"),          # 마크다운/HTML 모드
        (By.ID, 'editor-tistory_ifr'),                  # 구 에디터 iframe (있으면 switch 필요)
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
    ]
    for by, sel in selectors:
        try:
            el = WebDriverWait(driver, 8).until(EC.presence_of_element_located((by, sel)))
            el.click()
            time.sleep(0.3)
            actions = ActionChains(driver)
            for line in content.split('\n'):
                if line:
                    actions.send_keys(line)
                actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)
            actions.perform()
            return True
        except (TimeoutException, NoSuchElementException):
            continue
    if log_fn:
        log_fn('⚠️ 본문 입력영역을 찾지 못함')
    return False


def _set_tags(driver, tags: str, log_fn=None):
    if not tags:
        return
    try:
        tag_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='태그']")
        for tag in [t.strip() for t in tags.split(',') if t.strip()]:
            tag_input.send_keys(tag)
            tag_input.send_keys(Keys.RETURN)
            time.sleep(0.3)
    except NoSuchElementException:
        if log_fn:
            log_fn('⚠️ 태그 입력창을 찾지 못함(건너뜀)')


def write_and_publish(driver, blog_name: str, title: str, content: str,
                       tags: str = '', category: str = '', mode: str = 'draft',
                       log_fn=None) -> dict:
    """글쓰기 화면 진입 → 제목/본문/태그 입력 → 저장.
    mode='draft'(기본, 항상 안전) | 'publish'(명시적 요청시에만 실제 공개발행)."""
    def log(msg):
        logger.info(f'[tistory:{blog_name}] {msg}')
        if log_fn:
            log_fn(msg)

    driver.get(f'https://{blog_name}.tistory.com/manage/newpost/')
    time.sleep(3)

    if not _set_title(driver, title, log_fn=log):
        return {'success': False, 'error': '제목 입력 실패'}
    if not _set_content(driver, content, log_fn=log):
        return {'success': False, 'error': '본문 입력 실패'}
    _set_tags(driver, tags, log_fn=log)

    if mode == 'publish':
        btn_xpaths = ["//button[contains(., '공개') and contains(., '발행')]",
                      "//button[normalize-space()='발행']"]
        action_label = '공개발행'
    else:
        btn_xpaths = ["//button[normalize-space()='저장']",
                      "//button[contains(., '임시저장')]"]
        action_label = '임시저장'

    clicked = False
    for xp in btn_xpaths:
        try:
            btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click()
            clicked = True
            break
        except TimeoutException:
            continue

    if not clicked:
        log(f'⚠️ {action_label} 버튼을 찾지 못함')
        return {'success': False, 'error': f'{action_label} 버튼 없음'}

    time.sleep(3)
    log(f'{action_label} 완료')
    return {'success': True, 'mode': mode, 'url': driver.current_url}


def run_publish(account, title: str, content: str, tags: str = '', category: str = '',
                 mode: str = 'draft', log_fn=None) -> dict:
    """전체 발행 파이프라인(락+드라이버+로그인+작성)을 한 번에 처리하는 진입점.
    platform='tistory' 전용 락 사용 — 11번가/지마켓 등 다른 플랫폼 크론과 완전히 분리되어
    서로 영향을 주지 않음(같은 tistory 작업끼리만 동시실행 방지)."""
    from apps.cpc import eleven_block_guard as guard
    from .browser import create_driver, stop_display

    ok, reason = guard.preflight('티스토리발행', platform='tistory', wait=True, wait_timeout=1800)
    if not ok:
        if log_fn:
            log_fn(f'⛔ preflight 차단: {reason}')
        return {'success': False, 'error': reason}

    driver = None
    try:
        driver = create_driver()
        if not ensure_login(driver, account, log_fn=log_fn):
            return {'success': False, 'error': '로그인 실패'}
        return write_and_publish(
            driver, account.blog_name, title, content,
            tags=tags, category=category, mode=mode, log_fn=log_fn,
        )
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        stop_display()
        guard.release_global_lock(platform='tistory')

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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

logger = logging.getLogger('crawler')

TISTORY_LOGIN_URL = 'https://www.tistory.com/auth/login'
COOKIE_TTL_HOURS = 72


def _dismiss_resume_alert(driver):
    """/manage/newpost/ 진입 시 이전 임시저장 글이 있으면 뜨는
    '이어서 작성하시겠습니까?' alert을 취소(dismiss). 이 alert이 떠 있는 동안
    current_url 등 대부분의 selenium 호출이 UnexpectedAlertPresentException으로 실패하므로
    (2026-07-26 실측 — 쿠키 로그인 판정이 이 때문에 계속 False로 오판됨) 페이지 이동 직후
    항상 먼저 호출해야 함."""
    try:
        alert = driver.switch_to.alert
        alert.dismiss()
        time.sleep(1)
        return True
    except Exception:
        return False


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
        _dismiss_resume_alert(driver)
        # 리다이렉트 체인(로그인 확인→최종 manage 페이지)이 끝나기 전에 판정하면 오탐(false)
        # 나기 쉬움(2026-07-26 실측) — URL이 안정될 때까지 최대 6초 폴링.
        last_url = None
        for _ in range(6):
            time.sleep(1)
            _dismiss_resume_alert(driver)
            cur = driver.current_url
            if cur == last_url:
                break
            last_url = cur
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
    # 카카오 보안정책(기기인증/2단계인증) 화면이 뜰 수 있음 — 자동 처리 불가.
    # 사람이 폰에서 카카오톡 인증을 승인할 시간을 줘야 함(기존엔 3초만 보고 바로 실패 처리해
    # 사용자가 폰을 확인하기도 전에 스크립트가 종료돼버리는 문제가 있었음 — 2026-07-27).
    if 'accounts.kakao.com' in driver.current_url:
        log('⚠️ 카카오 2단계 인증 화면 감지 — 폰에서 카카오톡 인증을 승인해주세요 (최대 90초 대기)')
        try:
            from apps.cpc import eleven_block_guard as guard
            guard._send_telegram_alert(
                '📱 [티스토리 로그인] 카카오 2단계 인증 요청이 떴습니다.\n'
                '카카오톡 앱에서 인증을 승인해주세요 (90초 내 미승인 시 실패 처리됩니다).'
            )
        except Exception:
            pass

        waited = 0
        while waited < 90 and 'accounts.kakao.com' in driver.current_url:
            time.sleep(3)
            waited += 3

        if 'accounts.kakao.com' in driver.current_url:
            log('⛔ 90초 내 인증 승인 확인 안 됨 — 로그인 실패')
            return False
        log('✅ 카카오 2단계 인증 승인 확인됨')

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
    """본문 입력. 티스토리 기본 에디터는 iframe#editor-tistory_ifr 안에 실제
    contenteditable 영역이 있음(2026-07-26 실측, id='editor-tistory_ifr') — 반드시
    switch_to.frame 후 입력하고, 끝나면 default_content로 복귀해야 이후 태그/저장버튼 클릭이 됨.
    줄바꿈은 Shift+Enter로 처리(문단 분리 방지)."""
    try:
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, 'editor-tistory_ifr'))
        )
        body = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body[contenteditable='true'], body"))
        )
        body.click()
        time.sleep(0.3)
        actions = ActionChains(driver)
        for line in content.split('\n'):
            # '## 소제목' 마커는 Ctrl+B로 토글해서 굵게 처리 후 마커 자체는 입력하지 않음
            # (naver_blog 크롤러의 _insert_heading과 동일한 패턴 — 문자 그대로 유출 방지).
            if line.startswith('## '):
                heading = line[3:].strip()
                actions.key_down(Keys.CONTROL).send_keys('b').key_up(Keys.CONTROL)
                actions.send_keys(heading)
                actions.key_down(Keys.CONTROL).send_keys('b').key_up(Keys.CONTROL)
            elif line:
                actions.send_keys(line)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)
        actions.perform()
        driver.switch_to.default_content()
        return True
    except (TimeoutException, NoSuchElementException) as e:
        driver.switch_to.default_content()
        if log_fn:
            log_fn(f'⚠️ 본문 입력영역을 찾지 못함: {e}')
        return False


def _insert_image(driver, file_path, log_fn=None):
    """본문 내 현재 커서 위치(보통 _set_content 직후 = 본문 끝)에 로컬 이미지 파일을 업로드+삽입.
    사진 버튼(mceu_0-open, TinyMCE)은 iframe 밖(부모 문서)에 있고, 클릭하면 서브메뉴가
    열리는데 그중 'attach-image' 항목을 눌러야 실제 파일 입력창(input#openFile)이 생성됨
    (2026-07-26 실측 — 카카오CDN에 업로드되고 본문에 <img> 태그로 자동 삽입되는 것까지 확인)."""
    try:
        driver.switch_to.default_content()
        btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.ID, 'mceu_0-open')))
        btn.click()
        time.sleep(0.5)
        attach = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'attach-image')))
        driver.execute_script("arguments[0].click();", attach)
        time.sleep(0.5)
        file_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'openFile')))
        file_input.send_keys(file_path)
        time.sleep(4)  # 업로드+본문 삽입 대기
        return True
    except (TimeoutException, NoSuchElementException) as e:
        if log_fn:
            log_fn(f'⚠️ 이미지 삽입 실패: {e}')
        return False


def _set_tags(driver, tags: str, log_fn=None):
    """태그 하나 등록할 때마다 입력창 DOM이 재생성돼 참조가 stale해짐(2026-07-26 실측,
    실제 공개발행 시도 중 StaleElementReferenceException 발생) — 매 태그마다 요소를 다시 조회."""
    if not tags:
        return
    for tag in [t.strip() for t in tags.split(',') if t.strip()]:
        try:
            tag_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='태그']")
            tag_input.send_keys(tag)
            tag_input.send_keys(Keys.RETURN)
            time.sleep(0.3)
        except (NoSuchElementException, StaleElementReferenceException):
            if log_fn:
                log_fn(f'⚠️ 태그 "{tag}" 입력 실패(건너뜀)')
            continue


def write_and_publish(driver, blog_name: str, title: str, content: str,
                       tags: str = '', category: str = '', mode: str = 'draft',
                       image_paths: list = None, log_fn=None) -> dict:
    """글쓰기 화면 진입 → 제목/본문/이미지/태그 입력 → 저장.
    mode='draft'(기본, 항상 안전) | 'publish'(명시적 요청시에만 실제 공개발행).
    image_paths: 로컬 이미지 파일 경로 리스트 — 본문 입력 직후(현재 커서=본문 끝)에 순서대로 삽입."""
    def log(msg):
        logger.info(f'[tistory:{blog_name}] {msg}')
        if log_fn:
            log_fn(msg)

    driver.get(f'https://{blog_name}.tistory.com/manage/newpost/')
    time.sleep(3)

    # 이전에 임시저장된 글이 있으면 "이어서 작성하시겠습니까?" alert이 뜸 — 취소(dismiss)해서
    # 항상 새 글로 시작(2026-07-26 실측). 없으면 그냥 지나감.
    try:
        alert = driver.switch_to.alert
        log(f'alert: {alert.text}')
        alert.dismiss()
        time.sleep(1)
    except Exception:
        pass

    if not _set_title(driver, title, log_fn=log):
        return {'success': False, 'error': '제목 입력 실패'}
    if not _set_content(driver, content, log_fn=log):
        return {'success': False, 'error': '본문 입력 실패'}
    for img_path in (image_paths or []):
        if _insert_image(driver, img_path, log_fn=log):
            log(f'이미지 삽입 완료: {img_path}')
    _set_tags(driver, tags, log_fn=log)

    # "완료" 버튼(id=publish-layer-btn)을 눌러야 공개범위 선택+저장 패널이 열림.
    # 패널 기본값은 '비공개'(draft에 해당) — publish 모드일 때만 '공개' 라디오(id=open20)로
    # 명시적으로 바꾼다. 저장 버튼(id=publish-btn) 텍스트는 선택에 따라
    # '비공개 저장' / '공개 발행'으로 자동 바뀜(2026-07-26 실측).
    action_label = '공개발행' if mode == 'publish' else '임시저장(비공개)'
    try:
        open_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.ID, 'publish-layer-btn')))
        open_btn.click()
        time.sleep(1)
    except TimeoutException:
        log('⚠️ 발행 패널 열기 버튼(완료)을 찾지 못함')
        return {'success': False, 'error': '발행 패널 버튼 없음'}

    if mode == 'publish':
        try:
            radio_label = driver.find_element(By.CSS_SELECTOR, "label[for='open20']")
            driver.execute_script("arguments[0].click();", radio_label)
            time.sleep(0.5)
        except NoSuchElementException:
            log('⚠️ 공개 옵션(라디오)을 찾지 못함 — 기본값(비공개)으로 저장될 수 있음')

    try:
        pub_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.ID, 'publish-btn')))
        pub_btn.click()
    except TimeoutException:
        log(f'⚠️ {action_label} 버튼을 찾지 못함')
        return {'success': False, 'error': f'{action_label} 버튼 없음'}

    time.sleep(3)
    log(f'{action_label} 완료')
    return {'success': True, 'mode': mode, 'url': driver.current_url}


def run_publish(account, title: str, content: str, tags: str = '', category: str = '',
                 mode: str = 'draft', image_paths: list = None, log_fn=None) -> dict:
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
            tags=tags, category=category, mode=mode, image_paths=image_paths, log_fn=log_fn,
        )
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        stop_display()
        guard.release_global_lock(platform='tistory')

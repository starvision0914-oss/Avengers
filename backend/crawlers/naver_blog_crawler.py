"""
네이버 블로그 자동 발행 크롤러
- SmartEditor ONE (iframe + contenteditable)
- xclip + xdotool 입력 (기존 크롤러 패턴)
"""
import os
import time
import subprocess
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger('crawler')

NAVER_LOGIN_URL = 'https://nid.naver.com/nidlogin.login'
BLOG_WRITE_URL = 'https://blog.naver.com/PostWriteForm.naver'


def _xtype(text, display_env=None):
    env = {**os.environ}
    if display_env:
        env['DISPLAY'] = display_env
    subprocess.run(['xclip', '-selection', 'clipboard'],
                   input=text.encode('utf-8'), check=True, env=env)
    time.sleep(0.2)
    subprocess.run(['xdotool', 'key', 'ctrl+v'], env=env)
    time.sleep(0.2)


def _xkey(key, display_env=None):
    env = {**os.environ}
    if display_env:
        env['DISPLAY'] = display_env
    subprocess.run(['xdotool', 'key', key], env=env)
    time.sleep(0.1)


def _get_display():
    return os.environ.get('DISPLAY', ':99')


def login_naver(driver, login_id: str, login_pw: str, log_fn=None) -> bool:
    def log(msg):
        if log_fn:
            log_fn(msg)
        logger.info(msg)

    disp = _get_display()
    driver.get(NAVER_LOGIN_URL)
    time.sleep(2)

    try:
        wait = WebDriverWait(driver, 10)

        # 아이디 입력
        id_field = wait.until(EC.presence_of_element_located((By.ID, 'id')))
        id_field.click()
        time.sleep(0.3)
        _xtype(login_id, disp)

        # 비밀번호 입력
        pw_field = driver.find_element(By.ID, 'pw')
        pw_field.click()
        time.sleep(0.3)
        _xtype(login_pw, disp)
        time.sleep(0.3)

        # 로그인 버튼
        login_btn = driver.find_element(By.ID, 'log.login')
        login_btn.click()
        time.sleep(3)

        # 로그인 성공 확인 (my.naver.com 또는 리디렉션)
        current = driver.current_url
        if 'nid.naver.com' in current and 'login' in current:
            # 보안 문자나 2단계 인증 페이지
            log(f'로그인 후 URL: {current} — 추가 인증 필요 가능성')
            # 캡차 없으면 잠시 대기 후 재확인
            time.sleep(3)
            current = driver.current_url
            if 'nid.naver.com' in current:
                log('로그인 실패 (캡차 or 인증 필요)')
                return False

        log(f'로그인 성공: {login_id}')
        return True

    except Exception as e:
        log(f'로그인 오류: {e}')
        return False


def _wait_editor_ready(driver, timeout=30):
    """SmartEditor ONE iframe + contenteditable 준비 대기"""
    wait = WebDriverWait(driver, timeout)

    # 에디터 iframe 탐지
    try:
        iframe = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'iframe[title*="에디터"], iframe[id*="SE"], iframe[name*="editor"]')
        ))
        driver.switch_to.frame(iframe)
    except TimeoutException:
        # iframe 없이 직접 contenteditable인 경우
        pass

    # contenteditable 편집 영역 대기
    try:
        editor = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '.se-content, [contenteditable="true"], #postWriteIframe')
        ))
        return editor
    except TimeoutException:
        return None


def write_and_publish(driver, blog_id: str, title: str, content: str,
                      tags: str = '', category_name: str = '',
                      image_paths: list = None, log_fn=None) -> str:
    """
    글 작성 후 발행
    반환: 발행된 URL (실패시 '')
    """
    def log(msg):
        if log_fn:
            log_fn(msg)
        logger.info(msg)

    disp = _get_display()
    image_paths = image_paths or []

    try:
        # 글쓰기 페이지 이동
        url = f'{BLOG_WRITE_URL}?blogId={blog_id}'
        driver.get(url)
        time.sleep(3)
        log('글쓰기 페이지 이동 완료')

        wait = WebDriverWait(driver, 20)

        # ── 제목 입력 ──
        try:
            title_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.se-title-input, input[placeholder*="제목"], .title_input')
            ))
            title_input.click()
            time.sleep(0.3)
            _xtype(title, disp)
            log(f'제목 입력: {title[:30]}')
        except TimeoutException:
            log('제목 입력창 없음')
            return ''

        time.sleep(0.5)

        # ── 본문 입력 (SmartEditor iframe) ──
        try:
            # 메인 에디터 iframe으로 전환
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            editor_frame = None
            for fr in iframes:
                src = fr.get_attribute('src') or ''
                if 'editor' in src.lower() or fr.get_attribute('id', '').lower().startswith('se'):
                    editor_frame = fr
                    break

            if editor_frame:
                driver.switch_to.frame(editor_frame)
                time.sleep(0.5)

            # contenteditable 본문 영역 클릭
            body = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[contenteditable="true"]')
            ))
            body.click()
            time.sleep(0.3)

            # 단락별로 입력 (긴 글 한번에 붙여넣기)
            _xtype(content, disp)
            log(f'본문 입력 완료 ({len(content)}자)')

            driver.switch_to.default_content()

        except Exception as e:
            log(f'본문 입력 오류: {e}')
            driver.switch_to.default_content()

        time.sleep(0.5)

        # ── 태그 입력 ──
        if tags:
            try:
                tag_input = driver.find_element(
                    By.CSS_SELECTOR, '.tag_input, input[placeholder*="태그"], .se-tag-input'
                )
                tag_input.click()
                for tag in tags.split(',')[:10]:
                    tag = tag.strip()
                    if tag:
                        _xtype(tag, disp)
                        _xkey('Return', disp)
                        time.sleep(0.2)
                log(f'태그 입력: {tags[:50]}')
            except NoSuchElementException:
                log('태그 입력창 없음 (스킵)')

        time.sleep(0.5)

        # ── 발행 버튼 ──
        try:
            publish_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '.btn_publish, button[class*="publish"], .publish_btn')
            ))
            publish_btn.click()
            time.sleep(2)
            log('발행 버튼 클릭')
        except TimeoutException:
            log('발행 버튼 없음')
            return ''

        # 발행 확인 팝업 처리
        try:
            confirm_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '.btn_confirm, .confirm_btn, button[class*="confirm"]')
            ))
            confirm_btn.click()
            time.sleep(2)
        except TimeoutException:
            pass  # 팝업 없으면 바로 발행

        # 발행 후 URL 획득
        time.sleep(2)
        published_url = driver.current_url
        log(f'발행 완료: {published_url}')
        return published_url

    except Exception as e:
        log(f'발행 오류: {e}')
        driver.switch_to.default_content()
        return ''

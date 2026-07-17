"""
네이버 블로그 자동 발행 크롤러
- SmartEditor ONE: iframe 없이 직접 DOM (제목 .se-title-text, 본문 se-module-text,
  저장 button[data-click-area="tpb.save"], 발행 button[data-click-area="tpb.publish"])
- xclip + xdotool 입력, 없으면 Selenium ActionChains 폴백
"""
import os
import time
import json
import subprocess
import logging

from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger('crawler')

NAVER_LOGIN_URL = 'https://nid.naver.com/nidlogin.login'
BLOG_WRITE_URL = 'https://blog.naver.com/PostWriteForm.naver'
NAVER_HOME_URL = 'https://www.naver.com/'
COOKIE_TTL_HOURS = 72


def _try_cookie_login(driver, account) -> bool:
    """저장된 쿠키로 로그인 시도. 성공하면 True (id/pw 재입력 불필요, 캡차/2FA 재발생 없음)."""
    from datetime import timedelta
    if not account.cookie_data or not account.cookie_saved_at:
        return False
    if timezone.now() - account.cookie_saved_at > timedelta(hours=COOKIE_TTL_HOURS):
        return False
    try:
        driver.get(NAVER_HOME_URL)
        time.sleep(1)
        for cookie in json.loads(account.cookie_data):
            cookie.pop('sameSite', None)
            cookie.pop('expiry', None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        driver.get(NAVER_HOME_URL)
        time.sleep(2)
        return _naver_logged_in(driver)
    except Exception:
        return False


def _naver_logged_in(driver) -> bool:
    """네이버 홈 기준 로그인 여부 — '로그아웃' 링크/버튼 존재로 판단(미검증, 화면 변경시 셀렉터 재확인 필요)."""
    try:
        return len(driver.find_elements(
            By.XPATH, "//*[self::a or self::button][contains(., '로그아웃')]"
        )) > 0
    except Exception:
        return False


def _save_cookies(driver, account):
    try:
        account.cookie_data = json.dumps(driver.get_cookies())
        account.cookie_saved_at = timezone.now()
        account.save(update_fields=['cookie_data', 'cookie_saved_at'])
    except Exception:
        pass


def _xtype(text, display_env=None, driver=None):
    """xclip+xdotool로 붙여넣기(사람 입력에 가까움). 두 바이너리가 없으면
    Selenium ActionChains로 현재 포커스된 요소에 실제 키 이벤트를 보냄(로그인 폼이
    아닌 글쓰기 에디터 입력용 폴백 — 봇탐지 민감도가 낮은 화면에서만 사용할 것)."""
    env = {**os.environ}
    if display_env:
        env['DISPLAY'] = display_env
    try:
        subprocess.run(['xclip', '-selection', 'clipboard'],
                       input=text.encode('utf-8'), check=True, env=env)
        time.sleep(0.2)
        subprocess.run(['xdotool', 'key', 'ctrl+v'], env=env)
        time.sleep(0.2)
    except FileNotFoundError:
        if driver is None:
            raise
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(text).perform()
        time.sleep(0.2)


def _xkey(key, display_env=None, driver=None):
    env = {**os.environ}
    if display_env:
        env['DISPLAY'] = display_env
    try:
        subprocess.run(['xdotool', 'key', key], env=env)
        time.sleep(0.1)
    except FileNotFoundError:
        if driver is None:
            raise
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys
        keymap = {'Return': Keys.RETURN, 'Tab': Keys.TAB, 'Delete': Keys.DELETE, 'BackSpace': Keys.BACKSPACE}
        if key == 'ctrl+a':
            ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
        else:
            ActionChains(driver).send_keys(keymap.get(key, key)).perform()
        time.sleep(0.1)


def _get_display():
    return os.environ.get('DISPLAY', ':99')


def ensure_login(driver, account, log_fn=None) -> bool:
    """계정으로 로그인 보장: 저장 쿠키 우선 시도 → 실패 시 id/pw 로그인 후 쿠키 저장.
    쿠키가 유효한 동안(72시간)은 캡차/2FA를 다시 겪지 않음."""
    def log(msg):
        if log_fn:
            log_fn(msg)
        logger.info(msg)

    if _try_cookie_login(driver, account):
        log(f'쿠키 로그인 성공: {account.login_id}')
        return True

    log(f'쿠키 없음/만료 — id/pw 로그인 시도: {account.login_id}')
    ok = login_naver(driver, account.login_id, account.login_pw, log_fn)
    if ok:
        _save_cookies(driver, account)
        log('로그인 성공 — 쿠키 저장(다음 실행부터 재사용)')
    return ok


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
        _xtype(login_id, disp, driver)

        # 비밀번호 입력
        pw_field = driver.find_element(By.ID, 'pw')
        pw_field.click()
        time.sleep(0.3)
        _xtype(login_pw, disp, driver)
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


def _insert_quote(driver, text, disp, log_fn=None):
    """상단 툴바 '인용구' 버튼으로 인용구 블록 삽입 후 텍스트 입력 (기본 스타일, 확인됨 2026-07-17)"""
    def log(msg):
        if log_fn:
            log_fn(msg)
        logger.info(msg)
    try:
        btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[data-name="quotation"][data-type="icon-select"][data-value="default"]')
        ))
        btn.click()
        time.sleep(0.5)
        _xtype(text, disp, driver)
        log(f'인용구 삽입: {text[:30]}')
    except Exception as e:
        log(f'인용구 삽입 실패({e}) — 일반 텍스트로 대체')
        _xtype(text, disp, driver)


def _insert_image(driver, file_path, disp, log_fn=None):
    """상단 툴바 '사진' 버튼이 만드는 숨은 input#hidden-file에 로컬 파일 경로를 직접 전달(확인됨 2026-07-17)"""
    def log(msg):
        if log_fn:
            log_fn(msg)
        logger.info(msg)
    if not file_path or not os.path.exists(file_path):
        log(f'이미지 파일 없음: {file_path}')
        return False
    try:
        img_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[data-name="image"][data-group="documentToolbar"]')
        ))
        img_btn.click()
        time.sleep(0.5)
        file_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[type="file"]#hidden-file')
        ))
        file_input.send_keys(os.path.abspath(file_path))
        time.sleep(3)  # 업로드+삽입 대기(파일 크기에 따라 더 걸릴 수 있음)
        log(f'이미지 삽입: {os.path.basename(file_path)}')
        return True
    except Exception as e:
        log(f'이미지 삽입 실패: {e}')
        return False


def fetch_temp_post_lognos(driver, blog_id):
    """admin.blog.naver.com의 임시저장 글 목록 JSON API 조회 (확인됨 2026-07-17).
    반환: [{blogNo, logNo, title, modiDate, editorVersion}, ...]"""
    driver.get(f'https://admin.blog.naver.com/TempPostList.naver?blogId={blog_id}')
    time.sleep(1.5)
    import json as _json
    try:
        raw = driver.find_element(By.TAG_NAME, 'pre').text
    except NoSuchElementException:
        raw = driver.execute_script('return document.body.innerText')
    try:
        data = _json.loads(raw)
        return data.get('result', {}).get('tempPostList', []) or []
    except Exception:
        return []


def write_and_publish(driver, blog_id: str, title: str, content: str,
                      tags: str = '', category_name: str = '',
                      image_paths: list = None, log_fn=None,
                      publish: bool = True, log_no: str = '') -> str:
    """
    글 작성 후 발행(publish=True) 또는 네이버 자체 임시저장(publish=False)
    log_no를 주면 새 글이 아니라 해당 임시저장 글을 열어서 덮어씀(중복 방지, 미검증).
    반환: 발행 시 결과 URL, 임시저장 시 logNo 문자열(조회 실패하면 'saved_draft'), 실패 시 ''

    주의: publish=False(임시저장) 경로의 버튼 셀렉터는 실제 네이버 화면에서
    검증되지 않았음. 계정 등록 후 1개 계정으로 반드시 먼저 테스트할 것.
    """
    def log(msg):
        if log_fn:
            log_fn(msg)
        logger.info(msg)

    disp = _get_display()
    image_paths = image_paths or []

    try:
        # 글쓰기 페이지 이동 (log_no 있으면 해당 임시저장 글을 직접 열어서 수정)
        url = f'{BLOG_WRITE_URL}?blogId={blog_id}' + (f'&logNo={log_no}' if log_no else '')
        driver.get(url)
        time.sleep(3)
        log('글쓰기 페이지 이동 완료' + (f' (logNo={log_no} 수정)' if log_no else ''))

        wait = WebDriverWait(driver, 20)

        if not log_no:
            # "작성 중인 글이 있습니다. 이어서 작성하시겠습니까?" 팝업 — 항상 새 글로 시작하도록 '취소' 클릭
            # 주의: contains()로 하면 툴바의 '취소선' 버튼이 먼저 걸림 — 정확히 '취소'인 것만 매칭
            try:
                cancel_btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[normalize-space(.)='취소']")
                ))
                cancel_btn.click()
                time.sleep(1)
                log('이어서 작성 팝업 — 취소(새 글로 시작)')
            except TimeoutException:
                pass

        # 도움말 패널이 열려있으면 닫기(가림 방지, 없어도 무방)
        try:
            driver.find_element(By.CSS_SELECTOR, '.se-help-panel-close-button').click()
            time.sleep(0.3)
        except Exception:
            pass

        # ── 제목 입력 ── (SmartEditor ONE: 제목도 contenteditable 컴포넌트, 별도 iframe 없음)
        try:
            title_area = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '.se-title-text')
            ))
            title_area.click()
            time.sleep(0.3)
            if log_no:
                _xkey('ctrl+a', disp, driver)
                _xkey('Delete', disp, driver)
                time.sleep(0.2)
            _xtype(title, disp, driver)
            log(f'제목 입력: {title[:30]}')
        except TimeoutException:
            log('제목 입력창 없음')
            return ''

        time.sleep(0.5)

        # ── 본문 입력 ── (제목이 아닌 첫 se-module-text 컴포넌트)
        # 본문 마크업: '> 텍스트' 줄 = 인용구 블록, '[이미지N]' 단독 줄 = image_paths[N-1] 삽입
        try:
            body_area = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "(//div[contains(@class,'se-module-text') and not(contains(@class,'se-title-text'))])[1]"
            )))
            body_area.click()
            time.sleep(0.3)
            if log_no:
                # 기존 본문 전체 삭제 후 새로 입력(미검증: 제목까지 같이 지워지지 않는지 확인 필요)
                _xkey('ctrl+a', disp, driver)
                _xkey('Delete', disp, driver)
                time.sleep(0.2)

            import re as _re
            buf = []

            def flush():
                if buf:
                    _xtype('\n'.join(buf), disp, driver)
                    buf.clear()

            for line in content.split('\n'):
                stripped = line.strip()
                img_m = _re.match(r'^\[이미지\s*(\d+)\]$', stripped)
                if stripped.startswith('> '):
                    flush()
                    _insert_quote(driver, stripped[2:], disp, log_fn)
                elif img_m:
                    flush()
                    idx = int(img_m.group(1)) - 1
                    if 0 <= idx < len(image_paths):
                        _insert_image(driver, image_paths[idx], disp, log_fn)
                    else:
                        log(f'이미지 마커 [이미지{idx+1}] — 전달된 이미지 부족(스킵)')
                else:
                    buf.append(line)
            flush()
            log(f'본문 입력 완료 ({len(content)}자, 이미지 {len(image_paths)}개 전달)')
        except Exception as e:
            log(f'본문 입력 오류: {e}')

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
                        _xtype(tag, disp, driver)
                        _xkey('Return', disp, driver)
                        time.sleep(0.2)
                log(f'태그 입력: {tags[:50]}')
            except NoSuchElementException:
                log('태그 입력창 없음 (스킵)')

        time.sleep(0.5)

        if not publish:
            # ── 네이버 자체 임시저장 ── 상단 툴바 '저장' 버튼 (data-click-area="tpb.save", 확인됨 2026-07-17)
            try:
                save_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR, 'button[data-click-area="tpb.save"]'
                )))
                save_btn.click()
                time.sleep(2)
                log('임시저장 버튼 클릭')
            except TimeoutException:
                log('임시저장 버튼을 찾지 못함 — 자동저장에 의존')

            time.sleep(2)
            log(f'임시저장 완료(추정): {title[:30]}')

            # 방금 저장한 글의 logNo 조회 (다음 수정 때 새 글 대신 이 글을 덮어쓰기 위함)
            try:
                items = fetch_temp_post_lognos(driver, blog_id)
                match = next((it for it in items if it.get('title') == title), None)
                if match and match.get('logNo'):
                    log(f'logNo 확인: {match["logNo"]}')
                    return str(match['logNo'])
            except Exception as e:
                log(f'logNo 조회 실패(치명적이지 않음): {e}')

            return 'saved_draft'

        # ── 발행 버튼 ── 상단 툴바 '발행' 버튼 (data-click-area="tpb.publish", 확인됨 2026-07-17)
        # 클릭 시 카테고리/공개설정 패널이 열리고 그 안에 최종 확인 버튼이 있을 수 있음(미검증)
        try:
            publish_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[data-click-area="tpb.publish"]')
            ))
            publish_btn.click()
            time.sleep(2)
            log('발행 버튼 클릭')
        except TimeoutException:
            log('발행 버튼 없음')
            return ''

        # 발행 확인 팝업 처리 (카테고리/공개설정 패널의 최종 발행 버튼, 셀렉터 미검증)
        try:
            confirm_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
                (By.XPATH, "//*[self::button][contains(normalize-space(.), '발행')]")
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
        log(f'발행/저장 오류: {e}')
        driver.switch_to.default_content()
        return ''

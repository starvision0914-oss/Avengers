"""로하스 간편일괄수정 - Headless CLI port (메인 탭: 분류 기반 1.0/2.0 실행).

Subcommands:
  list-categories --user X --password Y
      Login and emit available categories as a single JSON line:
          CATEGORIES: ["분류명1", "분류명2", ...]
      Emitted order matches the XPATH index (1-based). The frontend can
      use these names directly for the subsequent `run` call.

  run --user X --password Y --mode {1.0,2.0} --categories "name1,name2,..."
      Login, fetch category list to resolve indices, then iterate through
      the selected categories running either the 1.0 or 2.0 flow.

The original tkinter UI and 지마켓/11번가 탭들은 포함하지 않습니다 (원본도
해당 플로우 일부가 미완 상태 - 별도 작업 필요).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Callable, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoAlertPresentException,
    NoSuchWindowException,
    UnexpectedAlertPresentException,
    StaleElementReferenceException,
)


# ---------------------------------------------------------------------------
# Logging / globals
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, flush=True)


g_main_window: Optional[str] = None


# ---------------------------------------------------------------------------
# Driver / login
# ---------------------------------------------------------------------------

def init_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('window-size=1920,1080')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
    )
    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(5)
    drv.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    drv.execute_script('window.chrome = {}')
    return drv


def login(driver: webdriver.Chrome, user: str, password: str) -> bool:
    driver.get('http://com.exponet.co.kr/manager/')
    try:
        driver.find_element(
            By.XPATH,
            '//*[@id="loginForm"]/div/div/div/table/tbody/tr/td[1]/table/tbody/tr[1]/td[2]/input',
        ).send_keys(user)
        driver.find_element(
            By.XPATH,
            '//*[@id="loginForm"]/div/div/div/table/tbody/tr/td[1]/table/tbody/tr[2]/td[2]/input',
        ).send_keys(password)
        driver.find_element(
            By.XPATH,
            '//*[@id="loginForm"]/div/div/div/table/tbody/tr/td[2]/input',
        ).click()
        log('[login] form submitted, waiting for response...')
    except NoSuchElementException:
        log('[login] ❌ 로그인 폼을 찾을 수 없음')
        return False

    # 서버가 응답할 시간을 주고 alert 체크
    time.sleep(2)
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        alert.accept()
        log(f'[login] ❌ 로그인 실패: {alert_text}')
        return False
    except NoAlertPresentException:
        pass
    except Exception:
        pass

    # URL이 여전히 /member 또는 /manager/ 이면 실패, 다른 경로면 성공
    try:
        current = driver.current_url
    except Exception:
        current = ''
    if '/member' in current and 'manager' not in current:
        log(f'[login] ❌ 로그인 실패 (member 페이지 잔류): {current}')
        return False

    # /manager/ 루트도 일단 OK로 판단 (카테고리 fetch 단계에서 재검증됨)
    log(f'[login] ✅ 로그인 성공 ({current})')
    return True


def fetch_category_map(driver: webdriver.Chrome) -> Dict[str, int]:
    """분류 목록을 가져옴. 인덱스는 호환용이지만 실제 선택은 visible text로 함."""
    log('[categories] fetching...')
    try:
        driver.get('http://com.exponet.co.kr/manager/commercial/commercial_tiedlist')
    except UnexpectedAlertPresentException as exc:
        # 로그인이 실제로는 실패했을 때 alert가 여기서 터지는 경우
        try:
            alert = driver.switch_to.alert
            text = alert.text
            alert.accept()
            log(f'[categories] ❌ alert 발생 — 로그인 실패일 가능성: {text}')
        except Exception:
            log(f'[categories] ❌ alert 예외: {exc}')
        return {}

    time.sleep(1)
    try:
        elements = driver.find_elements(
            By.XPATH, '//select[@name="site_categoryname_search"]/option'
        )
    except UnexpectedAlertPresentException:
        try:
            alert = driver.switch_to.alert
            text = alert.text
            alert.accept()
            log(f'[categories] ❌ alert: {text}')
        except Exception:
            pass
        return {}

    result: Dict[str, int] = {}
    for index, element in enumerate(elements, start=1):
        name = element.text.strip()
        if name:
            result[name] = index
    log(f'[categories] fetched {len(result)} items')
    return result


def select_category_by_name(driver: webdriver.Chrome, name: str) -> bool:
    """분류 select를 visible text로 선택. (인덱스 의존 X — 사이트 변경에 강건)

    1) name="site_categoryname_search" 를 우선
    2) 실패 시 searchBox tr[2]/td[2]/select[1] fallback
    """
    for finder in (
        lambda: driver.find_element(By.NAME, 'site_categoryname_search'),
        lambda: driver.find_element(
            By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/select[1]'
        ),
    ):
        try:
            sel_el = finder()
            Select(sel_el).select_by_visible_text(name)
            return True
        except NoSuchElementException:
            continue
        except Exception as exc:
            log(f'[category] select error for "{name}": {exc}')
    return False


# ---------------------------------------------------------------------------
# Alert helpers
# ---------------------------------------------------------------------------

def handle_alerts(driver: webdriver.Chrome) -> None:
    try:
        for _ in range(4):
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            a = Alert(driver)
            log(f'[alert] {a.text}')
            a.accept()
            time.sleep(1)
    except TimeoutException:
        pass


def handle_alert(driver: webdriver.Chrome) -> bool:
    try:
        alert = WebDriverWait(driver, 2).until(EC.alert_is_present())
        text = alert.text
        log(f'[alert] {text}')
        if '상품 갯수는 20개를 넘을 수 없습니다' in text:
            alert.accept()
            close_popup_window(driver)
            return False
        if '등록수가 50개 이상입니다' in text:
            alert.accept()
            close_popup_window(driver)
            return False
        alert.accept()
        return True
    except (TimeoutException, NoAlertPresentException):
        return True
    except Exception as exc:
        log(f'[alert] handler error: {exc}')
        return True


def close_popup_window(driver: webdriver.Chrome) -> None:
    try:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
    except NoSuchWindowException:
        pass


# ---------------------------------------------------------------------------
# 1.0 flow — process_items / handle_popup / save_and_close
# ---------------------------------------------------------------------------

def save_and_close(driver: webdriver.Chrome) -> None:
    try:
        save = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="tieForm"]/div/span/input'))
        )
        save.click()
        log('[1.0] save clicked')
        WebDriverWait(driver, 120, poll_frequency=1).until(EC.alert_is_present())
        handle_alert(driver)
        WebDriverWait(driver, 3).until(EC.number_of_windows_to_be(1))
        driver.switch_to.window(driver.window_handles[0])
    except (
        TimeoutException,
        NoSuchElementException,
        UnexpectedAlertPresentException,
        NoSuchWindowException,
    ) as exc:
        log(f'[1.0] save_and_close error: {exc}')
        handle_alert(driver)
        try:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except NoSuchWindowException:
            pass


def handle_popup_10(driver: webdriver.Chrome) -> bool:
    try:
        WebDriverWait(driver, 3).until(EC.number_of_windows_to_be(2))
        driver.switch_to.window(driver.window_handles[1])
        driver.find_element(By.XPATH, '//*[@id="tieForm"]/div/span/input').click()
        time.sleep(2)
        save_and_close(driver)
        return True
    except TimeoutException:
        return False
    except UnexpectedAlertPresentException:
        return handle_alert(driver)


def process_items_10(driver: webdriver.Chrome, stop_check: Callable[[], bool]) -> None:
    processed = set()
    current = 2
    while not stop_check():
        try:
            rows = driver.find_elements(
                By.XPATH, '//*[@id="tiedlistForm"]/table[2]/tbody/tr'
            )
            total = len(rows)
            if total < 2:
                log('[1.0] no items, moving on')
                return
            log(f'[1.0] page has {total} rows')
            while current <= total:
                if stop_check():
                    return
                if current >= total:
                    return
                if current in processed:
                    current += 1
                    continue
                try:
                    xp = f'//*[@id="tiedlistForm"]/table[2]/tbody/tr[{current}]/td[10]/span[1]/input'
                    btn = driver.find_element(By.XPATH, xp)
                    if btn.is_displayed():
                        btn.click()
                        log(f'[1.0] row {current} clicked')
                        if not handle_popup_10(driver):
                            log(f'[1.0] row {current} no popup, skip')
                        else:
                            processed.add(current)
                        current += 1
                        continue
                except NoSuchElementException:
                    return
        except Exception as exc:
            log(f'[1.0] error: {exc}')
            return


# ---------------------------------------------------------------------------
# 2.0 flow — process_product_items / modify_product_v2 / ...
# ---------------------------------------------------------------------------

def modify_product_v2(driver: webdriver.Chrome) -> None:
    global g_main_window
    try:
        main_window = driver.current_window_handle
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
        new_window = [h for h in driver.window_handles if h != main_window][0]
        driver.switch_to.window(new_window)
        log('[2.0] switched to new window')

        for attempt in range(2):
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'child_main_id2'))
                )
                log('[2.0] dropdown ready')
                break
            except TimeoutException:
                log(f'[2.0] dropdown missing (try {attempt + 1}), refreshing')
                driver.refresh()
                time.sleep(3)
        else:
            log('[2.0] dropdown still missing — close and return')
            driver.close()
            driver.switch_to.window(main_window)
            return

        first_opt = driver.find_element(
            By.XPATH, '//*[@id="child_main_id2"]/option[1]'
        )
        if not first_opt.is_selected():
            log('[2.0] first option not selected — proceeding next')
            driver.find_element(By.XPATH, '//*[@id="proc_next"]').click()
            time.sleep(3)
            try:
                alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
                if '등록수가 50개 이상입니다' in alert.text:
                    log('[2.0] registration overflow — return')
                    alert.accept()
                    driver.close()
                    driver.switch_to.window(main_window)
                    return
            except TimeoutException:
                pass
            modify_Lcode_product(driver)
            return

        log('[2.0] first option selected — representative product logic')
        metrics = []  # (sale_count, days, row_idx)
        row = 3
        while True:
            try:
                sale_text = (
                    driver.find_element(By.XPATH, f'//tbody/tr[{row}]/td[6]')
                    .text.strip().replace(',', '')
                )
                days_text = (
                    driver.find_element(By.XPATH, f'//tbody/tr[{row}]/td[10]')
                    .text.strip().replace('일', '')
                )
                sale = int(sale_text) if sale_text.isdigit() else 0
                days = int(days_text) if days_text.isdigit() else 0
                metrics.append((sale, days, row))
                row += 1
            except NoSuchElementException:
                break

        if not metrics:
            log('[2.0] no metrics — return')
            driver.close()
            driver.switch_to.window(main_window)
            return

        if any(s > 0 for s, _, _ in metrics):
            chosen = max(metrics, key=lambda x: (x[0], x[1]))
            log(f'[2.0] by sales: row {chosen[2]} (qty {chosen[0]}, days {chosen[1]})')
        else:
            if len(metrics) < 2:
                log('[2.0] not enough rows — return')
                driver.close()
                driver.switch_to.window(main_window)
                return
            by_days = sorted(metrics, key=lambda x: x[1], reverse=True)
            chosen = by_days[1]
            log(f'[2.0] by days: row {chosen[2]} (days {chosen[1]})')

        selected_row = chosen[2]
        option = driver.find_element(
            By.XPATH, f'//*[@id="child_main_id2"]/option[{selected_row - 1}]'
        )
        option.click()
        log(f'[2.0] selected rep: {option.text}')

        change_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '/html/body/table/tbody/tr/td[1]/table/tbody/tr[1]/th/span[2]/input',
            ))
        )
        change_btn.click()
        log('[2.0] change clicked')
        handle_alerts(driver)

        next_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="proc_next"]'))
        )
        next_btn.click()
        time.sleep(3)
        try:
            alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
            if '등록수가 50개 이상입니다' in alert.text:
                log('[2.0] registration overflow — return')
                alert.accept()
                driver.close()
                driver.switch_to.window(main_window)
                return
        except TimeoutException:
            pass

        log('[2.0] next clicked')
        modify_Lcode_product(driver)

    except Exception as exc:
        log(f'[2.0] modify_product_v2 error: {exc}')
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def modify_Lcode_product(driver: webdriver.Chrome) -> None:
    try:
        modify_buttons = driver.find_elements(
            By.XPATH, '//tbody/tr/td[11]/span[1]/input[1]'
        )
        for idx, btn in enumerate(modify_buttons, start=3):
            try:
                cls = btn.get_attribute('class') or ''
                if 'btn_z btn_zb' in cls:
                    log(f'[2.0/L] row {idx} not completed — return')
                    driver.close()
                    if g_main_window:
                        driver.switch_to.window(g_main_window)
                    return
            except Exception as exc:
                log(f'[2.0/L] row {idx} error: {exc}')
                continue

        try:
            next_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="proc_next"]'))
            )
            next_btn.click()
            log('[2.0/L] next clicked')
            modify_SplitCode_product(driver)
        except TimeoutException:
            log('[2.0/L] no next button — possible last page')
    except Exception as exc:
        log(f'[2.0/L] error: {exc}')


def modify_SplitCode_product(driver: webdriver.Chrome) -> None:
    try:
        modify_buttons = driver.find_elements(
            By.XPATH, '//tbody/tr/td[11]/span[1]/input[1]'
        )
        for idx, btn in enumerate(modify_buttons, start=3):
            try:
                cls = btn.get_attribute('class') or ''
                if 'btn_z btn_zb' in cls:
                    log(f'[2.0/S] row {idx} not completed — return')
                    driver.close()
                    if g_main_window:
                        driver.switch_to.window(g_main_window)
                    return
            except StaleElementReferenceException:
                continue
            except Exception:
                continue
    except Exception as exc:
        log(f'[2.0/S] error: {exc}')

    try:
        nxt = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="proc_next"]'))
        )
        nxt.click()
        log('[2.0/S] next clicked')
        select_bundle_product(driver)
    except TimeoutException:
        log('[2.0/S] no next button')


def select_bundle_product(driver: webdriver.Chrome) -> None:
    try:
        nxt = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="tieForm"]/div/span[2]/input'))
        )
        nxt.click()
        log('[2.0/bundle] next clicked')
        WebDriverWait(driver, 15).until(
            EC.text_to_be_present_in_element(
                (By.XPATH, '//*[@id="tieForm"]/table/tbody/tr[1]/th'),
                '▶ 묶음정보 상품 정보 확인',
            )
        )
        confirm_bundle_product_info(driver)
    except TimeoutException:
        log('[2.0/bundle] confirm page not detected')
    except Exception as exc:
        log(f'[2.0/bundle] error: {exc}')


def confirm_bundle_product_info(driver: webdriver.Chrome) -> bool:
    try:
        main_window = driver.current_window_handle
        complete = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//*[@id="tieForm"]/table/tbody/tr[2]/td/table/tbody/tr[9]/td/input[3]',
            ))
        )
        complete.click()
        log('[2.0/confirm] complete clicked')
        handle_alerts(driver)

        save = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((
                By.XPATH, '//*[@id="tieForm"]/table/tbody/tr[2]/td/div/span[1]/input'
            ))
        )
        save.click()
        log('[2.0/confirm] save clicked')

        try:
            WebDriverWait(driver, 15).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except TimeoutException:
            pass

        try:
            close_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    '//*[@id="tieForm"]/table/tbody/tr[2]/td/div/span[2]/input',
                ))
            )
            close_btn.click()
            WebDriverWait(driver, 10).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
            WebDriverWait(driver, 3).until(EC.number_of_windows_to_be(1))
            driver.switch_to.window(driver.window_handles[0])
        except TimeoutException:
            pass
        return True
    except Exception as exc:
        log(f'[2.0/confirm] error: {exc}')
        return False
    finally:
        try:
            driver.switch_to.default_content()
        except NoSuchWindowException:
            pass


def process_product_items_20(driver: webdriver.Chrome, stop_check: Callable[[], bool]) -> None:
    global g_main_window
    g_main_window = driver.current_window_handle
    try:
        rows = driver.find_elements(
            By.XPATH, '//*[@id="tiedlistForm"]/table[2]/tbody/tr'
        )
        total = len(rows)
        log(f'[2.0] total rows to edit: {total}')
        for row_num in range(2, total + 1):
            if stop_check():
                return
            try:
                xp = f'//*[@id="tiedlistForm"]/table[2]/tbody/tr[{row_num}]/td[10]/span[2]/input'
                btn = driver.find_element(By.XPATH, xp)
                btn.click()
                log(f'[2.0] ({row_num - 1}/{total - 1}) modify clicked')
                time.sleep(3)
                modify_product_v2(driver)
            except NoSuchElementException:
                log(f'[2.0] row {row_num} no button — skip')
                continue
    except Exception as exc:
        log(f'[2.0] process error: {exc}')


# ---------------------------------------------------------------------------
# Category search drivers
# ---------------------------------------------------------------------------

def run_mode_10(
    driver: webdriver.Chrome,
    cats: Dict[str, int],
    selected_names: List[str],
    stop_check: Callable[[], bool],
) -> None:
    """1.0 일괄 수정 플로우.

    검색 조건 (사용자 확인 XPath):
      - 분류 (select[1]) = 선택한 분류명 (visible text 매칭)
      - 작업상태 (select[3]/option[1]) = 작업완료
      - 정보수정 (select[6]/option[2]) = 수정사항유
      - 조회수 (select[16]/option[6]) = 500개
    """
    target = 'http://com.exponet.co.kr/manager/commercial/commercial_tiedlist'
    for name in selected_names:
        if stop_check():
            return
        log(f'[1.0] ====== 분류: {name} ======')
        driver.get(target)
        time.sleep(1)

        if not select_category_by_name(driver, name):
            log(f'[1.0] ⚠️ 분류 선택 실패 (visible text "{name}" 없음)')
            continue
        log(f'[1.0] ✅ 분류 선택: {name}')

        # 작업상태 = 작업완료
        try:
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/select[3]/option[1]'
            ).click()
            log('[1.0] ✅ 작업상태 = 작업완료')
        except NoSuchElementException:
            log('[1.0] ⚠️ 작업상태 셀렉터 못 찾음 (select[3]/option[1])')

        # 정보수정 = 수정사항유
        try:
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/select[6]/option[2]'
            ).click()
            log('[1.0] ✅ 정보수정 = 수정사항유')
        except NoSuchElementException:
            log('[1.0] ⚠️ 정보수정 셀렉터 못 찾음 (select[6]/option[2])')

        # 조회수 = 500개
        try:
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/select[16]/option[6]'
            ).click()
            log('[1.0] ✅ 조회수 = 500개')
        except NoSuchElementException:
            log('[1.0] ⚠️ 조회수 셀렉터 못 찾음 (select[16]/option[6])')

        # 검색 버튼
        try:
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/button'
            ).click()
            log('[1.0] 🔍 검색 실행')
        except NoSuchElementException:
            log('[1.0] ❌ 검색 버튼 못 찾음 — 다음 분류로')
            continue

        time.sleep(2)
        process_items_10(driver, stop_check)
        log(f'[1.0] ====== {name} 처리 완료 ======')


def run_mode_20(
    driver: webdriver.Chrome,
    cats: Dict[str, int],
    selected_names: List[str],
    stop_check: Callable[[], bool],
) -> None:
    target = 'http://com.exponet.co.kr/manager/commercial/commercial_tiedlist'
    for name in selected_names:
        if stop_check():
            return
        log(f'[2.0] ====== 분류: {name} ======')
        driver.get(target)
        time.sleep(1)

        if not select_category_by_name(driver, name):
            log(f'[2.0] ⚠️ 분류 선택 실패: {name}')
            continue
        log(f'[2.0] ✅ 분류 선택: {name}')

        try:
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/select[3]/option[3]'
            ).click()
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/select[7]/option[3]'
            ).click()
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/select[16]'
            ).click()
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr[2]/td[2]/button'
            ).click()
            log('[2.0] 🔍 검색 실행')
            time.sleep(2)
            process_product_items_20(driver, stop_check)
            log(f'[2.0] ====== {name} 처리 완료 ======')
        except NoSuchElementException as exc:
            log(f'[2.0] 셀렉터 실패: {exc}')


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def cmd_list_categories(args) -> int:
    driver = init_driver(headless=not args.no_headless)
    try:
        if not login(driver, args.user, args.password):
            return 3
        cats = fetch_category_map(driver)
        if not cats:
            log('[list-categories] ❌ 분류 목록을 가져오지 못함 (로그인 또는 페이지 접근 실패)')
            return 4
        names = list(cats.keys())
        log('CATEGORIES: ' + json.dumps(names, ensure_ascii=False))
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def cmd_run(args) -> int:
    selected = [c.strip() for c in args.categories.split(',') if c.strip()]
    if not selected:
        log('[run] no categories provided')
        return 2

    driver = init_driver(headless=not args.no_headless)
    try:
        if not login(driver, args.user, args.password):
            return 3
        cats = fetch_category_map(driver)
        if not cats:
            log('[run] category list empty')
            return 4

        def stop_check() -> bool:
            return False  # subprocess kill handles stopping

        if args.mode == '1.0':
            run_mode_10(driver, cats, selected, stop_check)
        else:
            run_mode_20(driver, cats, selected, stop_check)
        log('[run] done')
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('list-categories')
    p1.add_argument('--user', required=True)
    p1.add_argument('--password', required=True)
    p1.add_argument('--no-headless', action='store_true')

    p2 = sub.add_parser('run')
    p2.add_argument('--user', required=True)
    p2.add_argument('--password', required=True)
    p2.add_argument('--mode', choices=['1.0', '2.0'], required=True)
    p2.add_argument('--categories', required=True,
                    help='comma-separated category names')
    p2.add_argument('--no-headless', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'list-categories':
        return cmd_list_categories(args)
    return cmd_run(args)


if __name__ == '__main__':
    sys.exit(main())

"""로하스 재입고 상품추가 - Headless CLI port.

Usage:
  python restock.py --user <ID> --password <PW> --codes "L1234\nL5678"

Reads product codes either from --codes (newline-separated string)
or from --codes-file (path to a text file, one code per line).

Because the original flow uses multi-step product-add popups that
were controlled via tkinter messagebox prompts, this CLI version
always auto-confirms (equivalent of answering '예') and runs in
headless Chrome.
"""
from __future__ import annotations

import argparse
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def log(msg: str) -> None:
    print(msg, flush=True)


def init_driver(headless: bool) -> webdriver.Chrome:
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
    return drv


def login(driver: webdriver.Chrome, user: str, password: str) -> bool:
    driver.get('http://com.exponet.co.kr/manager/')
    try:
        id_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                '//*[@id="loginForm"]/div/div/div/table/tbody/tr/td[1]/table/tbody/tr[1]/td[2]/input',
            ))
        )
        id_input.send_keys(user)
        pw_input = driver.find_element(
            By.XPATH,
            '//*[@id="loginForm"]/div/div/div/table/tbody/tr/td[1]/table/tbody/tr[2]/td[2]/input',
        )
        pw_input.send_keys(password)
        driver.find_element(
            By.XPATH,
            '//*[@id="loginForm"]/div/div/div/table/tbody/tr/td[2]/input',
        ).click()
    except Exception as exc:
        log(f'[login] error: {exc}')
        return False

    try:
        WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="kc-login-error-message"]'))
        )
        log('[login] failed')
        return False
    except TimeoutException:
        log('[login] success')
        return True


def handle_popup(driver: webdriver.Chrome) -> None:
    main_window = driver.current_window_handle

    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
    popup_window = [w for w in driver.window_handles if w != main_window][0]
    driver.switch_to.window(popup_window)

    collected = []
    try:
        rows = driver.find_elements(By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr')
        log(f'[popup] rows collected: {max(len(rows) - 1, 0)}')
        for i, row in enumerate(rows[1:], start=1):
            try:
                text = row.find_element(By.XPATH, 'td[2]').text
                collected.append(text)
                log(f'[popup] row {i}: {text}')
            except Exception as exc:
                log(f'[popup] row {i} failed: {exc}')
    except Exception as exc:
        log(f'[popup] collect error: {exc}')

    try:
        driver.find_element(By.XPATH, '/html/body/table/tbody/tr[1]/td/span/input').click()
        log('[popup] first add button clicked')
    except Exception as exc:
        log(f'[popup] first add button error: {exc}')

    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(3))
    second_popup = [w for w in driver.window_handles if w not in (main_window, popup_window)][0]
    driver.switch_to.window(second_popup)

    try:
        driver.find_element(
            By.XPATH, '/html/body/table/tbody/tr/td[2]/table/tbody/tr[1]/th/span/input'
        ).click()
        log('[popup] second add button clicked')
    except Exception as exc:
        log(f'[popup] second add button error: {exc}')

    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(4))
    third_popup = [
        w for w in driver.window_handles if w not in (main_window, popup_window, second_popup)
    ][0]
    driver.switch_to.window(third_popup)

    try:
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="fv"]'))
        )
        driver.execute_script(
            'arguments[0].value = arguments[1];', search_box, '\n'.join(collected)
        )
        log('[popup] data inserted')

        driver.find_element(
            By.XPATH, '//*[@id="searchBox"]/tbody/tr/td[2]/select[9]/option[2]'
        ).click()
        driver.find_element(
            By.XPATH, '//*[@id="searchBox"]/tbody/tr/td[2]/input[6]'
        ).click()
        log('[popup] search clicked')
    except Exception as exc:
        log(f'[popup] search error: {exc}')

    # Auto-confirm: select all + add + close (equivalent of tkinter "예")
    try:
        driver.find_element(
            By.XPATH, '//*[@id="listForm"]/table[3]/tbody/tr[1]/th[1]/input'
        ).click()
        log('[popup] select all')
        time.sleep(2)
        driver.find_element(
            By.XPATH, '//*[@id="listForm"]/table[2]/tbody/tr[1]/td/span/input'
        ).click()
        log('[popup] add-and-close clicked')
    except Exception as exc:
        log(f'[popup] add-and-close error: {exc}')

    try:
        driver.switch_to.window(second_popup)
        time.sleep(2)
        driver.find_element(By.XPATH, '//*[@id="tieForm"]/div/span/input').click()
        log('[popup] next clicked')
        time.sleep(2)
        driver.find_element(By.XPATH, '//*[@id="tieForm"]/div/span/input').click()
        log('[popup] save-and-close clicked')

        WebDriverWait(driver, 5).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()
        log('[popup] save alert accepted')
    except Exception as exc:
        log(f'[popup] save error: {exc}')

    for handle in driver.window_handles:
        if handle != main_window:
            try:
                driver.switch_to.window(handle)
                driver.close()
            except Exception:
                pass
    driver.switch_to.window(main_window)
    log('[popup] returned to main window')


def process_items(driver: webdriver.Chrome) -> None:
    i = 2
    while True:
        try:
            xpath = f'//*[@id="tiedlistForm"]/table[2]/tbody/tr[{i}]/td[8]/span/input'
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            btn.click()
            log(f'[process] row {i - 1}: opened popup')
            handle_popup(driver)
            i += 1
        except (NoSuchElementException, TimeoutException):
            log(f'[process] finished at row {i - 1}')
            break


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--codes', default='', help='newline-separated product codes')
    parser.add_argument('--codes-file', default='', help='file with one code per line')
    parser.add_argument('--no-headless', action='store_true')
    args = parser.parse_args()

    codes = args.codes
    if args.codes_file:
        with open(args.codes_file, 'r', encoding='utf-8') as fh:
            codes = fh.read()
    codes = codes.strip()
    if not codes:
        log('[main] no product codes provided')
        return 2

    driver = init_driver(headless=not args.no_headless)
    try:
        if not login(driver, args.user, args.password):
            return 3

        target = 'http://com.exponet.co.kr/manager/commercial/commercial_stats_new2B/p/1'
        driver.get(target)
        try:
            WebDriverWait(driver, 15).until(EC.url_to_be(target))
        except TimeoutException:
            log('[main] target url load timeout')
            return 4

        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    '//*[@id="searchBox"]/tbody/tr/td[2]/select[17]/option[5]',
                ))
            ).click()
        except Exception as exc:
            log(f'[main] viewnum select failed: {exc}')
            return 5

        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="fv"]'))
            )
            driver.execute_script('arguments[0].value = arguments[1];', search_box, codes)
            driver.find_element(
                By.XPATH, '//*[@id="searchBox"]/tbody/tr/td[2]/input[7]'
            ).click()
            log('[main] search clicked')
        except Exception as exc:
            log(f'[main] search failed: {exc}')
            return 6

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    '//*[@id="tiedlistForm"]/table[2]/tbody/tr[2]/td[8]/span/input',
                ))
            )
            log('[main] results loaded')
        except TimeoutException:
            log('[main] no search results')
            return 7

        process_items(driver)
        log('[main] done')
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    sys.exit(main())

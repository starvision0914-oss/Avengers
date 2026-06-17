"""Debug version of restock.py — non-headless + screenshots at each step.

Run inside xvfb-run:
    xvfb-run -a python3 restock_debug.py --user X --password Y --codes "L12345"

Screenshots are written to /home/rejoice888/PUBLIC/로하스/screenshots/ so they
can be viewed from Windows via Samba.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

SHOTS = Path('/home/rejoice888/PUBLIC/로하스/screenshots')
SHOTS.mkdir(parents=True, exist_ok=True)

_step = 0


def log(msg: str) -> None:
    print(msg, flush=True)


def shot(driver, label: str) -> None:
    global _step
    _step += 1
    name = f'{_step:03d}_{label}.png'
    path = SHOTS / name
    try:
        driver.save_screenshot(str(path))
        log(f'[shot] {name}')
    except Exception as exc:
        log(f'[shot] failed {name}: {exc}')


def dump_html(driver, label: str) -> None:
    path = SHOTS / f'{_step:03d}_{label}.html'
    try:
        path.write_text(driver.page_source, encoding='utf-8')
        log(f'[html] {label}.html saved')
    except Exception as exc:
        log(f'[html] dump failed: {exc}')


def init_driver() -> webdriver.Chrome:
    opts = Options()
    # NOT headless — we want a real browser inside xvfb
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


def login(driver, user: str, password: str) -> bool:
    driver.get('http://com.exponet.co.kr/manager/')
    shot(driver, 'login_page')
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
        log('[login] submitted')
        time.sleep(3)
        shot(driver, 'after_login')
        return True
    except Exception as exc:
        log(f'[login] error: {exc}')
        shot(driver, 'login_error')
        return False


def run(user: str, password: str, codes: str) -> int:
    driver = init_driver()
    try:
        if not login(driver, user, password):
            return 1

        driver.get('http://com.exponet.co.kr/manager/commercial/commercial_stats_new2B/p/1')
        time.sleep(2)
        shot(driver, 'target_page')

        # Apply view count
        try:
            driver.find_element(
                By.XPATH,
                '//*[@id="searchBox"]/tbody/tr/td[2]/select[17]/option[5]',
            ).click()
            log('[main] viewnum selected')
        except Exception as exc:
            log(f'[main] viewnum error: {exc}')

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="fv"]'))
        )
        driver.execute_script('arguments[0].value = arguments[1];', search_box, codes)
        shot(driver, 'codes_entered')
        driver.find_element(
            By.XPATH, '//*[@id="searchBox"]/tbody/tr/td[2]/input[7]'
        ).click()
        log('[main] search clicked')
        time.sleep(3)
        shot(driver, 'search_results')

        # Click first row's 포함상품보기 button
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.XPATH,
                '//*[@id="tiedlistForm"]/table[2]/tbody/tr[2]/td[8]/span/input',
            ))
        )
        main_window = driver.current_window_handle
        driver.find_element(
            By.XPATH,
            '//*[@id="tiedlistForm"]/table[2]/tbody/tr[2]/td[8]/span/input',
        ).click()
        log('[main] row1 포함상품보기 clicked')

        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
        popup1 = [w for w in driver.window_handles if w != main_window][0]
        driver.switch_to.window(popup1)
        time.sleep(1)
        shot(driver, 'popup1_open')

        # Click first 상품추가 button
        driver.find_element(
            By.XPATH, '/html/body/table/tbody/tr[1]/td/span/input'
        ).click()
        log('[popup1] first add button clicked')
        time.sleep(3)

        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(3))
        popup2 = [
            w for w in driver.window_handles if w not in (main_window, popup1)
        ][0]
        driver.switch_to.window(popup2)
        time.sleep(2)
        shot(driver, 'popup2_open')
        dump_html(driver, 'popup2')

        # Try to find the second add button — list all inputs first
        log('[popup2] inspecting inputs...')
        inputs = driver.find_elements(By.TAG_NAME, 'input')
        for i, el in enumerate(inputs[:30]):
            try:
                log(
                    f'  input[{i}] type={el.get_attribute("type")} '
                    f'value={el.get_attribute("value")} name={el.get_attribute("name")}'
                )
            except Exception:
                pass

        # Try the original XPath
        try:
            btn = driver.find_element(
                By.XPATH, '/html/body/table/tbody/tr/td[2]/table/tbody/tr[1]/th/span/input'
            )
            log(f'[popup2] original XPath found: value={btn.get_attribute("value")}')
            btn.click()
            log('[popup2] second add button clicked')
        except NoSuchElementException:
            log('[popup2] original XPath NOT FOUND — trying alternatives')
            # Try finding by value (common Korean labels)
            for val in ['상품추가', '선택상품추가', '추가']:
                try:
                    btn = driver.find_element(
                        By.XPATH, f'//input[@value="{val}"]'
                    )
                    log(f'[popup2] fallback input[@value="{val}"] found')
                    btn.click()
                    log(f'[popup2] clicked "{val}"')
                    break
                except NoSuchElementException:
                    log(f'[popup2] no input with value "{val}"')
                    continue

        time.sleep(3)
        shot(driver, 'popup2_after_click')

        # Check how many windows we have now
        log(f'[popup2] window count now: {len(driver.window_handles)}')
        if len(driver.window_handles) >= 3:
            try:
                popup3 = [
                    w for w in driver.window_handles
                    if w not in (main_window, popup1, popup2)
                ][0]
                driver.switch_to.window(popup3)
                time.sleep(2)
                shot(driver, 'popup3_open')
                dump_html(driver, 'popup3')
            except Exception as exc:
                log(f'[popup3] switch error: {exc}')

        return 0
    except Exception as exc:
        log(f'[fatal] {type(exc).__name__}: {exc}')
        try:
            shot(driver, 'fatal')
        except Exception:
            pass
        return 2
    finally:
        time.sleep(2)
        try:
            driver.quit()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--codes', required=True)
    args = parser.parse_args()
    # Clean old screenshots
    for p in SHOTS.glob('*'):
        try:
            p.unlink()
        except Exception:
            pass
    return run(args.user, args.password, args.codes)


if __name__ == '__main__':
    sys.exit(main())

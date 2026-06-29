"""네이버 쇼핑파트너센터 클린위반 전체 계정 크롤링"""
import time
from datetime import date, datetime
from django.core.management.base import BaseCommand
from apps.smartstore.models import SmartStoreAccount, SmartStoreCleanViolation

from crawlers.browser import create_driver, stop_display
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, NoSuchElementException


def w(n):
    time.sleep(n)


def login(driver, login_id, login_pw):
    CLEAN_URL = 'https://center.shopping.naver.com/monitor/clean'
    driver.get(CLEAN_URL)
    w(4)

    try:
        btn = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button.btn_login'))
        )
        driver.execute_script("arguments[0].click();", btn)
        w(5)
    except Exception:
        return False

    handles = driver.window_handles
    if len(handles) > 1:
        driver.switch_to.window(handles[-1])
        w(3)

    try:
        id_inp = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="이메일"], input[placeholder*="아이디"]'))
        )
        id_inp.clear()
        id_inp.send_keys(login_id)
        w(0.3)
        pw_inp = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        pw_inp.clear()
        pw_inp.send_keys(login_pw)
        w(0.3)
        try:
            driver.find_element(By.CSS_SELECTOR, 'button.Button_btn__wNWXt').click()
        except Exception:
            pw_inp.send_keys(Keys.RETURN)
    except Exception as e:
        print(f'    로그인 입력 오류: {e}')
        return False

    for i in range(15):
        w(1)
        try:
            cur = driver.current_url or ''
            if 'accounts.commerce' not in cur and 'login' not in cur.lower():
                return True
        except WebDriverException:
            pass
    return False


def crawl_violations(driver):
    """iframe 진입 후 전 페이지 클린위반 수집"""
    CLEAN_URL = 'https://center.shopping.naver.com/monitor/clean'

    driver.switch_to.window(driver.window_handles[0])
    driver.get(CLEAN_URL)
    w(12)

    if 'monitor/clean' not in driver.current_url:
        return []

    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
    if not iframes:
        return []

    driver.switch_to.frame(iframes[0])
    w(3)

    all_rows = []
    page = 1
    while True:
        rows = driver.execute_script("""
            var rows = document.querySelectorAll('table tr');
            var result = [];
            rows.forEach(function(row) {
                var cells = row.querySelectorAll('td');
                if (cells.length >= 4) {
                    result.push(Array.from(cells).map(c => c.innerText.trim()));
                }
            });
            return result;
        """)

        valid = [r for r in rows if len(r) >= 4 and r[0] and '-' in r[0] and r[2]]
        all_rows.extend(valid)

        # 다음 페이지 버튼 찾기
        try:
            next_page = page + 1
            next_el = driver.find_element(By.XPATH, f'//*[normalize-space(text())="{next_page}"]')
            driver.execute_script("arguments[0].click();", next_el)
            w(4)
            page += 1
        except NoSuchElementException:
            break
        except Exception:
            break

    driver.switch_to.default_content()
    return all_rows


def parse_violation_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except Exception:
        return None


def save_violations(account, rows):
    saved = 0
    skipped = 0
    for row in rows:
        if len(row) < 4:
            continue
        vdate = parse_violation_date(row[0])
        if not vdate:
            continue
        violation_type = row[1] if len(row) > 1 else ''
        product_name = row[2] if len(row) > 2 else ''
        product_id = row[3] if len(row) > 3 else ''
        nv_mid = row[4] if len(row) > 4 else ''
        note = row[5] if len(row) > 5 else ''

        if not product_id:
            continue

        _, created = SmartStoreCleanViolation.objects.update_or_create(
            account=account,
            violation_date=vdate,
            product_id=product_id,
            defaults={
                'violation_type': violation_type,
                'product_name': product_name,
                'nv_mid': nv_mid,
                'note': note,
            }
        )
        if created:
            saved += 1
        else:
            skipped += 1
    return saved, skipped


class Command(BaseCommand):
    help = '네이버 쇼핑파트너센터 클린위반 전계정 크롤링'

    def add_arguments(self, parser):
        parser.add_argument('--account-ids', nargs='+', type=int, help='특정 account id만')

    def handle(self, *args, **options):
        # 2026년 실적 있는 계정만 (login_id 기준 중복 제거)
        TARGET_IDS = [13, 7, 5, 12, 4, 10, 14, 15, 3, 6]

        if options.get('account_ids'):
            TARGET_IDS = options['account_ids']

        accounts = SmartStoreAccount.objects.filter(
            id__in=TARGET_IDS, is_active=True
        ).order_by('id')

        # login_id 기준 중복 제거 (같은 계정으로 여러 스토어 운영 시 한 번만 로그인)
        seen_login = {}
        for acc in accounts:
            if acc.login_id not in seen_login:
                seen_login[acc.login_id] = acc

        unique_accounts = list(seen_login.values())
        self.stdout.write(f'크롤링 대상: {len(unique_accounts)}개 계정')

        driver = None
        total_saved = 0
        total_errors = 0

        for i, acc in enumerate(unique_accounts):
            self.stdout.write(f'\n[{i+1}/{len(unique_accounts)}] {acc.store_name} ({acc.login_id})')

            if not acc.login_pw:
                self.stdout.write(f'  비밀번호 없음 — 스킵')
                continue

            driver = None
            try:
                driver = create_driver()
                driver.set_page_load_timeout(60)
                driver.set_window_size(1920, 1080)
                driver.implicitly_wait(2)

                ok = login(driver, acc.login_id, acc.login_pw)
                if not ok:
                    self.stdout.write(f'  로그인 실패 — 스킵')
                    total_errors += 1
                    continue
                self.stdout.write(f'  로그인 성공')

                rows = crawl_violations(driver)
                self.stdout.write(f'  수집: {len(rows)}건')

                same_login_accounts = [a for a in accounts if a.login_id == acc.login_id]
                for target_acc in same_login_accounts:
                    saved, skipped = save_violations(target_acc, rows)
                    self.stdout.write(f'  [{target_acc.store_name}] 저장={saved}, 갱신={skipped}')
                    total_saved += saved

            except Exception as e:
                self.stdout.write(f'  오류: {e}')
                total_errors += 1
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

            if i < len(unique_accounts) - 1:
                w(3)

        stop_display()

        self.stdout.write(f'\n=== 완료: 신규저장 {total_saved}건, 오류 {total_errors}건 ===')

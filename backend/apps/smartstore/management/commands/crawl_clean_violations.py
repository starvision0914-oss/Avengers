"""네이버 쇼핑파트너센터 클린위반 전계정 크롤링"""
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from apps.smartstore.models import SmartStoreAccount, SmartStoreCleanViolation

from crawlers.browser import create_driver, stop_display
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, NoSuchElementException

CLEAN_URL = 'https://center.shopping.naver.com/monitor/clean'
SS_URL = 'https://sell.smartstore.naver.com/#/home/dashboard'

# 복수스토어 계정: login_id → (ss_radio_value, account_id)
# starvis7783: 스마트스토어에서 스토어 이동 팝업 두번째 radio value
MULTI_STORE = {
    'starvis7783@gmail.com': '101489530',  # 아이리스. (account_id=7)
}


def w(n):
    time.sleep(n)


def login(driver, login_id, login_pw):
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
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[placeholder*="이메일"], input[placeholder*="아이디"]')
            )
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

    for _ in range(15):
        w(1)
        try:
            cur = driver.current_url or ''
            if 'accounts.commerce' not in cur and 'login' not in cur.lower():
                return True
        except WebDriverException:
            pass
    return False


def switch_to_iris(driver, radio_value):
    """스마트스토어 스토어 이동 팝업에서 두번째 스토어 선택"""
    try:
        driver.switch_to.window(driver.window_handles[0])
        driver.get(SS_URL)
        w(8)
        # 팝업 닫기
        for _ in range(2):
            try:
                b = driver.find_element(By.XPATH, '//button[text()="닫기" or text()="확인"]')
                driver.execute_script("arguments[0].click();", b)
                w(1)
            except Exception:
                break
        # 스토어 이동 버튼
        move_btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, '//*[contains(text(),"스토어 이동")]'))
        )
        driver.execute_script("arguments[0].click();", move_btn)
        w(5)
        # 두 번째 radio 클릭
        result = driver.execute_script("""
            var inputs = document.querySelectorAll('.modal-body input, .modal-content input');
            for (var i = 0; i < inputs.length; i++) {
                if (inputs[i].value === arguments[0]) {
                    inputs[i].click();
                    return {clicked: true, value: inputs[i].value};
                }
            }
            // fallback: 두번째 radio
            if (inputs.length >= 2) { inputs[1].click(); return {clicked: true, fallback: true}; }
            return {clicked: false};
        """, radio_value)
        w(6)
        # 쇼핑파트너센터 링크 클릭
        try:
            link = driver.find_element(By.XPATH, '//a[contains(@href,"center.shopping.naver.com")]')
            driver.execute_script("arguments[0].click();", link)
            w(8)
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
        except Exception:
            pass
        return result.get('clicked', False)
    except Exception as e:
        print(f'    스토어 이동 오류: {e}')
        return False


def crawl_violations(driver):
    """iframe 진입 후 전 페이지 클린위반 수집"""
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
                if (cells.length >= 4)
                    result.push(Array.from(cells).map(c => c.innerText.trim()));
            });
            return result;
        """)
        valid = [r for r in rows if len(r) >= 4 and r[0] and '-' in r[0] and r[2]]
        all_rows.extend(valid)
        try:
            next_el = driver.find_element(By.XPATH, f'//*[normalize-space(text())="{page + 1}"]')
            driver.execute_script("arguments[0].click();", next_el)
            w(4)
            page += 1
        except Exception:
            break

    driver.switch_to.default_content()
    return all_rows


def save_violations(account, rows):
    saved = skipped = 0
    for row in rows:
        if len(row) < 4:
            continue
        try:
            vdate = datetime.strptime(row[0].strip(), '%Y-%m-%d').date()
        except Exception:
            continue
        product_id = row[3] if len(row) > 3 else ''
        if not product_id:
            continue
        _, created = SmartStoreCleanViolation.objects.update_or_create(
            account=account,
            violation_date=vdate,
            product_id=product_id,
            defaults={
                'violation_type': row[1] if len(row) > 1 else '',
                'product_name': row[2] if len(row) > 2 else '',
                'nv_mid': row[4] if len(row) > 4 else '',
                'note': row[5] if len(row) > 5 else '',
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
        if options.get('account_ids'):
            accounts_qs = SmartStoreAccount.objects.filter(
                id__in=options['account_ids'], is_active=True
            ).order_by('display_order', 'id')
        else:
            accounts_qs = SmartStoreAccount.objects.filter(
                is_active=True
            ).order_by('display_order', 'id')

        accounts = list(accounts_qs)

        # login_id 기준 중복 제거 (같은 로그인으로 여러 스토어 운영 시 대표 1개만 로그인)
        seen_login = {}
        for acc in accounts:
            if acc.login_id not in seen_login:
                seen_login[acc.login_id] = acc

        unique_logins = list(seen_login.values())
        self.stdout.write(f'크롤링 대상: {len(accounts)}개 계정 / {len(unique_logins)}개 고유 로그인')

        total_saved = 0
        total_errors = 0

        for i, acc in enumerate(unique_logins):
            name = acc.display_name or acc.store_name
            self.stdout.write(f'\n[{i+1}/{len(unique_logins)}] {name} ({acc.login_id})')

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

                # 복수스토어: 스마트스토어센터에서 해당 스토어로 전환 후 파트너센터 접속
                radio_value = MULTI_STORE.get(acc.login_id)
                if radio_value:
                    switched = switch_to_iris(driver, radio_value)
                    self.stdout.write(f'  스토어 전환: {"성공" if switched else "실패(기본스토어로 진행)"}')

                rows = crawl_violations(driver)
                self.stdout.write(f'  수집: {len(rows)}건')

                # 같은 login_id의 모든 계정에 저장
                same_login_accounts = [a for a in accounts if a.login_id == acc.login_id]
                for target_acc in same_login_accounts:
                    saved, skipped = save_violations(target_acc, rows)
                    tname = target_acc.display_name or target_acc.store_name
                    self.stdout.write(f'  [{tname}] 저장={saved}, 갱신={skipped}')
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

            if i < len(unique_logins) - 1:
                w(3)

        stop_display()
        self.stdout.write(f'\n=== 완료: 신규저장 {total_saved}건, 오류 {total_errors}건 ===')

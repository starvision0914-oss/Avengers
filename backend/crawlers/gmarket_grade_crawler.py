"""
지마켓 셀러 등급 크롤러 — ai100 gmarket_seller_grade.py 이식
- ESM Plus (www.esmplus.com) 로그인 → 대시보드 "내 판매 정보"
- 드롭다운 셀러 선택 → AJAX 대기 → CSS selector 파싱
- 매 계정마다 driver 재생성 (안정성)
- 옥션 셀러는 건너뜀 (G마켓만)
"""
import re
import time
import logging
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .browser import create_driver, stop_display, _kill_stale_chrome
from .utils import parse_int

logger = logging.getLogger('crawler')
LOGIN_URL = 'https://signin.esmplus.com/login'


def _parse_max_items(text):
    cleaned = re.sub(r'[^\d]', '', str(text or ''))
    return int(cleaned) if cleaned else None


def _login(driver, login_id, password):
    driver.get(LOGIN_URL)
    time.sleep(2)
    try:
        driver.find_element(By.CSS_SELECTOR, '.button__tab--gmarket').click()
        time.sleep(0.5)
        driver.find_element(By.ID, 'typeMemberInputId01').clear()
        driver.find_element(By.ID, 'typeMemberInputId01').send_keys(login_id)
        driver.find_element(By.ID, 'typeMemberInputPassword01').clear()
        driver.find_element(By.ID, 'typeMemberInputPassword01').send_keys(password)
        for btn in driver.find_elements(By.TAG_NAME, 'button'):
            if '로그인' in (btn.text or ''):
                btn.click()
                break
        time.sleep(3)
        return 'signin' not in driver.current_url.lower()
    except Exception as e:
        logger.error(f'[GM등급:{login_id}] 로그인 실패: {e}')
        return False


def _close_popups(driver):
    """ai100 패턴: JS로 모든 모달/팝업 닫기"""
    driver.execute_script("""
        document.querySelectorAll('.popup-close, [class*="close"], button').forEach(function(el) {
            if (el.offsetParent !== null && el.offsetHeight > 5) {
                var text = el.textContent.trim();
                if (text === '×' || text === 'X' || text === '닫기' || el.className.includes('close')) {
                    try { el.click(); } catch(e) {}
                }
            }
        });
        document.querySelectorAll('.layer-close, .btn-layer-close').forEach(function(el) {
            try { el.click(); } catch(e) {}
        });
    """)
    time.sleep(0.5)
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except Exception:
        pass


def _collect_grades(driver, login_id, log_fn=None):
    """ai100 패턴: 대시보드 "내 판매 정보" 에서 등급 수집"""
    def log(msg):
        logger.info(f'[GM등급:{login_id}] {msg}')
        if log_fn: log_fn(f'[GM등급:{login_id}] {msg}')

    results = []
    _close_popups(driver)

    # "내 판매 정보" 섹션 찾기
    try:
        my_info = driver.find_element(By.XPATH, "//h3[contains(text(),'내 판매 정보')]")
    except Exception:
        log('"내 판매 정보" 섹션 미발견')
        return results

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", my_info)
    time.sleep(0.5)

    info_container = driver.execute_script(
        "return arguments[0].closest('.box__column-half') || arguments[0].closest('.box');",
        my_info
    )
    if not info_container:
        log('컨테이너 미발견')
        return results

    # 드롭다운 열기
    dropdown = driver.execute_script("""
        var container = arguments[0];
        var btns = container.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.includes('선택') || btns[i].classList.contains('button__opener')) {
                return btns[i];
            }
        }
        return null;
    """, info_container)

    if not dropdown:
        # 싱글 셀러: 드롭다운 없이 직접 추출
        try:
            items = info_container.find_elements(By.CSS_SELECTOR, '.list__info-sale .list-item')
            if len(items) >= 4:
                grade = items[0].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                max_items = _parse_max_items(items[1].find_element(By.CSS_SELECTOR, '.text__info').text)
                approval = items[2].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                expiry = items[3].find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                results.append({
                    'gmarket_id': login_id, 'seller_id': login_id,
                    'seller_grade': grade, 'max_item_count': max_items,
                    'approval_status': approval, 'contact_expiry': expiry,
                    'collected_at': timezone.now(),
                })
                log(f'{login_id}: 등급={grade} 최대수량={max_items}')
        except Exception as e:
            log(f'싱글 셀러 추출 실패: {e}')
        return results

    # 드롭다운 클릭 → 옵션 로딩
    driver.execute_script("arguments[0].click();", dropdown)
    time.sleep(1)

    # G마켓 옵션만 (옥션 제외)
    options = info_container.find_elements(By.CSS_SELECTOR, 'ul[role="listbox"] li button[role="option"]')
    gmarket_options = []
    for opt in options:
        gm_span = opt.find_elements(By.CSS_SELECTOR, '.text--gmarket')
        if gm_span:
            text = opt.text.strip()
            seller_id = text.replace('G', '').replace('선택됨', '').strip()
            gmarket_options.append((opt, seller_id))

    log(f'G마켓 셀러 {len(gmarket_options)}개')

    # 드롭다운 닫기
    driver.execute_script("arguments[0].click();", dropdown)
    time.sleep(0.3)

    for i, (opt_ref, seller_id) in enumerate(gmarket_options):
        try:
            # 드롭다운 열기
            driver.execute_script("arguments[0].click();", dropdown)
            time.sleep(1)

            # 옵션 다시 찾기 (DOM 변경)
            options = info_container.find_elements(By.CSS_SELECTOR, 'ul[role="listbox"] li button[role="option"]')
            target = None
            for o in options:
                gm_span = o.find_elements(By.CSS_SELECTOR, '.text--gmarket')
                if gm_span and seller_id in o.text:
                    target = o
                    break

            if not target:
                log(f'{seller_id}: 옵션 미발견')
                driver.execute_script("arguments[0].click();", dropdown)
                continue

            driver.execute_script("arguments[0].click();", target)
            time.sleep(3)

            # AJAX 데이터 로딩 대기 (최대 10회 × 2초)
            grade, max_items, approval, expiry = '', None, '', ''
            for attempt in range(10):
                items = info_container.find_elements(By.CSS_SELECTOR, '.list__info-sale .list-item')
                if len(items) >= 4:
                    try:
                        label0 = items[0].find_element(By.CSS_SELECTOR, '.box__left .text, .text__label').text.strip()
                    except Exception:
                        label0 = ''

                    for item in items:
                        try:
                            label = item.find_element(By.CSS_SELECTOR, '.box__left .text, .text__label').text.strip()
                        except Exception:
                            continue
                        try:
                            value = item.find_element(By.CSS_SELECTOR, '.text__info').text.strip()
                        except Exception:
                            value = ''

                        if '판매등급' in label:
                            grade = value
                        elif '판매가능' in label and '수량' in label:
                            max_items = _parse_max_items(value)
                        elif '판매승인' in label:
                            approval = value
                        elif '연락처' in label and '인증' in label:
                            expiry = value

                    if grade and max_items is not None:
                        break
                time.sleep(2)

            results.append({
                'gmarket_id': login_id, 'seller_id': seller_id,
                'seller_grade': grade, 'max_item_count': max_items,
                'approval_status': approval, 'contact_expiry': expiry,
                'collected_at': timezone.now(),
            })
            log(f'{seller_id}: 등급={grade} 최대수량={max_items}')

        except Exception as e:
            log(f'{seller_id} 실패: {e}')

    return results


def run_all_accounts(log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, GmarketSellerGrade, CrawlerLog
    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
    if account_filter:
        qs = qs.filter(login_id__in=account_filter)
    if not qs.exists():
        if log_fn: log_fn('활성 지마켓 계정 없음')
        return {'collected': 0, 'failed': 0}

    all_grades = []

    for acct in qs:
        if acct.crawling_status == '차단됨':
            if log_fn: log_fn(f'[GM등급:{acct.login_id}] 차단됨 - 건너뜀')
            continue

        driver = None
        try:
            _kill_stale_chrome()
            driver = create_driver()
            if _login(driver, acct.login_id, acct.password_enc):
                time.sleep(2)
                _close_popups(driver)
                grades = _collect_grades(driver, acct.login_id, log_fn)
                all_grades.extend(grades)
            else:
                if log_fn: log_fn(f'[GM등급:{acct.login_id}] 로그인 실패')
        except Exception as e:
            if log_fn: log_fn(f'[GM등급:{acct.login_id}] 오류: {e}')
        finally:
            if driver:
                try: driver.quit()
                except: pass
    stop_display()

    for g in all_grades:
        GmarketSellerGrade.objects.create(**g)

    CrawlerLog.objects.create(platform='gmarket', level='info', message=f'등급 수집: {len(all_grades)}건')
    if log_fn: log_fn(f'지마켓 등급 수집 완료: {len(all_grades)}건')
    return {'collected': len(all_grades), 'failed': 0}

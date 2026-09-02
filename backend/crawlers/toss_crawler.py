"""토스쇼핑 파트너스(shopping-seller.toss.im) 광고비 수집.

로그인은 토스 계정(이메일/비밀번호) 그대로 사용, 광고센터 별도 로그인 없음(2026-09-02 실측, 2FA 없음).
/ads 페이지에서 기간 프리셋 버튼(오늘/어제)을 눌러 "전체 캠페인" 표를 스크래핑한다.
표의 앞쪽 칸 수(상태/ID/캠페인명 뒤)는 알림배지 유무로 흔들리지만, 뒤에서부터 14칸
(집행광고비~종료일)은 항상 고정 순서라 뒤에서부터 슬라이스해 매핑한다(2026-09-02 실측 확인).
계정 합계(TossAdCost)는 별도 파싱 없이 캠페인별 합으로 계산한다.
"""
import re
import time
import logging
import datetime

from django.utils import timezone

from apps.cpc import eleven_block_guard as guard
from apps.toss.models import TossAccount, TossAdCost, TossCampaignAdCost

logger = logging.getLogger('crawler')

LOGIN_URL = 'https://shopping-seller.toss.im/login?redirectTo=%2Fads'
ADS_URL = 'https://shopping-seller.toss.im/ads'


def _int(s):
    s = re.sub(r'[^\d-]', '', str(s or ''))
    return int(s) if s not in ('', '-') else 0


def _pct(s):
    m = re.search(r'-?[\d.]+', str(s or ''))
    return float(m.group()) if m else 0.0


def _clean_name(s):
    return re.sub(r'(일별\s*성과|수정|삭제)+$', '', str(s or '')).strip()


def _close_popup(driver):
    for xp in ["//button[.//text()='확인']", "//div[contains(@class,'Toast')]//button",
               "//*[local-name()='svg' and @data-testid='CloseIcon']/.."]:
        try:
            els = driver.find_elements('xpath', xp)
            for e in els:
                if e.is_displayed():
                    driver.execute_script("arguments[0].click();", e)
        except Exception:
            pass


def _login(driver, account):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    driver.get(LOGIN_URL)
    time.sleep(3)
    if 'login' not in driver.current_url:
        return True
    inputs = driver.find_elements(By.TAG_NAME, 'input')
    email_input = next((i for i in inputs if i.get_attribute('placeholder') and '이메일' in i.get_attribute('placeholder')), None)
    pw_input = next((i for i in inputs if i.get_attribute('type') == 'password'), None)
    if not email_input or not pw_input:
        return False
    email_input.click(); email_input.send_keys(account.login_id)
    pw_input.click(); pw_input.send_keys(account.login_pw)
    pw_input.send_keys(Keys.ENTER)
    time.sleep(5)
    return 'login' not in driver.current_url


def _click_preset(driver, label):
    from selenium.webdriver.common.by import By
    els = driver.find_elements(By.XPATH, f"//button[normalize-space()='{label}'] | //div[normalize-space()='{label}']")
    for e in els:
        if e.is_displayed():
            driver.execute_script("arguments[0].click();", e)
            return True
    return False


def _scrape_key_metric(driver, label):
    """'주요 성과' 카드에서 라벨 옆 값을 읽는다 — 계정 전체 유효광고수익률은 캠페인별 합산 비율과
    달라(가중/기간 attribution 차이로 추정, 2026-09-02 실측: 8,483원/36,300원인데 카드는 462.15%,
    단순비율은 427.9%) 카드값을 그대로 신뢰한다."""
    try:
        els = driver.find_elements(
            'xpath', f"//*[contains(text(),'{label}') and (self::div or self::span)]")
        for e in els:
            card = e.find_element('xpath', '../..')
            lines = [ln.strip() for ln in card.text.split('\n') if ln.strip()]
            for ln in reversed(lines):
                if ln != label and re.search(r'[\d%원]', ln):
                    return ln
    except Exception:
        pass
    return None


def _scrape_campaign_table(driver):
    """반환: [{status, campaign_id, campaign_name, exec_ad_cost, ...}, ...]"""
    rows = driver.execute_script("""
    const table = document.querySelector('table');
    if (!table) return [];
    return Array.from(table.querySelectorAll('tbody tr')).map(
        r => Array.from(r.querySelectorAll('td')).map(td => td.innerText.trim())
    );
    """)
    out = []
    for cells in rows:
        if len(cells) < 17 or not cells[0] or cells[0].startswith('전체'):
            continue
        tail = cells[-14:]
        out.append({
            'status': cells[0],
            'campaign_id': cells[1],
            'campaign_name': _clean_name(cells[2]),
            'exec_ad_cost': _int(tail[0]),
            'conversion_amount': _int(tail[1]),
            'effective_roas': _pct(tail[2]),
            'impressions': _int(tail[3]),
            'clicks': _int(tail[4]),
            'ctr': _pct(tail[5]),
            'conv_qty': _int(tail[8]),
            'conv_orders': _int(tail[9]),
            'conv_rate': _pct(tail[10]),
            'cpc': _int(tail[11]),
            'start_date': tail[12],
            'end_date': tail[13],
        })
    return out


def collect_daily(account, when='yesterday', log_fn=None):
    """when: 'yesterday' | 'today' — 해당 프리셋 버튼 기준 1일치 수집."""
    import os
    os.environ.setdefault('DISPLAY', ':99')
    from crawlers.browser import create_driver

    ok, reason = guard.preflight(f'toss_ad_cost:{account.login_id}', wait=True, platform='toss')
    if not ok:
        msg = f'[toss:{account.login_id}] 전역락/접속 불가 — {reason}'
        logger.info(msg)
        if log_fn:
            log_fn(msg)
        return False

    label = '어제' if when == 'yesterday' else '오늘'
    target_date = datetime.date.today() - datetime.timedelta(days=1 if when == 'yesterday' else 0)

    driver = None
    try:
        driver = create_driver(user_data_dir=f'/tmp/toss_profiles/{account.login_id}', kill_existing=False)
        if not _login(driver, account):
            account.fail_count += 1
            account.save(update_fields=['fail_count'])
            logger.info(f'[toss:{account.login_id}] 로그인 실패')
            return False
        driver.get(ADS_URL)
        time.sleep(4)
        _close_popup(driver)
        _click_preset(driver, label)
        time.sleep(2)
        _close_popup(driver)

        campaigns = _scrape_campaign_table(driver)
        total_cost = sum(c['exec_ad_cost'] for c in campaigns)
        total_conv = sum(c['conversion_amount'] for c in campaigns)
        total_imp = sum(c['impressions'] for c in campaigns)
        total_click = sum(c['clicks'] for c in campaigns)
        card_roas = _pct(_scrape_key_metric(driver, '유효 광고 수익률'))
        total_roas = card_roas if card_roas else (round(total_conv / total_cost * 100, 2) if total_cost else 0)

        TossAdCost.objects.update_or_create(
            account=account, date=target_date,
            defaults={
                'exec_ad_cost': total_cost, 'conversion_amount': total_conv,
                'effective_roas': total_roas, 'impressions': total_imp, 'clicks': total_click,
            },
        )
        for c in campaigns:
            TossCampaignAdCost.objects.update_or_create(
                account=account, date=target_date, campaign_id=c['campaign_id'],
                defaults={k: v for k, v in c.items() if k not in ('campaign_id',)},
            )

        account.last_crawled_at = timezone.now()
        account.fail_count = 0
        account.save(update_fields=['last_crawled_at', 'fail_count'])
        msg = f'[toss:{account.login_id}] {target_date} 집행광고비 {total_cost:,}원 (캠페인 {len(campaigns)}개)'
        logger.info(msg)
        if log_fn:
            log_fn(msg)
        return True
    except Exception as e:
        account.fail_count += 1
        account.save(update_fields=['fail_count'])
        logger.exception(f'[toss:{account.login_id}] 수집 오류: {e}')
        if log_fn:
            log_fn(f'[toss:{account.login_id}] 오류: {e}')
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        guard.release_global_lock(platform='toss')


def collect_all(when='yesterday'):
    results = {}
    for account in TossAccount.objects.filter(is_active=True).order_by('display_order', 'id'):
        results[account.login_id] = collect_daily(account, when=when)
    return results

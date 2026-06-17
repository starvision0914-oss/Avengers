"""
11번가 passwordCampaign 페이지 HTML 캡처 (우회 셀렉터 찾기용)
"""
import time
from pathlib import Path
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '11번가 비밀번호 캠페인 페이지 HTML 캡처'

    def add_arguments(self, parser):
        parser.add_argument('--account', required=True)

    def handle(self, *args, **options):
        from apps.cpc.models import CrawlerAccount
        from crawlers.browser import create_driver, stop_display
        from selenium.webdriver.common.by import By

        acc = CrawlerAccount.objects.filter(platform='11st', login_id=options['account']).first()
        if not acc:
            self.stdout.write(self.style.ERROR('계정 없음'))
            return

        driver = create_driver()
        try:
            # 로그인
            driver.get('https://login.11st.co.kr/auth/front/selleroffice/login.tmall')
            time.sleep(3)
            driver.find_element(By.ID, 'loginName').send_keys(acc.login_id)
            driver.find_element(By.ID, 'passWord').send_keys(acc.password_enc)
            driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
            time.sleep(5)

            # alert 처리
            try:
                a = driver.switch_to.alert
                self.stdout.write(f'alert: {a.text}')
                a.accept()
                time.sleep(1)
            except Exception:
                pass

            url = driver.current_url
            self.stdout.write(f'\n현재 URL: {url}')

            dbg = Path('/tmp/avengers_otp_debug')
            dbg.mkdir(exist_ok=True)
            ts = int(time.time())
            (dbg / f'campaign_{acc.login_id}_{ts}.html').write_text(driver.page_source, encoding='utf-8')
            driver.save_screenshot(str(dbg / f'campaign_{acc.login_id}_{ts}.png'))
            self.stdout.write(f'\nHTML 저장: campaign_{acc.login_id}_{ts}.html')

            # 페이지에서 버튼/링크 텍스트 추출
            import re
            page = driver.page_source
            self.stdout.write('\n=== 모든 button/a 텍스트 ===')
            for m in re.finditer(r'<(?:button|a)[^>]*>([^<]{2,40})</(?:button|a)>', page):
                t = m.group(1).strip()
                if t and not t.startswith('&'):
                    self.stdout.write(f'  - {t!r}')
        finally:
            try:
                driver.quit()
            except Exception:
                pass
            stop_display()

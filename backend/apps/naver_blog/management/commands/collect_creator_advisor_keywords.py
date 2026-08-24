"""
크리에이터 어드바이저(creator-advisor.naver.com) '주제별 인기유입검색어' 수집.
(2026-08-24) 데이터가 있는 가장 최근 날짜를 자동으로 찾아(최대 --max-back 일 전까지 '이전 기간 조회'
로 거슬러 올라감), 그날 노출된 전체 카테고리(맛집/국내여행 등)의 키워드를 전부 NaverKeyword에
추가한다. keyword 필드가 unique=True라 get_or_create로 자연스럽게 중복 제거됨.
추가 직후 collect_naver_keywords(전체 활성)를 이어서 호출해 경쟁도까지 자동 수집.

사용: python manage.py collect_creator_advisor_keywords [--login-id rejoice888] [--max-back 10]
"""
import time

from django.core.management.base import BaseCommand
from django.core.management import call_command

from apps.naver_blog.models import NaverBlogAccount, NaverKeyword


class Command(BaseCommand):
    help = '크리에이터 어드바이저 주제별 인기유입검색어 수집 → 키워드 등록 → 경쟁도 수집'

    def add_arguments(self, parser):
        parser.add_argument('--login-id', type=str, default='rejoice888')
        parser.add_argument('--max-back', type=int, default=10, help='데이터 있는 날짜 찾을 때 최대 며칠 전까지 거슬러갈지')
        parser.add_argument('--skip-competition', action='store_true', help='경쟁도 수집 생략(키워드 추가만)')

    def handle(self, *args, **options):
        from crawlers.browser import create_driver, stop_display
        from crawlers.naver_blog_crawler import ensure_login
        from selenium.webdriver.common.by import By

        login_id = options['login_id']
        max_back = options['max_back']

        account = NaverBlogAccount.objects.get(login_id=login_id)
        driver = create_driver()
        try:
            ok = ensure_login(driver, account, log_fn=self.stdout.write)
            if not ok:
                self.stdout.write(self.style.ERROR('로그인 실패 — 수동 로그인 필요(naver_blog_manual_login_wait.py)'))
                return

            driver.get(f'https://creator-advisor.naver.com/naver_blog/{login_id}/trends')
            time.sleep(4)

            used_date = None
            keywords = []
            for attempt in range(max_back + 1):
                try:
                    date_el = driver.find_element(
                        By.XPATH,
                        '/html/body/div[1]/div/div/div[2]/div[1]/div/div[1]/div[1]/div/div/span')
                    used_date = date_el.text
                except Exception:
                    used_date = None

                try:
                    # 실측 구조(2026-08-24): '주제별'/'성별,연령별' 헤더는 같은 탭바(자식[0])에 나란히
                    # 있고, following::/ancestor:: 만으로는 두 섹션을 구분 못 함(같은 공통조상 아래
                    # 뒤섞임). 대신 공통조상(div[5])의 '직계자식' 중 트렌드 항목을 가진 첫 번째
                    # 블록이 주제별, 두 번째가 성별·연령별로 고정 순서라 인덱스로 구분한다.
                    topic_header = driver.find_element(By.XPATH, "//*[contains(text(),'주제별 인기유입검색어')]")
                    common = topic_header.find_element(By.XPATH, "ancestor::div[5]")
                    content_blocks = [
                        c for c in common.find_elements(By.XPATH, "./*")
                        if c.find_elements(By.CLASS_NAME, 'u_ni_trend_text')
                    ]
                    if not content_blocks:
                        raise Exception('트렌드 콘텐츠 블록 없음')
                    topic_block = content_blocks[0]
                    texts = topic_block.find_elements(By.CLASS_NAME, 'u_ni_trend_text')
                    keywords = [t.text.strip() for t in texts if t.text.strip()]
                except Exception as e:
                    self.stdout.write(f'섹션 파싱 실패({used_date}): {e}')
                    keywords = []

                if keywords:
                    self.stdout.write(f'{used_date}: 키워드 {len(keywords)}개 발견')
                    break

                self.stdout.write(f'{used_date}: 데이터 없음 — 이전 기간으로 이동 ({attempt + 1}/{max_back})')
                try:
                    prev_btn = driver.find_element(By.XPATH, "//*[contains(text(),'이전 기간 조회')]")
                    driver.execute_script("arguments[0].click();", prev_btn)
                    time.sleep(3.5)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'이전기간 버튼 없음 — 중단: {e}'))
                    break

            if not keywords:
                self.stdout.write(self.style.WARNING(f'{max_back}일 내 데이터를 찾지 못함'))
                return

        finally:
            try:
                driver.quit()
            except Exception:
                pass
            stop_display()

        uniq_keywords = sorted(set(keywords))
        created, updated = 0, 0
        for kw in uniq_keywords:
            obj, was_created = NaverKeyword.objects.get_or_create(
                keyword=kw, defaults={'category': '크리에이터어드바이저', 'is_active': True})
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'[{used_date}] 총 {len(uniq_keywords)}개 키워드(중복제거 후) — 신규 {created}건 / 기존 {updated}건'))

        if not options['skip_competition']:
            self.stdout.write('경쟁도 수집 시작(전체 활성 키워드 대상)...')
            call_command('collect_naver_keywords')

"""
지마켓 과거 광고비 수집 (2024-01 ~ 현재)
- ad.esmplus.com/cpc/Report/DailyReport 기간조회
- 계정별 월별 일별 데이터 테이블 파싱 → DB 저장
- 9시 전에 자동 중단
"""
import os
import time
import logging
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger('crawler')


class Command(BaseCommand):
    help = '지마켓 과거 광고비 일별 데이터 수집 (2024-01 ~ 현재)'

    def add_arguments(self, parser):
        parser.add_argument('--start', default='2024-01', help='시작 년월 (YYYY-MM)')
        parser.add_argument('--end', default=None, help='종료 년월 (기본: 현재)')
        parser.add_argument('--accounts', nargs='*', help='특정 계정만')
        parser.add_argument('--stop-hour', type=int, default=9, help='이 시(KST) 되면 중단 (기본 9)')

    def handle(self, *args, **options):
        from apps.cpc.models import CrawlerAccount, GmarketDepositSnapshot, CrawlerLog
        from crawlers.browser import create_driver, stop_display, _kill_stale_chrome
        from crawlers.gmarket_crawler import _try_cookie_login, _full_login, _save_cookies
        from selenium.webdriver.common.by import By
        import pytz

        kst = pytz.timezone('Asia/Seoul')
        stop_hour = options['stop_hour']
        start_str = options['start']
        end_str = options['end'] or date.today().strftime('%Y-%m')

        start_date = datetime.strptime(start_str, '%Y-%m').date()
        end_date = datetime.strptime(end_str, '%Y-%m').date()

        # 월 리스트 생성
        months = []
        d = start_date
        while d <= end_date:
            months.append(d)
            d += relativedelta(months=1)

        accounts = CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
        if options.get('accounts'):
            accounts = accounts.filter(login_id__in=options['accounts'])
        accounts = accounts.exclude(crawling_status='차단됨')

        dl_dir = '/tmp/avengers_gm_history_downloads'
        os.makedirs(dl_dir, exist_ok=True)

        self.stdout.write(f'계정 {accounts.count()}개 × {len(months)}개월 = {accounts.count() * len(months)}회 조회')
        self.stdout.write(f'{stop_hour}시 전까지 수집')

        total_saved = 0

        for acct in accounts:
            # 시간 체크
            now_kst = datetime.now(kst)
            if now_kst.hour >= stop_hour:
                self.stdout.write(self.style.WARNING(f'{stop_hour}시 도달 — 중단'))
                break

            driver = None
            try:
                _kill_stale_chrome()
                time.sleep(1)
                driver = create_driver()

                # 로그인
                if not _try_cookie_login(driver, acct):
                    from crawlers.gmarket_crawler import _full_login as gm_login
                    if not gm_login(driver, acct.login_id, acct.password_enc):
                        self.stdout.write(f'[{acct.login_id}] 로그인 실패')
                        continue
                    _save_cookies(driver, acct)

                for month_date in months:
                    # 시간 체크
                    if datetime.now(kst).hour >= stop_hour:
                        self.stdout.write(self.style.WARNING(f'{stop_hour}시 도달 — 중단'))
                        break

                    year = month_date.year
                    month = month_date.month
                    # 해당 월의 마지막 날
                    if month == 12:
                        last_day = 31
                    else:
                        last_day = (date(year, month + 1, 1) - timedelta(days=1)).day

                    try:
                        # 리포트 페이지
                        driver.get('https://ad.esmplus.com/cpc/Report/DailyReport')
                        time.sleep(4)

                        # datepicker 열기
                        driver.find_element(By.CSS_SELECTOR, '.daterangepicker_field').click()
                        time.sleep(1)

                        # 년/월 선택 (왼쪽 달력 헤더 클릭)
                        titles = driver.find_elements(By.CSS_SELECTOR, '.ui-datepicker-title')
                        if titles:
                            titles[0].click()
                            time.sleep(0.5)

                        # 년도
                        for y in driver.find_element(By.ID, 'selectBoxYear').find_elements(By.TAG_NAME, 'li'):
                            if str(year) in y.text:
                                y.click()
                                break
                        time.sleep(0.3)

                        # 월
                        month_text = f'{month}월'
                        for m in driver.find_element(By.ID, 'selectBoxMonth').find_elements(By.TAG_NAME, 'li'):
                            if m.text.strip() == month_text:
                                m.click()
                                break
                        time.sleep(0.3)

                        # 1일 클릭
                        for d in driver.find_elements(By.CSS_SELECTOR, '.ui-datepicker-calendar td a'):
                            if d.text.strip() == '1':
                                d.click()
                                break
                        time.sleep(0.3)

                        # 마지막 날 클릭
                        for d in reversed(driver.find_elements(By.CSS_SELECTOR, '.ui-datepicker-calendar td a')):
                            if d.text.strip() == str(last_day):
                                d.click()
                                break
                        time.sleep(0.3)

                        # 적용
                        driver.find_element(By.CSS_SELECTOR, '.btn_apply').click()
                        time.sleep(1)

                        # 조회
                        driver.execute_script("ReportList.GetTotalSearch();")
                        time.sleep(6)

                        # 엑셀 다운로드
                        dl_dir_acct = os.path.join(dl_dir, acct.login_id)
                        os.makedirs(dl_dir_acct, exist_ok=True)
                        # 기존 파일 정리
                        import glob as _glob
                        for f in _glob.glob(f'{dl_dir_acct}/*'):
                            os.remove(f)

                        driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                            'behavior': 'allow', 'downloadPath': dl_dir_acct,
                        })
                        driver.execute_script("ReportList.ExcelDown('Day');")

                        # 다운로드 대기 (최대 30초)
                        filepath = None
                        for _ in range(30):
                            time.sleep(1)
                            files = [f for f in _glob.glob(f'{dl_dir_acct}/*') if not f.endswith('.crdownload')]
                            if files:
                                filepath = files[0]
                                break

                        month_saved = 0
                        if filepath:
                            # 엑셀 파싱
                            try:
                                # xlsx (openpyxl) 또는 xls (xlrd)
                                all_rows = []
                                if filepath.endswith('.xlsx'):
                                    import openpyxl
                                    wb = openpyxl.load_workbook(filepath)
                                    ws_sheet = wb.active
                                    all_rows = list(ws_sheet.iter_rows(values_only=True))
                                else:
                                    import xlrd
                                    wk = xlrd.open_workbook(filepath)
                                    ws_sheet = wk.sheet_by_index(0)
                                    all_rows = [ws_sheet.row_values(i) for i in range(ws_sheet.nrows)]

                                if not all_rows:
                                    continue

                                # 헤더 행 찾기
                                header_idx = 0
                                for i, row in enumerate(all_rows[:10]):
                                    row_text = ' '.join(str(c or '') for c in row)
                                    if '날짜' in row_text or '일자' in row_text or 'Date' in row_text or '노출수' in row_text:
                                        header_idx = i
                                        break

                                headers = [str(c or '').strip() for c in all_rows[header_idx]]

                                for row in all_rows[header_idx + 1:]:
                                    if not any(str(c).strip() for c in row):
                                        continue

                                    date_text = str(row[0]).strip()
                                    if not date_text or str(year) not in date_text:
                                        continue

                                    def parse_num(t):
                                        c = str(t).replace(',', '').replace('원', '').replace('%', '').strip()
                                        try: return int(float(c))
                                        except: return 0

                                    # 비용 컬럼 찾기
                                    cost_idx = None
                                    for hi, h in enumerate(headers):
                                        if '비용' in h or '광고비' in h or 'cost' in h.lower():
                                            cost_idx = hi
                                            break

                                    cost = parse_num(row[cost_idx]) if cost_idx and cost_idx < len(row) else 0
                                    clicks = parse_num(row[2]) if len(row) > 2 else 0
                                    impressions = parse_num(row[1]) if len(row) > 1 else 0

                                    try:
                                        dt = datetime.strptime(date_text[:10], '%Y-%m-%d')
                                    except:
                                        continue

                                    collected_at = kst.localize(datetime.combine(dt, datetime.min.time()))

                                    exists = GmarketDepositSnapshot.objects.filter(
                                        gmarket_id=acct.login_id,
                                        collected_at__date=dt.date(),
                                    ).exists()
                                    if not exists:
                                        GmarketDepositSnapshot.objects.create(
                                            gmarket_id=acct.login_id,
                                            total_balance=0,
                                            cash_balance=0, card_balance=0,
                                            ad_balance=0, event_balance=0,
                                            gmarket_cpc=cost,
                                            auction_cpc=0, ai_usage=0,
                                            total_usage=cost,
                                            collected_at=collected_at,
                                        )
                                        month_saved += 1
                            except Exception as pe:
                                self.stdout.write(f'[{acct.login_id}] 파싱 오류: {pe}')
                        else:
                            self.stdout.write(f'[{acct.login_id}] {year}-{month:02d} 다운로드 실패')

                        total_saved += month_saved
                        self.stdout.write(f'[{acct.login_id}] {year}-{month:02d}: {month_saved}건')

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'[{acct.login_id}] {year}-{month:02d} 오류: {str(e)[:60]}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[{acct.login_id}] 오류: {str(e)[:60]}'))
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass

        stop_display()
        self.stdout.write(self.style.SUCCESS(f'총 {total_saved}건 저장'))

"""rejoice234 로그인 → 234/235/236 각각 2026-01-01~01-31 검색 → 그리드 금액 라이브 확인."""
import os, re, time, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from crawlers.browser import create_driver
from crawlers.gmarket_cost_crawler import _esm_login
from apps.cpc.models import CrawlerAccount

def drain(d):
    try: a=d.switch_to.alert; t=a.text; a.accept(); return t
    except NoAlertPresentException: return None
    except Exception: return None

acc = CrawlerAccount.objects.get(platform='gmarket', login_id='rejoice234')
d = create_driver(kill_existing=False)
try:
    print('로그인:', _esm_login(d, 'rejoice234', acc.password_enc), flush=True)
    d.get('https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'); time.sleep(4)
    AD = ('CPC 광고구매', 'AI매출업 광고구매')
    for sid in ['rejoice234', 'rejoice235', 'rejoice236']:
        try: Select(d.find_element(By.ID, 'sellerId')).select_by_value(sid); time.sleep(0.5)
        except Exception as e: print(f'{sid} 선택실패 {e}', flush=True); continue
        for fid, val in [('searchSDT', '2026-01-01'), ('searchEDT', '2026-01-31')]:
            d.execute_script(f"var e=document.getElementById('{fid}');if(e){{e.value='{val}';e.dispatchEvent(new Event('change'));}}")
        try: d.find_element(By.XPATH, '//*[@id="btnSearch"]/img').click()
        except UnexpectedAlertPresentException: pass
        drain(d); time.sleep(2)
        rows = d.find_elements(By.CSS_SELECTOR, '#grid_sortingData tr')
        total = ad_amt = ad_cnt = cnt = 0
        for tr in rows:
            tds = [(td.text or '').strip() for td in tr.find_elements(By.TAG_NAME, 'td')]
            if len(tds) < 10 or not re.search(r'2026-\d\d-\d\d', tds[1]): continue
            cnt += 1
            amt = int(re.sub(r'[^\d-]', '', tds[2]) or 0)
            cm = tds[7] or tds[5] or ''
            if any(k in cm for k in AD):
                ad_amt += amt; ad_cnt += 1
        print(f'[{sid}] 2026-01 그리드: 전체 {cnt}건 / 광고 {ad_cnt}건 / 광고비 {abs(ad_amt):,}원', flush=True)
finally:
    try: d.quit()
    except Exception: pass
print('=== DONE ===', flush=True)

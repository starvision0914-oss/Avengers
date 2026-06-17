"""지마켓 판매예치금 거래내역을 복수아이디 id별로 수집 (ai100 방식).
마스터 로그인 → GmktSellBalanceManagement → sellerId 드롭다운의 각 서브 선택 →
월별(1개월 제한) 검색 → grid_sortingData 그리드 스크랩 → GmarketCostHistory(market='gmarket') 저장.
실행: python -c "import crawlers.collect_gmkt_balance" [마스터...]"""
import os, sys, re, time, calendar, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from datetime import date
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from django.utils import timezone
from crawlers.browser import create_driver, stop_display
from crawlers.gmarket_cost_crawler import _esm_login, _classify
from apps.cpc.models import CrawlerAccount, GmarketCostHistory

YEAR = 2026
GMKT_PAGE = 'https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'

def _drain_alert(d):
    try:
        a = d.switch_to.alert; t = a.text; a.accept(); return t
    except NoAlertPresentException: return None
    except Exception: return None

def _months(year, upto_month):
    out = []
    for m in range(1, upto_month + 1):
        last = calendar.monthrange(year, m)[1]
        out.append((date(year, m, 1), date(year, m, last)))
    return out

def _scrape_month(d, sub, sdt, edt):
    """1개월 조회 → grid_sortingData 거래행 파싱. 반환 [(dt_date, use_type, ttype, comment, amount, related), ...]"""
    for fid, val in [('searchSDT', sdt.isoformat()), ('searchEDT', edt.isoformat())]:
        d.execute_script(f"var e=document.getElementById('{fid}');if(e){{e.value='{val}';e.dispatchEvent(new Event('change'));}}")
    try:
        d.find_element(By.XPATH, '//*[@id="btnSearch"]/img').click()
    except UnexpectedAlertPresentException:
        pass
    _drain_alert(d)
    time.sleep(2.0)
    rows = []
    tbls = d.find_elements(By.ID, 'grid_sortingData')
    if not tbls:
        return rows
    for tr in tbls[0].find_elements(By.TAG_NAME, 'tr'):
        tds = [(td.text or '').strip() for td in tr.find_elements(By.TAG_NAME, 'td')]
        if len(tds) < 10 or not re.search(r'\d{4}-\d{2}-\d{2}', tds[1] if len(tds) > 1 else ''):
            continue
        try:
            dt = tds[1][:10]
            d_date = date(*[int(x) for x in dt.split('-')])
            amount = int(re.sub(r'[^\d-]', '', tds[2]) or 0)
            comment = tds[7] or tds[5] or ''
            related = tds[9] if len(tds) > 9 else ''
            rows.append((d_date, tds[0], _classify(comment), comment[:255], amount, related[:50]))
        except Exception:
            continue
    return rows

def collect_master(master_id):
    acc = CrawlerAccount.objects.get(platform='gmarket', login_id=master_id)
    d = create_driver(kill_existing=False)
    summary = {}
    try:
        if not _esm_login(d, master_id, acc.password_enc):
            print(f'[{master_id}] 로그인 실패', flush=True); return summary
        d.get(GMKT_PAGE); time.sleep(4)
        sel = WebDriverWait(d, 10).until(EC.presence_of_element_located((By.ID, 'sellerId')))
        subs = [o.get_attribute('value') for o in sel.find_elements(By.TAG_NAME, 'option') if o.get_attribute('value')]
        print(f'[{master_id}] 서브 id: {subs}', flush=True)
        upto = timezone.localdate().month if timezone.localdate().year == YEAR else 12
        for sub in subs:
            Select(d.find_element(By.ID, 'sellerId')).select_by_value(sub); time.sleep(0.5)
            all_rows = []
            for sdt, edt in _months(YEAR, upto):
                mrows = _scrape_month(d, sub, sdt, edt)
                all_rows.extend(mrows)
            # 저장: 해당 (sub, gmarket, YEAR) 전 구간 삭제 후 재삽입(멱등)
            GmarketCostHistory.objects.filter(seller_id=sub, market='gmarket',
                                              use_date__year=YEAR).delete()
            objs, seq_by = [], {}
            for d_date, utype, ttype, comment, amount, related in all_rows:
                k = (d_date,); seq = seq_by.get(k, 0); seq_by[k] = seq + 1
                objs.append(GmarketCostHistory(seller_id=sub, market='gmarket', use_date=d_date,
                            seq=seq, use_type=utype[:20], transaction_type=ttype,
                            comment=comment, amount=amount, related_no=related))
            if objs:
                GmarketCostHistory.objects.bulk_create(objs, batch_size=500)
            ad = sum(1 for r in all_rows if r[2] in ('CPC', 'AI매출업', '서버비용'))
            adamt = abs(sum(r[4] for r in all_rows if r[2] in ('CPC', 'AI매출업', '서버비용')))
            summary[sub] = (len(all_rows), ad, adamt)
            print(f'  [{sub}] 거래 {len(all_rows)} / 광고 {ad} / 광고비 {adamt:,}원', flush=True)
    finally:
        try: d.quit()
        except Exception: pass
    return summary

if __name__ == '__main__' or True:
    masters = sys.argv[1:] or ['rejoice234', 'dlwodb000', 'rejoice222']
    print(f'=== 지마켓 복수아이디 판매예치금 수집 (마스터: {masters}) ===', flush=True)
    total = {}
    for m in masters:
        total.update(collect_master(m))
    try: stop_display()
    except Exception: pass
    print('=== 완료 ===', flush=True)
    for sid, (t, ad, amt) in total.items():
        print(f'  {sid:12} 거래{t:>3} 광고{ad:>3} 광고비 {amt:,}원', flush=True)

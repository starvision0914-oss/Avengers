"""지마켓+옥션 판매예치금 광고비 전체 수집기 (2024-01~현재, 엑셀 + 판매예치금 발생액).
- 검증된 정확법: 엑셀 다운로드(전체행) + '판매예치금 발생액' 컬럼 + 거래내역 분류 + JS클릭(오버레이 우회)
- 복수아이디 sellerId 드롭다운 순회, 지마켓+옥션 둘 다, traded_at(거래시각) 저장
- 멱등: (seller_id, market, use_date>=START) 삭제 후 삽입 → 재실행 중복0
- 계정별/서브별 저장(증분) → 중간 죽어도 완료분 보존
실행: python -u -c "import crawlers.gmkt_balance_full" [로그인계정...]
진행로그: /tmp/gmkt_full.log
"""
import os, re, time, glob, calendar
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from datetime import date, datetime
import pytz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException
from crawlers.browser import create_driver, stop_display
from apps.cpc.models import CrawlerAccount, GmarketCostHistory
from crawlers.gmarket_cost_crawler import _esm_login
import sys

KST = pytz.timezone('Asia/Seoul')
DL = '/tmp/gmkt_full_xl'
AD = ('CPC', 'AI매출업', '서버비용')
START_YEAR, START_MONTH = 2024, 1
LOG = open('/tmp/gmkt_full.log', 'a')


def p(*a):
    m = ' '.join(str(x) for x in a)
    LOG.write(m + '\n'); LOG.flush()
    try:
        print(m, flush=True)
    except Exception:
        pass


def drain(d):
    try:
        a = d.switch_to.alert; t = a.text; a.accept(); return t
    except Exception:
        return None


def wait_overlay(d):
    for _ in range(12):
        ov = d.find_elements(By.CSS_SELECTOR, '.layer_overlay')
        if not ov or all(not o.is_displayed() for o in ov):
            return
        time.sleep(0.5)


def jc(d, xp):
    els = d.find_elements(By.XPATH, xp)
    if els:
        d.execute_script('arguments[0].click();', els[0]); return True
    return False


def cls(cm):
    if 'AI매출업' in cm: return 'AI매출업'
    if '서버' in cm: return '서버비용'
    if 'CPC' in cm or 'cpc' in cm: return 'CPC'
    return '기타'


def months_range():
    today = date.today()
    out = []
    y, m = START_YEAR, START_MONTH
    while (y, m) <= (today.year, today.month):
        out.append((date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])))
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


def dl_month(d, sid, sdt, edt):
    for f in glob.glob(DL + '/*'):
        os.remove(f)
    try:
        Select(d.find_element(By.ID, 'sellerId')).select_by_value(sid)
    except Exception:
        pass
    time.sleep(0.3)
    for fid, val in [('searchSDT', sdt.isoformat()), ('searchEDT', edt.isoformat())]:
        d.execute_script("var e=document.getElementById('%s');if(e){e.value='%s';e.dispatchEvent(new Event('change'));}" % (fid, val))
    wait_overlay(d)
    jc(d, '//*[@id="btnSearch"]/img') or jc(d, '//*[@id="btnSearch"]')
    drain(d); time.sleep(1.5)
    wait_overlay(d)
    # 빈 달 빠른 스킵: 그리드에 거래행 없으면 엑셀 다운로드(6초 대기) 건너뜀
    has = False
    for tr in d.find_elements(By.CSS_SELECTOR, '#grid_sortingData tr'):
        if re.search(r'20\d\d-\d\d-\d\d', tr.text or ''):
            has = True; break
    if not has:
        return []
    jc(d, '//*[@id="excelDown"]')
    drain(d)
    # 다운로드 완료까지 폴링(최대 8초) — 고정 6초 대기보다 빠름
    for _ in range(16):
        files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
        if files:
            break
        time.sleep(0.5)
    files = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
    if not files:
        return []
    import xlrd
    try:
        sh = xlrd.open_workbook(files[-1]).sheet_by_index(0)
    except Exception:
        return []
    hdr = [str(x) for x in sh.row_values(0)]
    ci = {h: i for i, h in enumerate(hdr)}
    if '판매예치금 발생액' not in ci:
        return []
    rows = []
    for r in range(1, sh.nrows):
        row = sh.row_values(r)
        cm = str(row[ci.get('거래내역', 5)])
        amt = int(re.sub(r'[^\d-]', '', str(row[ci['판매예치금 발생액']])) or 0)
        dts = str(row[ci.get('거래일시', 1)]).strip()
        try:
            ta = KST.localize(datetime.strptime(dts[:19], '%Y-%m-%d %H:%M:%S')); dd = ta.date()
        except Exception:
            continue
        rows.append((dd, ta, cls(cm), cm[:255], amt, str(row[ci.get('관련번호', 6)])[:50]))
    return rows


def save(sid, market, rows):
    GmarketCostHistory.objects.filter(seller_id=sid, market=market,
                                      use_date__gte=date(START_YEAR, START_MONTH, 1)).delete()
    objs, seq = [], {}
    for dd, ta, tt, cm, amt, rel in rows:
        s = seq.get(dd, 0); seq[dd] = s + 1
        objs.append(GmarketCostHistory(seller_id=sid, market=market, use_date=dd, traded_at=ta,
                    seq=s, use_type='차감' if amt < 0 else '적립', transaction_type=tt,
                    comment=cm, amount=amt, related_no=rel))
    if objs:
        GmarketCostHistory.objects.bulk_create(objs, batch_size=1000)
    ad = [r for r in rows if r[2] in AD]
    return abs(sum(r[4] for r in ad)), len(ad)


def collect(login_id, months):
    acc = CrawlerAccount.objects.get(platform='gmarket', login_id=login_id)
    # 11번가 크롤러와 동시 실행 안전: 전용 user-data-dir(/tmp/org.chromium.*가 아니므로 11번가 임시정리에 안 지워짐)
    prof = '/tmp/gmkt_chrome_%d' % os.getpid()
    d = create_driver(download_dir=DL, kill_existing=False, user_data_dir=prof)
    try:
        d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
        if not _esm_login(d, login_id, acc.password_enc):
            p('  [%s] 로그인 실패' % login_id); return False
        for label, url in [('gmarket', 'https://www.esmplus.com/Member/Settle/GmktSellBalanceManagement'),
                           ('auction', 'https://www.esmplus.com/Member/Settle/IacSellBalanceManagement')]:
            d.get(url); time.sleep(4); wait_overlay(d)
            try:
                sel = WebDriverWait(d, 8).until(EC.presence_of_element_located((By.ID, 'sellerId')))
                subs = [o.get_attribute('value') for o in sel.find_elements(By.TAG_NAME, 'option') if o.get_attribute('value')]
            except Exception:
                subs = [login_id]
            for sid in subs:
                allr = []
                for sdt, edt in months:
                    allr += dl_month(d, sid, sdt, edt)
                amt, adn = save(sid, label, allr)
                p('  [%s|%s] 광고 %d건 / %s원' % (sid, label, adn, format(amt, ',')))
        return True
    finally:
        try: d.quit()
        except Exception: pass
        try:
            import shutil; shutil.rmtree(prof, ignore_errors=True)
        except Exception: pass


os.makedirs(DL, exist_ok=True)
logins = sys.argv[1:] or [a.login_id for a in CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
                          if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]
months = months_range()
p('=== 전체 광고비 수집 시작: %d계정 / %d개월(%s~%s) ===' % (
    len(logins), len(months), months[0][0], months[-1][1]))
ok = fail = 0
for i, lid in enumerate(logins, 1):
    p('[%d/%d] %s' % (i, len(logins), lid))
    try:
        if collect(lid, months):
            ok += 1
        else:
            fail += 1
    except Exception as e:
        fail += 1; p('  ! 오류: %s' % str(e)[:120])
    time.sleep(3)
try:
    stop_display()
except Exception:
    pass
p('=== 완료: 성공 %d / 실패 %d ===' % (ok, fail))
LOG.close()

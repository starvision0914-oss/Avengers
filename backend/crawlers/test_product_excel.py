"""11번가 상품현황 엑셀다운로드(팝업) 방식 테스트 — jinag7460
흐름: 로그인 → excel-download 팝업 → 파일생성요청 → 60초 대기 → 새로고침 → 다운로드 → 압축해제 → 파싱 → DB저장
"""
import os, sys, time, re, glob, zipfile, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount, ElevenMyProduct
from django.utils import timezone

LOGIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'jinag7460'
DL = Path('/tmp/avengers_11st_product_downloads') / LOGIN_ID
DL.mkdir(parents=True, exist_ok=True)
for f in DL.glob('*'):
    try: f.unlink()
    except Exception: pass

BTN_GEN = '//*[@id="popup-body-search"]/div[2]/button'
LNK_DL = '//*[@id="popup-body-grid"]/div/div/div/div[1]/div[2]/div[3]/div[2]/div/div/div/div[6]/a'


def log(m): print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def _accept_alert(driver, wait_s, tag=''):
    """alert 가 뜰 때까지 최대 wait_s 초 기다렸다 수락."""
    for _ in range(int(wait_s * 2)):
        try:
            a = driver.switch_to.alert
            log(f'alert[{tag}]: {a.text}')
            a.accept()
            time.sleep(0.5)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def discover_seller_no(driver):
    try:
        driver.get('https://soffice.11st.co.kr/')
        time.sleep(3)
    except Exception:
        pass
    for js in ["return window.sellerNo", "return window.SELLER_NO",
               "return (window.gnbInfo&&window.gnbInfo.sellerNo)"]:
        try:
            v = driver.execute_script(js)
            if v and str(v).isdigit():
                return str(v)
        except Exception:
            pass
    try:
        m = re.search(r'sellerNo["\']?\s*[:=]\s*["\']?(\d{6,})', driver.page_source)
        if m:
            return m.group(1)
    except Exception:
        pass
    try:
        for c in driver.get_cookies():
            if 'seller' in c['name'].lower() and str(c['value']).isdigit():
                return c['value']
    except Exception:
        pass
    return None


def main():
    acct = CrawlerAccount.objects.get(login_id=LOGIN_ID, platform='11st')
    driver = create_driver(download_dir=str(DL))
    try:
        log(f'로그인: {LOGIN_ID}')
        used = _ec._try_cookie_login(driver, acct)
        if not used:
            if not _ec._do_login(driver, acct.login_id, acct.password_enc):
                log('로그인 실패'); return
            _ec._save_cookies(driver, acct)
            log('일반 로그인 성공')
        else:
            log('쿠키 재사용')

        seller_no = discover_seller_no(driver)
        log(f'탐지된 sellerNo: {seller_no}')
        if not seller_no:
            seller_no = '75884047'
            log(f'탐지실패 → 예시값 사용: {seller_no}')

        url = f'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={seller_no}'
        log(f'엑셀다운로드 페이지: {url}')
        driver.get(url)
        time.sleep(5)

        try:
            driver.execute_cdp_cmd('Page.setDownloadBehavior',
                                   {'behavior': 'allow', 'downloadPath': str(DL)})
        except Exception:
            pass

        log('파일생성요청 클릭...')
        btn = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, BTN_GEN)))
        driver.execute_script("arguments[0].click();", btn)
        _accept_alert(driver, 15, '생성요청')

        log('60초 대기 (파일 생성)...')
        time.sleep(60)

        log('새로고침...')
        _accept_alert(driver, 3, '새로고침전')
        driver.refresh()
        time.sleep(6)
        _accept_alert(driver, 3, '새로고침후')

        log('다운로드 링크 클릭...')
        lnk = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, LNK_DL)))
        driver.execute_script("arguments[0].click();", lnk)
        _accept_alert(driver, 5, '다운로드')

        log('다운로드 대기...')
        got = None
        for _ in range(60):
            files = [f for f in DL.glob('*') if not f.name.endswith('.crdownload')]
            if files:
                got = max(files, key=lambda f: f.stat().st_mtime); break
            time.sleep(1)
        if not got:
            log('다운로드 실패 (파일 없음)'); return
        log(f'다운로드 완료: {got.name} ({got.stat().st_size} bytes)')

        # 압축 해제 (알집/zip)
        target = got
        if zipfile.is_zipfile(got):
            with zipfile.ZipFile(got) as z:
                names = z.namelist()
                log(f'압축 내용: {names}')
                z.extractall(DL)
            inner = [Path(DL) / n for n in names if n.lower().endswith(('.xls', '.xlsx', '.csv'))]
            if inner:
                target = inner[0]
                log(f'압축 내부 파일: {target.name}')
        else:
            log('zip 아님 — 그대로 파싱')

        # 헤더 미리보기
        rows = _read_rows(target)
        log(f'총 {len(rows)} 행')
        for i, r in enumerate(rows[:5]):
            log(f'  행{i}: {[str(c)[:18] for c in r[:12]]}')

        products = _ec_parse(rows)
        log(f'파싱된 상품: {len(products)}건')
        if products:
            log(f'  샘플: {products[0]}')
        n = _upsert(acct, products)
        log(f'DB 저장(나의상품) 완료: {n}건')
    finally:
        try: driver.quit()
        except Exception: pass
        stop_display()


def _read_rows(fp):
    fp = str(fp)
    try:
        if fp.lower().endswith('.csv'):
            import csv
            for enc in ('utf-8-sig', 'cp949', 'euc-kr'):
                try:
                    with open(fp, encoding=enc) as f:
                        return list(csv.reader(f))
                except Exception:
                    continue
            return []
        if fp.lower().endswith('.xls'):
            import xlrd
            wk = xlrd.open_workbook(fp); ws = wk.sheet_by_index(0)
            return [ws.row_values(i) for i in range(ws.nrows)]
        import openpyxl
        wb = openpyxl.load_workbook(fp, data_only=True)
        return list(wb.active.iter_rows(values_only=True))
    except Exception as e:
        log(f'파일 읽기 실패: {e}'); return []


def _ec_parse(rows):
    from crawlers.utils import parse_int
    hidx = None
    for i, row in enumerate(rows[:30]):
        s = ' '.join(str(c or '') for c in row)
        if '상품번호' in s and '상품명' in s:
            hidx = i; break
    if hidx is None:
        log('헤더(상품번호/상품명) 못찾음'); return []
    headers = [str(c or '').strip() for c in rows[hidx]]
    log(f'헤더: {headers}')
    col = {}
    for i, h in enumerate(headers):
        if '상품번호' in h and 'product_no' not in col: col['product_no'] = i
        elif '상품명' in h and 'product_name' not in col: col['product_name'] = i
        elif ('판매가' in h or '판매단가' in h) and 'sale_price' not in col: col['sale_price'] = i
        elif '재고' in h and 'stock' not in col: col['stock'] = i
        elif ('판매상태' in h or '상태' in h) and 'status' not in col: col['status'] = i
        elif ('판매자상품코드' in h or '셀러상품코드' in h) and 'seller_code' not in col: col['seller_code'] = i
        elif '카테고리' in h and 'category' not in col: col['category'] = i
    out = []
    for row in rows[hidx + 1:]:
        if not row: continue
        pno = parse_int(row[col['product_no']]) if 'product_no' in col else 0
        if not pno: continue
        out.append({
            'product_no': pno,
            'product_name': str(row[col.get('product_name', 1)] or '')[:500],
            'sale_price': parse_int(row[col['sale_price']]) if 'sale_price' in col else 0,
            'stock_quantity': parse_int(row[col['stock']]) if 'stock' in col else 0,
            'status_type': str(row[col['status']] or '')[:20] if 'status' in col else '',
            'seller_product_code': str(row[col['seller_code']] or '')[:100] if 'seller_code' in col else '',
            'category_id': str(row[col['category']] or '')[:50] if 'category' in col else '',
        })
    return out


def _upsert(acct, products):
    now = timezone.now()
    objs = [ElevenMyProduct(
        account=acct, product_no=p['product_no'], product_name=(p.get('product_name') or '')[:500],
        sale_price=p.get('sale_price') or 0, stock_quantity=p.get('stock_quantity') or 0,
        status_type=(p.get('status_type') or '')[:20], seller_product_code=(p.get('seller_product_code') or '')[:100],
        category_id=(p.get('category_id') or '')[:50], synced_at=now) for p in products]
    ElevenMyProduct.objects.bulk_create(
        objs, update_conflicts=True,
        update_fields=['product_name', 'sale_price', 'stock_quantity', 'status_type',
                       'seller_product_code', 'category_id', 'synced_at'], batch_size=500)
    return len(objs)


if __name__ == '__main__':
    main()

"""프로브 — AI 리마케팅 페이지(ad.esmplus.com/Remarketing/Management)의 상품별 실적 그리드 구조 조사. 실행 후 삭제."""
import time


def run():
    from crawlers.browser import create_driver, stop_display
    from crawlers.gmarket_crawler import _try_cookie_login, _full_login, AI_URL
    from apps.cpc.models import CrawlerAccount
    from selenium.webdriver.common.by import By

    acc = CrawlerAccount.objects.get(login_id='rejoice234')  # AI 매출 있는 계정
    drv = create_driver()
    try:
        if not _try_cookie_login(drv, acc):
            if not _full_login(drv, acc.login_id, acc.password_enc):
                print('[probe] 로그인 실패'); return
        print('[probe] 로그인 OK')
        drv.get(AI_URL)
        time.sleep(6)
        print('url=', drv.current_url[:90])
        src = drv.page_source
        for kw in ('상품명', '상품번호', '노출', '클릭', '광고비', '소진', '전환', '매출', 'ROAS', '광고수익률', '판매', '리마케팅'):
            if kw in src:
                print('  키워드:', kw)
        # id 후보
        print('--- id 후보(List/grid/Ad/item/tb) ---')
        for el in drv.find_elements(By.XPATH, "//*[@id]"):
            i = el.get_attribute('id') or ''
            if any(k in i for k in ('List', 'Grid', 'grid', 'Ad', 'item', 'Item', 'tb', 'Remark', 'campaign', 'Campaign')):
                print('  #' + i, el.tag_name)
        # 모든 table 헤더+첫행
        tables = drv.find_elements(By.TAG_NAME, 'table')
        print(f'--- table {len(tables)}개 ---')
        for idx, t in enumerate(tables):
            tid = t.get_attribute('id') or ''
            hdr = [(h.text or '').strip() for h in t.find_elements(By.TAG_NAME, 'th') if (h.text or '').strip()]
            fr = []
            for tr in t.find_elements(By.TAG_NAME, 'tr'):
                tds = tr.find_elements(By.TAG_NAME, 'td')
                if len(tds) >= 3:
                    fr = [(d.text or '').strip()[:14] for d in tds[:16]]
                    break
            if hdr or fr:
                print(f'  [{idx}] id={tid} 헤더={hdr[:16]}')
                if fr:
                    print(f'       첫행={fr}')
        # iframe 조사
        frames = drv.find_elements(By.TAG_NAME, 'iframe')
        print(f'--- iframe {len(frames)}개 ---')
        for i in range(len(frames)):
            try:
                drv.switch_to.default_content()
                drv.switch_to.frame(drv.find_elements(By.TAG_NAME, 'iframe')[i])
                ts = drv.find_elements(By.TAG_NAME, 'table')
                print(f'  iframe[{i}] table {len(ts)}개')
                for t in ts[:4]:
                    hdr = [(h.text or '').strip() for h in t.find_elements(By.TAG_NAME, 'th') if (h.text or '').strip()]
                    if hdr:
                        print('     헤더:', hdr[:16])
            except Exception as e:
                print(f'  iframe[{i}] 실패: {str(e)[:50]}')
        drv.switch_to.default_content()
    finally:
        try:
            drv.quit()
        except Exception:
            pass
        try:
            stop_display(None)
        except Exception:
            pass


run()

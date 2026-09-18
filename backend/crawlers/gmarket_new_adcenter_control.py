"""지마켓 신규 광고센터(adcenter.esmplus.com) 캠페인 ON/OFF 제어.
2026-09-04 신규 오픈 — 기존 ad.esmplus.com(간편광고/AI)과는 완전히 별도의 로그인 시스템.
로그인 탭은 'ESM PLUS'가 기본 선택인데 우리 계정은 '지마켓' 탭으로만 로그인됨(실측 확인).
캠페인 목록의 ON/OFF는 확인창 없이 토글 클릭 한 번으로 즉시 반영(실측)."""
import os
import glob
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException
from .browser import create_driver, stop_display

logger = logging.getLogger('crawler')

LOGIN_URL = 'https://adcenter.esmplus.com/login'
MGMT_URL = 'https://adcenter.esmplus.com/ad/management'


def _dismiss_alert(driver):
    try:
        driver.switch_to.alert.accept()
        return True
    except Exception:
        return False


def _login(driver, login_id, password, _attempt=0):
    """adcenter.esmplus.com 로그인 — '지마켓' 탭 선택 후 아이디/비번 입력.
    '지마켓' 탭 클릭이 폼을 리렌더링해서, 여러 계정을 연속으로 빠르게 돌릴 때
    간헐적으로 stale element reference가 남(2026-09-17 실측: 24계정 연속 실행 중
    23개가 이 에러로 로그인 실패, 1회 재시도로도 일부는 또 실패) — 최대 3회 시도."""
    try:
        driver.delete_all_cookies()
    except Exception:
        pass
    driver.get(LOGIN_URL)
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, 'login-username')))
    except TimeoutException:
        return False
    try:
        driver.find_element(By.CSS_SELECTOR, '.button__tab--gmarket').click()
        time.sleep(1.5)
        user = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'login-username')))
        user.clear()
        user.send_keys(login_id)
        pw = driver.find_element(By.ID, 'login-password')
        pw.clear()
        pw.send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        time.sleep(3)
    except Exception as e:
        logger.error(f'[신규광고센터:{login_id}] 로그인 폼 처리 오류: {e}')
        if _attempt < 2:
            time.sleep(3)
            return _login(driver, login_id, password, _attempt=_attempt + 1)
        return False
    return 'login' not in driver.current_url


REPORT_URL = 'https://adcenter.esmplus.com/report'


def _click_calendar_day(driver, day):
    """기간선택 캘린더에서 '비활성(is-disabled)이 아닌' 날짜버튼 중 텍스트가 day와 일치하는
    것을 클릭. 이전/다음달 잔여일이 같은 숫자로 disabled 처리돼 있어 이 필터가 필수."""
    return driver.execute_script("""
        const day = arguments[0];
        const btns = Array.from(document.querySelectorAll("td:not(.is-disabled) button.button__date"));
        const btn = btns.find(b => b.textContent.trim() === String(day));
        if (btn) { btn.click(); return true; }
        return false;
    """, day)


def fetch_daily_report(driver, login_id, password, since_date, until_date, log_fn=None):
    """신규 광고센터(adcenter.esmplus.com/report) '일별×날짜별' 상세리포트에서 계정 전체
    일자별 광고비를 가져온다(캠페인 타입 구분 없는 계정 총액, 2026-09-11 실측 확인 —
    GmarketNewAdCost 시간별 스냅샷 합계와 정확히 일치했음). 최대 3개월 전까지 조회 가능해
    시간별 스냅샷(2026-09-09부터만 존재)보다 과거를 더 볼 수 있다는 장점이 있음.
    ⚠️ since_date/until_date는 반드시 캘린더에 현재 표시된 달(=오늘이 속한 달) 안이어야 함
    (월 이동 클릭은 미구현 — since_date.day==1이 아니면서 이번달1일이 아닌 경우는 호출 안 할 것).
    반환: {date_str: cost, ...} — 조회기간 중 캠페인 집행이 아예 없던 날짜는 키 자체가 없음."""
    def log(m):
        logger.info(f'[신규광고센터리포트:{login_id}] {m}')
        if log_fn:
            log_fn(f'[신규광고센터리포트:{login_id}] {m}')

    if not _login(driver, login_id, password):
        log('로그인 실패')
        return {}

    driver.get(REPORT_URL)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button.button__calendar')))
    except TimeoutException:
        log('리포트 페이지 로딩 실패')
        return {}
    time.sleep(1)

    try:
        driver.execute_script("document.querySelector('button.button__calendar').click();")
        time.sleep(1)
        if not _click_calendar_day(driver, since_date.day):
            log(f'시작일({since_date}) 클릭 실패'); return {}
        time.sleep(0.4)
        if not _click_calendar_day(driver, until_date.day):
            log(f'종료일({until_date}) 클릭 실패'); return {}
        time.sleep(0.4)
        driver.find_element(By.XPATH,
            "//div[contains(@class,'box__button-wrap')]//button[text()='적용']").click()
        time.sleep(1.5)

        applied = driver.find_element(By.ID, 'date__start').get_attribute('value')
        expected = f'{since_date:%Y.%m.%d} ~ {until_date:%Y.%m.%d}'
        if applied != expected:
            log(f'기간 설정 확인 실패(적용={applied}, 기대={expected})')
            return {}

        driver.execute_script("document.getElementById('viewMode-daily').click();")
        time.sleep(0.3)
        driver.execute_script("document.querySelectorAll('.button__wrap button')[1].click();")  # 검색
        time.sleep(3)

        rows = driver.execute_script("""
            const table = document.querySelector('.box__table table');
            if (!table) return [];
            return Array.from(table.querySelectorAll('tbody tr')).map(
                tr => Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim()));
        """) or []
    except Exception as e:
        log(f'조회 중 오류: {e}')
        return {}

    result = {}
    for r in rows:
        if len(r) < 7:
            continue
        d = r[1]
        cost = int((r[6] or '0').replace(',', '') or 0)
        if cost:
            result[d] = cost
    log(f'{since_date}~{until_date} 일별 {len(result)}일 조회(합계 {sum(result.values()):,}원)')
    return result


NEWAD_DL = '/tmp/avengers_newadcenter_dl'


def _clear_newad_dl():
    os.makedirs(NEWAD_DL, exist_ok=True)
    for f in glob.glob(NEWAD_DL + '/*'):
        try: os.remove(f)
        except Exception: pass


def _wait_newad_dl(timeout=30):
    """.xlsx만 기다린다 — 리포트 생성이 아직 안 끝난 상태에서 다운로드 버튼을 누르면
    서버가 처리중 HTML을 내려줘 브라우저가 파일명 없이 'downloads.html'로 저장하는
    경우가 있었다(2026-09-17 실측, 빈 파일이거나 0바이트). 그건 무시하고 진짜 엑셀만 채택."""
    for _ in range(timeout * 2):
        fs = [f for f in glob.glob(NEWAD_DL + '/*')
              if f.lower().endswith('.xlsx') and not f.endswith('.crdownload')]
        if fs:
            time.sleep(1)
            return sorted(fs, key=os.path.getmtime)[-1]
        time.sleep(0.5)
    return None


def fetch_daily_report_xlsx(driver, login_id, password, since_date, until_date, log_fn=None):
    """신규 광고센터(adcenter.esmplus.com/report) '일별×날짜별' 상세리포트를 엑셀 다운로드로
    가져온다(2026-09-17 사용자 요청 — fetch_daily_report()의 화면표 읽기 대신 '엑셀 다운로드'
    버튼 사용, 노출수/클릭수/클릭률/평균클릭비용/광고비/전환금액/광고수익률 등 17개 컬럼 전체
    확보). 리포트는 '셀러별' 기준(엑셀 메타 '셀러ID' 행으로 실측 확인)이라 지마켓 아이디 단위
    집계가 저절로 보장됨 — 서브아이디가 별도 로그인 계정으로 존재하면 그 계정으로 한 번 더
    이 함수를 호출해서 따로 집계하면 됨(공유 세션/전환 개념 없음, 구광고센터 서브계정과 다름).
    ⚠️ '오늘'은 조회 캘린더에서 선택 불가(실측) — until_date는 어제 이하여야 함.
    ⚠️ since_date/until_date는 캘린더에 현재 표시된 달(오늘이 속한 달) 안이어야 함(월 이동 미구현).
    반환: [header_row, *data_rows](날짜 오름차순 정렬) 또는 실패 시 None. 집행 0건이어도
    엑셀 자체는 받아지므로 헤더만 있는 리스트가 올 수 있음."""
    def log(m):
        logger.info(f'[신규광고센터엑셀:{login_id}] {m}')
        if log_fn:
            log_fn(f'[신규광고센터엑셀:{login_id}] {m}')

    if not _login(driver, login_id, password):
        log('로그인 실패')
        return None

    driver.get(REPORT_URL)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button.button__calendar')))
    except TimeoutException:
        log('리포트 페이지 로딩 실패')
        return None
    time.sleep(1)

    try:
        driver.execute_script("document.querySelector('button.button__calendar').click();")
        time.sleep(1)
        if not _click_calendar_day(driver, since_date.day):
            log(f'시작일({since_date}) 클릭 실패'); return None
        time.sleep(0.4)
        if not _click_calendar_day(driver, until_date.day):
            log(f'종료일({until_date}) 클릭 실패'); return None
        time.sleep(0.4)
        driver.find_element(By.XPATH,
            "//div[contains(@class,'box__button-wrap')]//button[text()='적용']").click()
        time.sleep(1.5)

        applied = driver.find_element(By.ID, 'date__start').get_attribute('value')
        expected = f'{since_date:%Y.%m.%d} ~ {until_date:%Y.%m.%d}'
        if applied != expected:
            log(f'기간 설정 확인 실패(적용={applied}, 기대={expected})')
            return None

        driver.execute_script("document.getElementById('viewMode-daily').click();")
        time.sleep(0.3)
        driver.execute_script("document.querySelectorAll('.button__wrap button')[1].click();")  # 검색
        # 검색 결과 표가 실제로 그려질 때까지 대기(고정 3초만으로는 리포트 생성이 서버에서
        # 안 끝난 상태로 다운로드를 눌러 'downloads.html' 오다운로드가 발생했음, 2026-09-17 실측)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.box__table table tbody tr')))
        except TimeoutException:
            pass
        time.sleep(2)
    except Exception as e:
        log(f'조회 중 오류: {e}')
        return None

    f = None
    for attempt in range(3):
        _clear_newad_dl()
        try:
            btn = driver.find_element(By.XPATH,
                "//button[contains(@class,'button--excel') and text()='엑셀 다운로드']")
            btn.click()   # JS execute_script click은 실제 다운로드가 안 트리거됨(2026-09-17 실측)
        except Exception as e:
            log(f'다운로드 버튼 클릭 실패({attempt + 1}/3): {e}')
            time.sleep(2)
            continue
        f = _wait_newad_dl(20)
        if f:
            break
        log(f'엑셀 다운로드 재시도({attempt + 1}/3)')
        time.sleep(3)
    if not f or os.path.getsize(f) < 100:
        log('엑셀 다운로드 실패(3회 재시도 후)')
        return None

    try:
        import pandas as pd
        # 앞쪽 메타행(리포트종류/사이트/셀러ID/빈행)이 몇 줄인지 고정돼있지 않아, 첫 칸이
        # '날짜'인 행을 찾아 그 행을 헤더로 삼는다(2026-09-17 실측: 4행 고정 가정이 깨짐).
        raw = pd.read_excel(f, header=None)
        header_idx = None
        for i in range(min(len(raw), 20)):
            if str(raw.iloc[i, 0]).strip() == '날짜':
                header_idx = i
                break
        if header_idx is None:
            log('헤더행(날짜) 못 찾음')
            return None
        df = pd.read_excel(f, header=header_idx)
    except Exception as e:
        log(f'엑셀 파싱 실패: {e}')
        return None
    finally:
        try: os.remove(f)
        except Exception: pass

    if df.empty or len(df.columns) < 2:
        log('데이터 없음(0건)')
        return None

    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col]).sort_values(date_col)
    by_date = {r[date_col].date(): r for _, r in df.iterrows()}

    # CPC_KEY 스프레드시트 '종합' 워크시트가 이 워크시트의 D열(광고비)/J열(매출액)을
    # IMPORTRANGE로 그대로 참조한다(2026-09-17 확인) — 컬럼을 새로 늘리면서도 그 두 자리
    # 의미는 유지해야 종합시트 수식이 안 깨짐. '광고 비용'→D, '판매자 전환 금액'→J로
    # 오도록 나머지 15개 컬럼 순서를 재배치.
    orig_cols = list(df.columns[1:])
    # 헤더 '날짜'까지 A열이라 value_cols[0]=B열 ... value_cols[8]=J열.
    # '광고 비용'이 D열(index 2), '판매자 전환 금액'이 J열(index 8)에 오도록 배치.
    _priority = ['노출 수', '클릭 수', '광고 비용', '평균클릭비용', '클릭률', '광고수익률',
                 '판매자 전환 수', '광고 전환 수량', '판매자 전환 금액']
    value_cols = [c for c in _priority if c in orig_cols]
    value_cols += [c for c in orig_cols if c not in value_cols]

    pct_cols = {c for c in value_cols if ('률' in str(c) or '전환율' in str(c))}
    header = [str(date_col)] + [str(c) for c in value_cols]
    rows = [header]

    # '종합' 시트가 날짜별로 고정된 행번호(row=day+1)를 IMPORTRANGE로 참조하므로 월중
    # 어느 날 실행해도 행번호가 안 밀리게 그 달의 실제 말일까지 채우고, 합계는 말일 바로
    # 다음 행에 온다(2026-09-17 확정 — 9월은 30일까지+31행에 합계, 31일짜리 달은
    # 31일까지+32행에 합계 — 기존 일자별 시트 관례와 동일한 가변 위치).
    import calendar
    import datetime as _dt
    month_len = calendar.monthrange(since_date.year, since_date.month)[1]

    for day in range(1, month_len + 1):
        cur = since_date.replace(day=day)
        future = cur > until_date
        r = None if future else by_date.get(cur)
        row = [cur.strftime('%Y-%m-%d')]
        for c in value_cols:
            if future:
                row.append('')
            elif r is None:
                row.append('0%' if c in pct_cols else '0')
            else:
                v = r[c]
                row.append('' if pd.isna(v) else str(v))
        rows.append(row)

    # 기존 일자별 시트 관례(_build_daily_matrix)와 동일하게 맨 아래 합계행 추가
    # (2026-09-17 사용자 지적: 신규광고센터 형식엔 원래 없었음). %컬럼은 합산 의미가
    # 없어 빈칸으로 둔다.
    totals = ['합계']
    for idx, c in enumerate(value_cols):
        if c in pct_cols:
            totals.append('')
            continue
        s = 0
        for row in rows[1:]:
            try:
                s += float(row[idx + 1])
            except (ValueError, TypeError):
                pass
        totals.append(str(int(s)) if s == int(s) else str(s))
    rows.append(totals)

    log(f'{since_date}~{until_date} 일별 {len(rows) - 2}행(전체 날짜 채움, 원본 {len(df)}행) + 합계행')
    return rows


def collect_product_costs(driver, login_id, password, since_date, until_date, log_fn=None):
    """신규광고센터 '상품별×날짜별' 상세리포트를 엑셀로 받아 GmarketNewAdProductCost에 upsert
    (2026-09-18 사용자 요청 — 상품별 광고비를 못 받고 있던 문제 해결). 같은 상품이 여러
    캠페인/그룹에 동시 노출되면 날짜+상품 조합이 중복 행으로 나오므로(실측: 5,789행 중
    483건 중복) login_id+use_date+product_no로 합산해서 저장한다.
    반환: 저장된 (날짜,상품) 조합 수, 실패 시 None."""
    from apps.cpc.models import GmarketNewAdProductCost

    def log(m):
        logger.info(f'[신규광고센터상품별:{login_id}] {m}')
        if log_fn:
            log_fn(f'[신규광고센터상품별:{login_id}] {m}')

    if not _login(driver, login_id, password):
        log('로그인 실패')
        return None

    driver.get(REPORT_URL)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button.button__calendar')))
    except TimeoutException:
        log('리포트 페이지 로딩 실패')
        return None
    time.sleep(1)

    try:
        driver.execute_script("document.querySelector('button.button__calendar').click();")
        time.sleep(1)
        if not _click_calendar_day(driver, since_date.day):
            log(f'시작일({since_date}) 클릭 실패'); return None
        time.sleep(0.4)
        if not _click_calendar_day(driver, until_date.day):
            log(f'종료일({until_date}) 클릭 실패'); return None
        time.sleep(0.4)
        driver.find_element(By.XPATH,
            "//div[contains(@class,'box__button-wrap')]//button[text()='적용']").click()
        time.sleep(1.5)

        applied = driver.find_element(By.ID, 'date__start').get_attribute('value')
        expected = f'{since_date:%Y.%m.%d} ~ {until_date:%Y.%m.%d}'
        if applied != expected:
            log(f'기간 설정 확인 실패(적용={applied}, 기대={expected})')
            return None

        driver.execute_script("document.getElementById('reportType-product').click();")
        time.sleep(0.5)
        driver.execute_script("document.getElementById('viewMode-daily').click();")
        time.sleep(0.5)
        driver.execute_script("document.querySelectorAll('.button__wrap button')[1].click();")  # 검색
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.box__table table tbody tr')))
        except TimeoutException:
            pass
        time.sleep(2)
    except Exception as e:
        log(f'조회 중 오류: {e}')
        return None

    f = None
    for attempt in range(3):
        _clear_newad_dl()
        try:
            btn = driver.find_element(By.XPATH,
                "//button[contains(@class,'button--excel') and text()='엑셀 다운로드']")
            btn.click()
        except Exception as e:
            log(f'다운로드 버튼 클릭 실패({attempt + 1}/3): {e}')
            time.sleep(2)
            continue
        f = _wait_newad_dl(30)   # 상품별은 행이 훨씬 많아 계정별 리포트보다 여유있게 대기
        if f:
            break
        log(f'엑셀 다운로드 재시도({attempt + 1}/3)')
        time.sleep(3)
    if not f or os.path.getsize(f) < 100:
        log('엑셀 다운로드 실패(3회 재시도 후)')
        return None

    try:
        import pandas as pd
        raw = pd.read_excel(f, header=None)
        header_idx = None
        for i in range(min(len(raw), 20)):
            if str(raw.iloc[i, 0]).strip() == '날짜':
                header_idx = i
                break
        if header_idx is None:
            log('헤더행(날짜) 못 찾음')
            return None
        df = pd.read_excel(f, header=header_idx)
    except Exception as e:
        log(f'엑셀 파싱 실패: {e}')
        return None
    finally:
        try: os.remove(f)
        except Exception: pass

    if df.empty:
        log('데이터 없음(0건)')
        return 0

    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜', '상품번호'])

    agg = df.groupby(['날짜', '상품번호']).agg(
        상품명=('상품명', 'last'),
        노출수=('노출 수', 'sum'),
        클릭수=('클릭 수', 'sum'),
        광고비=('광고 비용', 'sum'),
        전환금액=('판매자 전환 금액', 'sum'),
        전환수=('판매자 전환 수', 'sum'),
    ).reset_index()

    saved = 0
    for _, r in agg.iterrows():
        cost = int(r['광고비'])
        clicks = int(r['클릭수'])
        conv_amount = int(r['전환금액'])
        roas = round(conv_amount / cost * 100, 2) if cost else 0
        GmarketNewAdProductCost.objects.update_or_create(
            login_id=login_id, use_date=r['날짜'].date(), product_no=str(r['상품번호']),
            defaults={
                'product_name': str(r['상품명'])[:500],
                'impressions': int(r['노출수']),
                'clicks': clicks,
                'avg_click_cost': round(cost / clicks) if clicks else 0,
                'cost': cost,
                'conv_amount': conv_amount,
                'conv_count': int(r['전환수']),
                'roas': roas,
            },
        )
        saved += 1

    log(f'{since_date}~{until_date} 상품 {agg["상품번호"].nunique()}개 / {saved}건 저장(원본 {len(df)}행, 중복합산)')
    return saved


def collect_product_keywords(driver, login_id, password, product_nos, since_date, until_date, log_fn=None):
    """신규광고센터 '키워드별' 리포트에서 지정 상품번호들의 키워드를 조회해 GmarketNewAdKeyword에
    upsert(2026-09-18 사용자 요청 — 효율 100%+ 상품 키워드 매칭용). 상품번호 필터는 콤마구분
    최대 5개까지만 되므로 5개씩 나눠서 조회. 보기방식은 '합계'(기간 전체 누적, 일자별 아님).
    ⚠️ '직접운영형'(자동타겟팅) 캠페인 상품은 수동 키워드가 없어 결과에 아예 안 잡힘 — 정상.
    반환: {product_no: 매칭된 키워드 수}, 로그인 실패 시 None."""
    from apps.cpc.models import GmarketNewAdKeyword

    def log(m):
        logger.info(f'[신규광고센터키워드:{login_id}] {m}')
        if log_fn:
            log_fn(f'[신규광고센터키워드:{login_id}] {m}')

    if not _login(driver, login_id, password):
        log('로그인 실패')
        return None

    counts = {p: 0 for p in product_nos}
    batches = [product_nos[i:i + 5] for i in range(0, len(product_nos), 5)]

    for bi, batch in enumerate(batches):
        driver.get(REPORT_URL)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button.button__calendar')))
        except TimeoutException:
            log(f'배치{bi+1}/{len(batches)} 리포트 페이지 로딩 실패')
            continue

        try:
            driver.execute_script("document.querySelector('button.button__calendar').click();")
            time.sleep(1)
            if not _click_calendar_day(driver, since_date.day):
                log(f'배치{bi+1} 시작일 클릭 실패'); continue
            time.sleep(0.4)
            if not _click_calendar_day(driver, until_date.day):
                log(f'배치{bi+1} 종료일 클릭 실패'); continue
            time.sleep(0.4)
            driver.find_element(By.XPATH,
                "//div[contains(@class,'box__button-wrap')]//button[text()='적용']").click()
            time.sleep(1.5)

            driver.find_element(By.ID, 'reportType-keyword').click()
            time.sleep(1)
            driver.find_element(By.ID, 'search-productNo').send_keys(','.join(batch))
            time.sleep(0.3)
            driver.execute_script("document.getElementById('viewMode-total').click();")
            time.sleep(0.3)
            driver.execute_script("document.querySelectorAll('.button__wrap button')[1].click();")  # 검색
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.box__table table')))
            except TimeoutException:
                pass
            time.sleep(2)
        except Exception as e:
            log(f'배치{bi+1} 조회 오류: {e}')
            continue

        rows = driver.execute_script("""
            const table = document.querySelector('.box__table table');
            if (!table) return [];
            return Array.from(table.querySelectorAll('tbody tr')).map(
                tr => Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim()));
        """) or []

        # 컬럼: [checkbox, 기간, 캠페인명, 그룹명, 상품명, 상품번호, 키워드, 노출수, 클릭수,
        #        클릭률, 평균클릭비용, 광고비, 판매자전환금액, 광고수익률, 판매자전환수, ...]
        for r in rows:
            if len(r) < 15 or not r[5].strip().isdigit():
                continue
            product_no = r[5].strip()
            if product_no not in counts:
                continue
            try:
                GmarketNewAdKeyword.objects.update_or_create(
                    login_id=login_id, product_no=product_no, keyword=r[6].strip(),
                    period_start=since_date, period_end=until_date,
                    defaults={
                        'product_name': r[4][:500],
                        'campaign_name': r[2][:255],
                        'group_name': r[3][:255],
                        'impressions': int(r[7].replace(',', '') or 0),
                        'clicks': int(r[8].replace(',', '') or 0),
                        'avg_click_cost': int(r[10].replace(',', '') or 0),
                        'cost': int(r[11].replace(',', '') or 0),
                        'conv_amount': int(r[12].replace(',', '') or 0),
                        'conv_count': int(r[14].replace(',', '') or 0),
                        'roas': float(r[13].replace('%', '').replace(',', '') or 0),
                    },
                )
                counts[product_no] += 1
            except Exception as e:
                log(f'행 저장 오류({product_no}): {e}')
        time.sleep(1)

    matched = sum(1 for v in counts.values() if v > 0)
    total_kw = sum(counts.values())
    log(f'상품 {len(product_nos)}개 중 {matched}개 키워드 매칭됨(총 {total_kw}개 키워드), '
        f'나머지 {len(product_nos) - matched}개는 자동타겟팅이라 키워드 없음')
    return counts


def _get_campaign_rows(driver, wait=10, _retried=False):
    """관리 페이지의 캠페인별 (토글엘리먼트, 이름, 현재상태) 목록. 매 호출마다 페이지 새로 진입해야 함
    (토글 클릭 후 다시 읽으려면 이 함수를 재호출).
    2026-09-04 실측: 계정에 따라 캠페인 목록 위에 '구매자에게 관심 받고 있는 상품을...' 추천 위젯이
    추가로 붙어 로딩이 더 걸리는 경우가 있었고, 이때 토글이 아직 안 떴는데 타임아웃돼 '캠페인 0개'로
    잘못 판정한 사례가 실제로 있었다(dlrmsgh012, 실제론 캠페인 5개 존재) — 1회 더 길게 재시도한다."""
    driver.get(MGMT_URL)
    try:
        WebDriverWait(driver, wait).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input.form__toggle')))
    except TimeoutException:
        if not _retried:
            time.sleep(2)
            return _get_campaign_rows(driver, wait=wait * 2, _retried=True)
        return []
    time.sleep(1)
    toggles = driver.find_elements(By.CSS_SELECTOR, 'input.form__toggle')
    names = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr td a, table tbody tr td span.for-a11y')
    # 이름 추출은 부정확할 수 있어(중첩 테이블) 참고용으로만 사용 — 개수만 정확하면 충분
    rows = []
    for i, tgl in enumerate(toggles):
        on = tgl.is_selected()
        rows.append({'idx': i, 'toggle': tgl, 'on': on})
    return rows


def _get_campaign_cost_rows(driver, wait=10, _retried=False):
    """관리 페이지 '오늘' 탭(기본값) 캠페인별 광고비용 목록.
    2026-09-09 실측: 표 컬럼 순서 = 체크박스,ON/OFF,캠페인명,상태,캠페인유형,노출수,클릭수,클릭률,
    평균클릭비용,전환수,전환율,전환금액,광고비용,광고수익율 — 0-index 11=전환금액(매출액),
    12=광고비용, 13=광고수익율(%). 캠페인명에 '통합운영'이 들어가면 AI광고(사용자 확인,
    2026-09-09), 나머지는 GM_CPC. 매출액/수익율은 2026-09-10 구글시트(상품별 CPC/AI 시트
    재구성) 요구로 추가 수집."""
    driver.get(MGMT_URL)
    try:
        WebDriverWait(driver, wait).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input.form__toggle')))
    except TimeoutException:
        if not _retried:
            time.sleep(2)
            return _get_campaign_cost_rows(driver, wait=wait * 2, _retried=True)
        return []
    time.sleep(1)
    rows = []
    for tr in driver.find_elements(By.CSS_SELECTOR, 'table tbody tr'):
        tds = tr.find_elements(By.TAG_NAME, 'td')
        if len(tds) < 13:
            continue
        try:
            name = tds[2].text.strip()
            campaign_type = tds[4].text.strip()
            cost_txt = tds[12].text.strip().replace(',', '')
            cost = int(cost_txt) if cost_txt.isdigit() else 0
            conv_txt = tds[11].text.strip().replace(',', '')
            conv_amount = int(conv_txt) if conv_txt.lstrip('-').isdigit() else 0
            roas_txt = tds[13].text.strip().replace(',', '').replace('%', '')
            try:
                roas = float(roas_txt)
            except ValueError:
                roas = 0.0
        except Exception:
            continue
        if not name:
            continue
        rows.append({'name': name, 'type': campaign_type, 'cost': cost,
                     'conv_amount': conv_amount, 'roas': roas, 'is_ai': '통합운영' in name})
    return rows


def collect_costs(driver, login_id, log_fn=None):
    """한 계정의 오늘자 캠페인별 광고비용을 수집해 upsert. 반환: [{'name','cost','is_ai'}, ...]"""
    from django.utils import timezone
    from apps.cpc.models import GmarketNewAdCost

    def log(msg):
        logger.info(f'[신규광고센터비용:{login_id}] {msg}')
        if log_fn:
            log_fn(f'[신규광고센터비용:{login_id}] {msg}')

    rows = _get_campaign_cost_rows(driver)
    if not rows:
        log('캠페인 없음/조회 실패')
        return []

    today = timezone.localdate()
    for r in rows:
        GmarketNewAdCost.objects.update_or_create(
            login_id=login_id, use_date=today, campaign_name=r['name'],
            defaults={'campaign_type': r['type'], 'is_ai': r['is_ai'], 'cost': r['cost'],
                      'conv_amount': r.get('conv_amount', 0), 'roas': r.get('roas', 0)},
        )
    ai_total = sum(r['cost'] for r in rows if r['is_ai'])
    cpc_total = sum(r['cost'] for r in rows if not r['is_ai'])
    log(f'저장 완료 — AI {ai_total:,}원 / CPC {cpc_total:,}원 (캠페인 {len(rows)}개)')
    return rows


def run_collect_costs(source='manual', log_fn=None, account_filter=None):
    """전체(또는 지정) 계정의 신규광고센터 캠페인별 광고비용 수집."""
    from apps.cpc.models import CrawlerAccount, CrawlerLog, protected_login_ids
    from apps.cpc import eleven_block_guard as guard

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    protected = protected_login_ids('gmarket') - {'dlwodb777'}
    if protected:
        qs = qs.exclude(login_id__in=protected)
    if account_filter:
        acct_map = {a.login_id: a for a in qs.filter(login_id__in=account_filter)}
        qs = [acct_map[lid] for lid in account_filter if lid in acct_map]
    else:
        qs = [a for a in qs if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

    LOCK_PLATFORM = 'gmarket_newad'
    if not guard.try_acquire_adcontrol('지마켓신규광고센터비용수집', platform=LOCK_PLATFORM):
        if log_fn:
            log_fn('⏭️ 이미 광고제어 실행 중 — 중복 방지로 스킵')
        return []
    ok, reason = guard.preflight('지마켓신규광고센터비용수집', platform=LOCK_PLATFORM, wait=True, wait_timeout=10800)
    if not ok:
        guard.clear_adcontrol_busy(LOCK_PLATFORM)
        if log_fn:
            log_fn(f'⏭️ 건너뜀 — {reason}')
        return []

    guard.clear_control_stop(LOCK_PLATFORM)
    results, driver = [], None
    try:
        driver = create_driver()
        try:
            driver.set_page_load_timeout(40)
        except Exception:
            pass
        for acct in qs:
            if guard.is_control_stop(LOCK_PLATFORM):
                if log_fn: log_fn('🛑 강제중지 요청 — 중단')
                break
            try:
                logged = False
                for _try in range(2):
                    if guard.is_control_stop(LOCK_PLATFORM):
                        break
                    try:
                        driver.delete_all_cookies()
                        if _login(driver, acct.login_id, acct.password_enc):
                            logged = True
                            break
                    except UnexpectedAlertPresentException:
                        _dismiss_alert(driver)
                    except Exception:
                        pass
                    time.sleep(2)
                if not logged:
                    if log_fn: log_fn(f'[신규광고센터비용:{acct.login_id}] 로그인 실패(2회) — 건너뜀')
                    CrawlerLog.objects.create(platform='gmarket', level='error',
                        message='신규광고센터 비용수집 로그인 실패(2회)', account_id=acct.login_id)
                    continue
                rows = collect_costs(driver, acct.login_id, log_fn)
                results.append({'login_id': acct.login_id, 'campaigns': len(rows)})
            except Exception as e:
                logger.exception(f'[신규광고센터비용:{acct.login_id}] 수집 오류')
                if log_fn: log_fn(f'[신규광고센터비용:{acct.login_id}] 오류: {e}')
                CrawlerLog.objects.create(platform='gmarket', level='error',
                    message=f'신규광고센터 비용수집 오류: {e}', account_id=acct.login_id)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        stop_display()
        guard.clear_adcontrol_busy(LOCK_PLATFORM)
        guard.release_global_lock(platform=LOCK_PLATFORM)

    return results


def control_one(driver, login_id, action, source='manual', log_fn=None):
    """계정 하나의 전체 캠페인을 action(on/off)으로 일괄 전환. 반환: {'before':N,'after':N,'changed':N}
    2026-09-09 사용자 지시로 개별토글 클릭 방식 대신 화면의 '전체 캠페인' 체크(#check-all) →
    '노출상태 일괄변경' → ON/OFF 라디오 선택 → '변경하기'로 한 번에 처리(실측 확인한 셀렉터)."""
    def log(msg):
        logger.info(f'[신규광고센터:{login_id}] {msg}')
        if log_fn:
            log_fn(f'[신규광고센터:{login_id}] {msg}')

    rows = _get_campaign_rows(driver)
    if not rows:
        log('캠페인 없음/조회 실패')
        return {'before': 0, 'after': 0, 'changed': 0, 'total': 0}

    want_on = (action == 'on')
    before_on = sum(1 for r in rows if r['on'])
    total = len(rows)

    try:
        driver.find_element(By.ID, 'check-all').click()
        time.sleep(0.5)
        driver.find_element(By.XPATH, "//button[contains(text(),'노출상태 일괄변경')]").click()
        time.sleep(1)
        radio_id = 'status_on' if want_on else 'status_off'
        driver.find_element(By.ID, radio_id).click()
        time.sleep(0.3)
        driver.find_element(
            By.XPATH, "//div[contains(@class,'box__layer-wrap')]//button[contains(text(),'변경하기')]"
        ).click()
        time.sleep(1.5)
        # 2026-09-04 실측: 계정 전체가 '운영중지' 상태에서 처음 ON하면 확인모달이 뜬다 —
        # "운영중인 AI매출업 광고가 있습니다. 캠페인 재개 시 기존 AI매출업 광고는 종료됩니다.
        # 계속하시겠습니까?" 이 모달을 안 닫으면 화면이 막힌다(사용자 확인 후 신규로 전환).
        # '노출상태 일괄변경' 모달과 같은 클래스(box__layer-wrap)를 공유하므로 텍스트로 구분한다.
        try:
            for m in driver.find_elements(By.CSS_SELECTOR, 'div.box__layer-wrap'):
                if m.is_displayed() and ('AI매출업' in m.text or '종료' in m.text):
                    m.find_element(By.CSS_SELECTOR, 'button.button--blue').click()
                    log('AI매출업 종료 확인모달 → 확인 클릭')
                    time.sleep(1)
                    break
        except Exception:
            pass
    except Exception as e:
        log(f'일괄변경 실패: {e}')

    time.sleep(1)
    final_rows = _get_campaign_rows(driver)
    after_on = sum(1 for r in final_rows if r['on'])
    changed = sum(1 for r, f in zip(rows, final_rows) if r['on'] != f['on']) if len(rows) == len(final_rows) else total
    log(f'{action.upper()} 완료(일괄) — 전{before_on}→후{after_on} (전체 {total}개)')
    return {'before': before_on, 'after': after_on, 'changed': changed, 'total': total}


def run_control(action, source='manual', log_fn=None, account_filter=None):
    from apps.cpc.models import CrawlerAccount, NewAdCenterHistory, CrawlerLog, protected_login_ids
    from apps.cpc import eleven_block_guard as guard

    qs = CrawlerAccount.objects.filter(platform='gmarket', is_active=True).exclude(crawling_status='차단됨')
    # dlwodb777: 상품삭제/판매중지 자동화는 계속 금지(project_gmarket_dlwod777_manual_only)지만,
    # 2026-09-07 사용자가 신규광고센터 on/off만 명시적으로 재요청 — 이 기능에 한해서만 보호 예외.
    protected = protected_login_ids('gmarket') - {'dlwodb777'}
    if protected:
        qs = qs.exclude(login_id__in=protected)
    if account_filter:
        acct_map = {a.login_id: a for a in qs.filter(login_id__in=account_filter)}
        qs = [acct_map[lid] for lid in account_filter if lid in acct_map]
    else:
        qs = [a for a in qs if not (a.gmarket_origin_id and a.gmarket_origin_id != a.login_id)]

    LOCK_PLATFORM = 'gmarket_newad'  # adcenter.esmplus.com 전용 락 — ad.esmplus.com(간편광고/AI) 크롤과 분리(2026-09-07)

    if not guard.try_acquire_adcontrol('지마켓신규광고센터제어', platform=LOCK_PLATFORM):
        if log_fn:
            log_fn('⏭️ 이미 광고제어 실행 중 — 중복 방지로 스킵')
        return []

    ok, reason = guard.preflight('지마켓신규광고센터제어', platform=LOCK_PLATFORM, wait=True, wait_timeout=10800)
    if not ok:
        guard.clear_adcontrol_busy(LOCK_PLATFORM)
        if log_fn:
            log_fn(f'⏭️ 건너뜀 — {reason}')
        return []

    guard.clear_control_stop(LOCK_PLATFORM)
    results, driver = [], None
    try:
        driver = create_driver()
        try:
            driver.set_page_load_timeout(40)
        except Exception:
            pass
        for acct in qs:
            if guard.is_control_stop('gmarket'):
                if log_fn: log_fn('🛑 강제중지 요청 — 중단')
                break
            try:
                logged = False
                for _try in range(2):
                    if guard.is_control_stop('gmarket'):
                        break
                    try:
                        driver.delete_all_cookies()
                        if _login(driver, acct.login_id, acct.password_enc):
                            logged = True
                            break
                    except UnexpectedAlertPresentException:
                        _dismiss_alert(driver)
                    except Exception:
                        pass
                    time.sleep(2)
                if not logged:
                    if log_fn: log_fn(f'[신규광고센터:{acct.login_id}] 로그인 실패(2회) — 건너뜀')
                    CrawlerLog.objects.create(platform='gmarket', level='error',
                        message='신규광고센터 로그인 실패(2회)', account_id=acct.login_id)
                    continue

                result = control_one(driver, acct.login_id, action, source, log_fn)
                NewAdCenterHistory.objects.create(
                    gmarket_id=acct.login_id, action=action,
                    campaign_before=result['before'], campaign_after=result['after'],
                    source=source,
                )
                results.append({'login_id': acct.login_id, **result})
            except Exception as e:
                logger.exception(f'[신규광고센터:{acct.login_id}] 제어 오류')
                if log_fn: log_fn(f'[신규광고센터:{acct.login_id}] 오류: {e}')
                CrawlerLog.objects.create(platform='gmarket', level='error',
                    message=f'신규광고센터 제어 오류: {e}', account_id=acct.login_id)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        stop_display()
        # LOCK_PLATFORM('gmarket_newad')으로 잡은 락을 'gmarket'으로 잘못 반납해 신규광고센터
        # 전역락이 영구히 안 풀리던 버그(2026-09-09 발견 — 06:55 실행분 락이 계속 남아있었음).
        guard.clear_adcontrol_busy(LOCK_PLATFORM)
        guard.release_global_lock(platform=LOCK_PLATFORM)

    return results

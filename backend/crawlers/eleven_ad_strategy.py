"""11번가 광고센터(adoffice) — 광고그룹 '노출 스케줄' 전략 일괄 적용.

흐름(원본 GUI 도구 로직을 Avengers 인프라에 이식):
  계정 로그인(OTP/쿠키 재사용) → 광고관리 → (선택한 캠페인 이름들) → '전체-' 광고그룹 전부
  → 각 그룹 /modify → 상세설정(스케줄) → 24h×7요일 표에서 [지정 요일·시간만 ON, 나머지 OFF] → 저장

전략(스케줄)은 파라미터로 받음:
  on_start, on_end : ON 시작/종료 '시'(포함). 예 8,16 → 08~16시 ON
  on_weekdays      : ON 요일 집합(1=월 … 7=일). 예 {1,2,3,4,5} → 평일만

안전장치:
- 기본 DRY-RUN(바꿀 칸 수만 계산·로그, 클릭/저장 없음). execute=True 일 때만 실제 적용.
- guard.preflight 전역락(동시크롤 금지) + 기존 11번가 로그인(_do_login) 재사용.
- 진행상황을 St11AdStrategyLog(run_id)로 기록 → 프론트가 폴링해 실시간 표시.

CLI:
  드라이런: python3 crawlers/eleven_ad_strategy.py --eid tmxkql27 --campaigns 자동_캠페인
  실제적용: ... --execute --on-start 8 --on-end 16 --weekdays 1,2,3,4,5
"""
import os, sys, time, argparse, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()
from apps.cpc.models import CrawlerAccount, St11AdStrategyLog
from apps.cpc import eleven_block_guard as guard
from crawlers.eleven_crawler import _do_login, _drain_alerts
from crawlers.browser import create_driver, stop_display
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ADOFFICE = 'https://adoffice.11st.co.kr/'
WEEKDAY_NAMES = {1: '월', 2: '화', 3: '수', 4: '목', 5: '금', 6: '토', 7: '일'}


def _log(run_id, status, msg, eid='', campaign='', group=''):
    print(time.strftime('%H:%M:%S '), f'[{status}] {eid} {campaign} {group} {msg}', flush=True)
    try:
        St11AdStrategyLog.objects.create(
            run_id=run_id, eleven_id=eid, campaign_name=campaign,
            group_name=group, status=status, detail=str(msg)[:500])
    except Exception:
        pass


def close_all_popups(driver):
    for _ in range(3):
        try:
            if not driver.find_elements(By.CSS_SELECTOR, '.MuiDialog-container'):
                break
            for btn in driver.find_elements(
                By.XPATH,
                "//button[contains(.,'닫기') or contains(.,'확인') or contains(.,'OK') or contains(.,'Close')]"):
                try:
                    driver.execute_script('arguments[0].click();', btn); time.sleep(0.4)
                except Exception:
                    pass
        except Exception:
            pass


def click_focus_menu(driver):
    focus_xpath = '//*[@id="root"]/div/div[1]/div/nav/div[2]/div[2]/div[1]/div[1]/span'
    for _ in range(3):
        try:
            close_all_popups(driver)
            el = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, focus_xpath)))
            driver.execute_script('arguments[0].click();', el)
            time.sleep(1); return True
        except Exception:
            time.sleep(1)
    return False


def open_ad_management(driver):
    ad_xpath = '//*[@id="root"]/div/div[1]/div/nav/div[2]/div[2]/div[2]/div/div/div/div[1]/div[1]/div[1]/span'
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, ad_xpath)))
        driver.find_element(By.XPATH, ad_xpath).click(); time.sleep(2); return True
    except Exception:
        # 텍스트 기반 폴백(메뉴 구조 변동 대비)
        els = [e for e in driver.find_elements(By.XPATH, "//*[normalize-space(text())='광고관리']") if e.is_displayed()]
        if els:
            driver.execute_script('arguments[0].click();', els[0]); time.sleep(2); return True
    return False


# 페이지 크기(목록 노출 개수) 드롭다운 — 사용자 확인 XPath
PAGESIZE_XPATHS = [
    '//*[@id="root"]/div/div[2]/div[2]/div[2]/div[2]/div/div',   # 사용자 제공(캠페인/그룹 목록)
]


def _click_100_option(driver):
    """드롭다운이 열린 상태에서 '100개'/'100' 옵션을 클릭(포털 렌더 포함). 성공시 True."""
    # 정확 매칭 우선 → 부분매칭(1000 등 오매칭 방지 위해 exact 먼저)
    selectors = [
        "//li[@data-value='100']",
        "//*[@role='option'][@data-value='100']",
        "//li[contains(.,'100개') and not(contains(.,'1000'))]",
        "//*[@role='option'][contains(.,'100개') and not(contains(.,'1000'))]",
        "//li[contains(normalize-space(),'100') and not(contains(normalize-space(),'1000'))]",
        "//option[contains(.,'100')]",
    ]
    for sel in selectors:
        for o in driver.find_elements(By.XPATH, sel):
            try:
                if not o.is_displayed():
                    continue
                label = (o.text or '100').strip() or '100'   # 클릭 전에 텍스트 확보(클릭후 stale 방지)
                try:
                    o.click()
                except Exception:
                    driver.execute_script('arguments[0].click();', o)
                time.sleep(2)
                return label
            except Exception:
                continue
    return None


def set_page_size_100(driver, run_id=None, eid=''):
    """목록을 100개까지 보이도록 페이지 크기를 100으로 설정.
    실제 정체=MUI Select(div.MuiSelect-select, 현재값 '30개', 옵션 텍스트에 \\u200b 포함).
    0) MUI Select 클릭→포털 li '100' 선택  1) 사용자 XPath  2) TablePagination  3) native."""
    # 0) MUI Select (.MuiSelect-select) — 페이지크기 셀렉트(텍스트에 '개' 또는 숫자)
    try:
        sels = [e for e in driver.find_elements(By.CSS_SELECTOR, '.MuiSelect-select') if e.is_displayed()]
        for s in sels:
            txt = (s.text or '').replace('​', '').strip()
            if not ('개' in txt or txt.replace('개', '').isdigit()):
                continue                      # 페이지크기 셀렉트로 보이는 것만
            if '100' in txt:
                if run_id: _log(run_id, 'INFO', '페이지 크기 이미 100', eid)
                return True
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", s)
            # MUI Select는 mousedown 으로 열림(JS click 무효) — 실제클릭→mousedown 순으로 시도
            for opener in ('real', 'mousedown'):
                try:
                    if opener == 'real':
                        s.click()
                    else:
                        driver.execute_script(
                            "arguments[0].dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window}));", s)
                    time.sleep(1.2)
                    if _click_100_option(driver):
                        if run_id: _log(run_id, 'INFO', f'페이지 크기 100 설정(MUI Select/{opener})', eid)
                        return True
                except Exception:
                    pass
    except Exception as e:
        if run_id: _log(run_id, 'INFO', f'MUI Select 처리 예외: {e}', eid)
    # 1) 사용자 지정 드롭다운
    for xp in PAGESIZE_XPATHS:
        try:
            trg = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, xp)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", trg)
            try:
                trg.click()
            except Exception:
                driver.execute_script('arguments[0].click();', trg)
            time.sleep(1.2)
            picked = _click_100_option(driver)
            if picked:
                if run_id: _log(run_id, 'INFO', f'페이지 크기 100 설정 완료("{picked}")', eid)
                return True
        except Exception as e:
            if run_id: _log(run_id, 'INFO', f'지정 드롭다운 처리 실패: {e}', eid)
    # 2) MUI TablePagination 버튼형
    try:
        btns = driver.find_elements(By.XPATH, "//*[contains(@class,'MuiTablePagination')]//div[@role='button' or @role='combobox']")
        if btns:
            driver.execute_script('arguments[0].click();', btns[0]); time.sleep(1)
            if _click_100_option(driver):
                if run_id: _log(run_id, 'INFO', '페이지 크기 100(TablePagination)', eid)
                return True
    except Exception:
        pass
    # 3) 네이티브 select
    try:
        for s in driver.find_elements(By.CSS_SELECTOR, 'select'):
            opts = [o.get_attribute('value') for o in s.find_elements(By.TAG_NAME, 'option')]
            if any((o or '').strip() == '100' for o in opts):
                driver.execute_script(
                    "arguments[0].value='100';"
                    "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", s)
                time.sleep(2)
                if run_id: _log(run_id, 'INFO', '페이지 크기 100(native select)', eid)
                return True
    except Exception:
        pass
    if run_id: _log(run_id, 'INFO', f'⚠️ 페이지 크기 100 실패. 후보={_dump_pagesize(driver)}', eid)
    return False


def find_campaign_links(driver):
    """캠페인 목록의 행 링크 [(name, element)] (최대 100개 가정, 페이지크기 100 적용 후)."""
    links = driver.find_elements(By.XPATH, "//*[@id='root']//table/tbody/tr/td[2]/div/div/a")
    if not links:
        links = driver.find_elements(By.XPATH, "//table/tbody/tr//a")
    return [(a.text.strip(), a) for a in links if a.text.strip()]


def get_group_links(driver):
    """'전체-XX' 로 시작하는 광고그룹 링크 수집."""
    try:
        els = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(text(),'전체-')]")))
    except Exception:
        els = driver.find_elements(By.XPATH, "//a[contains(text(),'전체-')]")
    return [(a.text.strip(), a.get_attribute('href')) for a in els if a.text.strip().startswith('전체-')]


def _dump_radios(driver):
    """화면의 라디오/관련 라벨을 진단용으로 덤프(셀렉터 보정용)."""
    try:
        return driver.execute_script(r"""
          var out=[];
          document.querySelectorAll("input[type=radio]").forEach(function(r){
            var lab='';
            if(r.id){var l=document.querySelector("label[for='"+r.id+"']"); if(l)lab=l.textContent.trim();}
            if(!lab){var p=r.closest('label'); if(p)lab=p.textContent.trim();}
            out.push({id:r.id||'', name:r.name||'', value:r.value||'', label:lab.slice(0,30)});
          });
          // '설정/시간/스케줄/상세' 텍스트 가진 클릭가능 요소도
          var texts=[];
          document.querySelectorAll("label,span,button,div").forEach(function(e){
            var t=(e.textContent||'').trim();
            if(t && t.length<20 && /(상세|스케줄|시간대|노출 ?시간|요일)/.test(t)) texts.push(t);
          });
          return {radios:out.slice(0,15), texts:Array.from(new Set(texts)).slice(0,12)};
        """)
    except Exception:
        return None


def _pick_schedule_radio(driver, run_id, eid, camp, grp_name, timeout=12):
    """'상세 설정(노출 스케줄)' 라디오/옵션을 여러 방법으로 찾아 클릭. 성공시 True.
    화면 렌더가 늦으면 못찾고 그룹이 통째 누락되므로 timeout초 동안 폴링 재시도."""
    candidates = [
        (By.CSS_SELECTOR, '#radio-schedule-setting'),
        (By.CSS_SELECTOR, "input[type=radio][id*='schedule']"),
        (By.CSS_SELECTOR, "input[type=radio][name*='schedule']"),
        (By.CSS_SELECTOR, "input[type=radio][value*='schedule']"),
        (By.XPATH, "//label[contains(.,'상세')]//input[@type='radio']"),
        (By.XPATH, "//label[contains(.,'상세')]"),
        (By.XPATH, "//*[contains(text(),'상세 설정') or contains(text(),'상세설정')]"),
        (By.XPATH, "//*[contains(text(),'시간대') or contains(text(),'노출 시간') or contains(text(),'요일')]"),
    ]
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        for by, sel in candidates:
            try:
                els = [e for e in driver.find_elements(by, sel) if e.is_displayed()]
                if els:
                    try:
                        els[0].click()
                    except Exception:
                        driver.execute_script('arguments[0].click();', els[0])
                    time.sleep(1)
                    _log(run_id, 'INFO', f'상세설정 클릭: {sel} (시도 {attempt})', eid, camp, grp_name)
                    return True
            except Exception:
                continue
        time.sleep(0.8)   # 렌더 대기 후 재탐색
    # timeout 내 실패 — 진단 덤프
    dump = _dump_radios(driver)
    _log(run_id, 'ERROR', f'상세설정 라디오 못찾음({timeout}s, {attempt}회). 화면 라디오/텍스트={dump}', eid, camp, grp_name)
    return False


def _dump_schedule(driver):
    """스케줄 영역 구조 진단 — 표/그리드/요일셀 클래스."""
    try:
        return driver.execute_script(r"""
          var info={tables:[],grids:[],week:[],onoff:0};
          document.querySelectorAll('table').forEach(function(t){
            var h=t.querySelector('tr'); info.tables.push({cls:(t.className||'').toString().slice(0,50),rows:t.querySelectorAll('tr').length,head:h?h.textContent.trim().slice(0,40):''});
          });
          document.querySelectorAll("[role='grid'],[role='table'],[class*='chedule'],[class*='ime'],[class*='eek']").forEach(function(g){
            info.grids.push({tag:g.tagName,cls:(g.className||'').toString().slice(0,60)});
          });
          document.querySelectorAll('th,td,div,span,button').forEach(function(e){
            var t=(e.textContent||'').trim();
            if(/^(월|화|수|목|금|토|일)$/.test(t)) info.week.push((e.tagName)+'.'+(e.className||'').toString().slice(0,25));
          });
          info.week=Array.from(new Set(info.week)).slice(0,8);
          info.onoff=document.querySelectorAll("[class*='on'],[class*='off']").length;
          return info;
        """)
    except Exception:
        return None


def _dump_pagesize(driver):
    """페이지크기(10/20/50/100개) 드롭다운 후보 진단."""
    try:
        return driver.execute_script(r"""
          var out=[];
          document.querySelectorAll("select,[role='combobox'],[role='button'],[class*='Select'],[class*='agination'],[class*='ropdown']").forEach(function(e){
            var t=(e.textContent||'').trim();
            if(/(개|^10$|^20$|^50$|^100$|10개|100)/.test(t) && t.length<25) out.push({tag:e.tagName,cls:(e.className||'').toString().slice(0,45),txt:t.slice(0,20)});
          });
          return out.slice(0,12);
        """)
    except Exception:
        return None


def apply_strategy(driver, run_id, eid, camp, grp_name, grp_url, on_start, on_end, weekdays, execute):
    """그룹 /modify → 상세설정 → 스케줄 표 [요일·시간 ON, 나머지 OFF] → (execute면) 저장."""
    modify_url = grp_url.rstrip('/') + '/modify'
    driver.get(modify_url)
    try:
        WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == 'complete')
    except Exception:
        pass
    time.sleep(2)
    close_all_popups(driver)

    # 상세 설정(스케줄) 라디오 — 다중 폴백 + 실패시 진단덤프
    if not _pick_schedule_radio(driver, run_id, eid, camp, grp_name):
        return
    time.sleep(2)   # 상세설정 클릭 후 스케줄 그리드 렌더 대기

    # 스케줄 표(여러 후보)
    table = None
    for sel in ["//table[contains(@class,'MuiTable')]", "//table",
                "//*[@role='grid']", "//*[contains(@class,'chedule')]"]:
        try:
            table = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, sel)))
            if table:
                _log(run_id, 'INFO', f'스케줄 영역 후보: {sel}', eid, camp, grp_name); break
        except Exception:
            continue
    if table is None:
        _log(run_id, 'ERROR', f'스케줄 표 못찾음. 진단={_dump_schedule(driver)}', eid, camp, grp_name); return
    try:
        rows = table.find_element(By.TAG_NAME, 'tbody').find_elements(By.TAG_NAME, 'tr')
    except Exception:
        rows = table.find_elements(By.TAG_NAME, 'tr')
    if not rows:
        _log(run_id, 'ERROR', f'스케줄 행 없음. 진단={_dump_schedule(driver)}', eid, camp, grp_name); return

    # 칸 클래스/구조 진단(ON/OFF 판정 검증용)
    try:
        cellinfo = driver.execute_script(r"""
          var t=arguments[0]; var rows=t.querySelectorAll('tbody tr'); var samp=[]; var cls={};
          for(var i=0;i<rows.length && i<3;i++){
            var tds=rows[i].querySelectorAll('td');
            for(var j=0;j<tds.length && j<4;j++){
              var c=tds[j].className||''; cls[c]=(cls[c]||0)+1;
              samp.push({r:i,c:j,cls:c.toString().slice(0,40),
                aria:(tds[j].getAttribute('aria-pressed')||tds[j].getAttribute('aria-checked')||tds[j].getAttribute('data-state')||''),
                txt:(tds[j].textContent||'').trim().slice(0,6),
                bg:(window.getComputedStyle(tds[j]).backgroundColor||'')});
            }
          }
          return {sample:samp.slice(0,12)};
        """, table)
        _log(run_id, 'INFO', f'칸구조: {cellinfo}', eid, camp, grp_name)
    except Exception as e:
        _log(run_id, 'INFO', f'칸구조 덤프 실패: {e}', eid, camp, grp_name)

    # ON 칸 = class 'on'(정확 일치, 배경 파랑). OFF = 그 외. td 클릭은 마우스이벤트로 토글.
    TOGGLE_JS = ("var el=arguments[0];['mousedown','mouseup','click'].forEach(function(t){"
                 "el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));});")

    def scan_and_toggle(do_click):
        cnt = 0
        for tr in rows[:-1]:
            try:
                hour = int(tr.find_element(By.TAG_NAME, 'td').text.replace('시', '').strip())
            except Exception:
                continue
            cells = tr.find_elements(By.TAG_NAME, 'td')[1:]
            for idx, td in enumerate(cells, start=1):     # idx 1=월 … 7=일
                want_on = (idx in weekdays) and (on_start <= hour <= on_end)
                is_on = (td.get_attribute('class') or '').strip() == 'on'
                if want_on != is_on:                       # 원하는 상태와 다르면 토글 대상
                    cnt += 1
                    if do_click:
                        try:
                            driver.execute_script(TOGGLE_JS, td)
                        except Exception:
                            pass
        return cnt

    changes = scan_and_toggle(do_click=execute)

    if not execute:
        _log(run_id, 'SKIP', f'[드라이런] 바꿀 칸 {changes}개 (저장 안함)', eid, camp, grp_name); return

    # 토글 직후 재검증(클릭이 실제로 먹었는지)
    time.sleep(1)
    rows = (table.find_elements(By.TAG_NAME, 'tr')
            or table.find_element(By.TAG_NAME, 'tbody').find_elements(By.TAG_NAME, 'tr'))
    remain = scan_and_toggle(do_click=False)
    _log(run_id, 'INFO', f'토글 {changes}칸 시도 → 잔여 불일치 {remain}칸', eid, camp, grp_name)

    # 저장 — 다중 셀렉터(저장/저장하기/적용/수정완료/완료), 실패시 버튼 덤프
    save_selectors = [
        "//button[normalize-space()='그룹 수정' or normalize-space()='그룹수정']",
        "//button[contains(.,'그룹 수정')]",
        "//button[normalize-space()='저장']",
        "//button[normalize-space()='저장하기']",
        "//button[normalize-space()='수정완료' or normalize-space()='수정 완료']",
        "//button[normalize-space()='적용' or normalize-space()='완료' or normalize-space()='등록']",
        "//button[contains(.,'저장')]",
        "//a[normalize-space()='저장' or contains(.,'저장')]",
        "//*[@role='button'][contains(.,'저장')]",
        "//span[normalize-space()='저장']/ancestor::*[self::button or self::a or @role='button'][1]",
        "//input[@type='submit' or @type='button'][contains(@value,'저장')]",
        "//*[normalize-space()='저장' or normalize-space()='저장하기' or normalize-space()='수정완료'][self::button or self::a or self::span or self::div][not(.//*[normalize-space()='저장'])]",
    ]
    saved = False
    for sel in save_selectors:
        try:
            els = [e for e in driver.find_elements(By.XPATH, sel) if e.is_displayed() and e.is_enabled()]
            if not els:
                continue
            btn = els[-1]   # 보통 하단 푸터의 저장이 마지막
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            try:
                btn.click()
            except Exception:
                driver.execute_script('arguments[0].click();', btn)
            time.sleep(2)
            # 저장 확인 팝업/alert 처리
            try:
                driver.switch_to.alert.accept(); time.sleep(1)
            except Exception:
                pass
            close_all_popups(driver)
            _log(run_id, 'APPLIED', f'스케줄 적용·저장 완료 (변경 {changes}칸, "{sel}")', eid, camp, grp_name)
            saved = True
            break
        except Exception:
            continue
    if not saved:
        # 저장 비슷한 텍스트를 가진 모든 요소(태그·클래스 포함) 덤프
        dump = driver.execute_script(r"""
          var out=[];
          document.querySelectorAll("*").forEach(function(e){
            if(e.offsetParent===null) return;
            var t=(e.textContent||e.value||'').trim();
            if(t && t.length<12 && /(저장|적용|완료|등록|수정)/.test(t) && e.children.length<=1){
              out.push(e.tagName+'.'+(e.className||'').toString().slice(0,30)+'='+t);
            }
          });
          return Array.from(new Set(out)).slice(0,20);
        """)
        _log(run_id, 'ERROR', f'저장 버튼 못찾음. 저장류 요소={dump}', eid, camp, grp_name)


def run_account(driver, run_id, eid, campaigns, on_start, on_end, weekdays, execute, max_groups=0):
    wd_txt = ''.join(WEEKDAY_NAMES[w] for w in sorted(weekdays))
    _log(run_id, 'INFO', f'전략: {on_start}~{on_end}시 ON / 요일 {wd_txt} / 캠페인 {campaigns}', eid)
    driver.get(ADOFFICE); time.sleep(6)
    close_all_popups(driver)
    click_focus_menu(driver)
    if not open_ad_management(driver):
        _log(run_id, 'ERROR', '광고관리 진입 실패', eid); return
    set_page_size_100(driver, run_id, eid)

    all_links = find_campaign_links(driver)
    _log(run_id, 'INFO', f'캠페인 {len(all_links)}개 감지', eid)
    # 이름 매칭(부분일치) — 선택 캠페인만
    name_to_idx = {}
    for i, (nm, _) in enumerate(all_links):
        name_to_idx.setdefault(nm, i)

    for camp in campaigns:
        # 캠페인 재진입(목록 새로고침 후 이름으로 클릭)
        driver.get(ADOFFICE); time.sleep(3); close_all_popups(driver)
        click_focus_menu(driver); open_ad_management(driver); set_page_size_100(driver, run_id, eid)
        links = find_campaign_links(driver)
        target = None
        def _norm(s):
            return (s or '').replace(' ', '').replace('_', '').lower()
        nc = _norm(camp)
        # 1) 정확 일치(공백·언더바 무시) 우선 — '자동_캠페인'이 '자동_캠페인_260202'보다 우선
        for nm, el in links:
            if _norm(nm) == nc:
                target = (nm, el); break
        # 2) 부분 일치 폴백
        if not target:
            for nm, el in links:
                if nc in _norm(nm) or _norm(nm) in nc:
                    target = (nm, el); break
        if not target:
            avail = [nm for nm, _ in links]
            _log(run_id, 'SKIP', f"캠페인 '{camp}' 못찾음. 목록={avail}", eid, camp); continue
        _log(run_id, 'INFO', f"캠페인 매칭: '{target[0]}'", eid, camp)
        try:
            driver.execute_script('arguments[0].click();', target[1]); time.sleep(3)
        except Exception as e:
            _log(run_id, 'ERROR', f'캠페인 클릭 실패: {e}', eid, camp); continue

        # 캠페인 진입 후: 광고그룹 목록을 100개까지 노출
        set_page_size_100(driver, run_id, eid)
        groups = get_group_links(driver)
        if max_groups and max_groups > 0:
            groups = groups[:max_groups]
            _log(run_id, 'INFO', f"'{target[0]}' 그룹 {len(groups)}개(진단: 처음 {max_groups}개만)", eid, camp)
        else:
            _log(run_id, 'INFO', f"'{target[0]}' 그룹 {len(groups)}개", eid, camp)
        for gname, gurl in groups:
            if guard.is_stop_requested() if hasattr(guard, 'is_stop_requested') else False:
                _log(run_id, 'INFO', '중지 요청 — 종료', eid, camp); return
            apply_strategy(driver, run_id, eid, camp, gname, gurl,
                           on_start, on_end, weekdays, execute)


def list_campaigns(eid, run_id=None):
    """대표 계정 1개로 로그인 → 광고관리 → 캠페인 이름(최대100) 읽어 로그(status='CAMP')로 적재.
    동시 로그인 금지(IP차단 방지) — 단일 계정만. 결과는 St11AdofficeCampaign에도 최소 upsert."""
    import time as _t
    if not run_id:
        run_id = _t.strftime('%Y%m%d%H%M%S')
    _log(run_id, 'START', f'캠페인 목록 조회 — {eid}')
    ok, reason = guard.preflight('11번가캠페인조회', wait=True, wait_timeout=300, platform='11st')
    if not ok:
        _log(run_id, 'ERROR', f'전역락/접속 불가 — {reason}', eid)
        _log(run_id, 'DONE', '중단'); return run_id
    pw = {x.login_id: x.password_enc for x in CrawlerAccount.objects.filter(platform='11st')}
    driver = None
    try:
        driver = create_driver(kill_existing=False)
        sn = _do_login(driver, eid, pw.get(eid, ''))
        if not sn:
            _log(run_id, 'ERROR', '로그인 실패', eid); _log(run_id, 'DONE', '중단'); return run_id
        driver.implicitly_wait(0); driver.set_page_load_timeout(40)
        _drain_alerts(driver, login_id=eid)
        driver.get(ADOFFICE); time.sleep(6); close_all_popups(driver)
        click_focus_menu(driver)
        if not open_ad_management(driver):
            _log(run_id, 'ERROR', '광고관리 진입 실패', eid); _log(run_id, 'DONE', '중단'); return run_id
        set_page_size_100(driver, run_id, eid)
        links = find_campaign_links(driver)
        names = []
        for nm, _el in links:
            if nm and nm not in names:
                names.append(nm)
        names = names[:100]
        _log(run_id, 'INFO', f'캠페인 {len(names)}개', eid)
        from apps.cpc.models import St11AdofficeCampaign
        from django.utils import timezone as _tz
        for nm in names:
            _log(run_id, 'CAMP', nm, eid)
            if not St11AdofficeCampaign.objects.filter(eleven_id=eid, campaign_name=nm).exists():
                try:
                    St11AdofficeCampaign.objects.create(
                        eleven_id=eid, campaign_name=nm, collected_at=_tz.now())
                except Exception:
                    pass
    except Exception as e:
        _log(run_id, 'ERROR', f'조회 오류: {e}', eid)
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock()
        try: stop_display()
        except Exception: pass
    _log(run_id, 'DONE', '캠페인 조회 완료')
    return run_id


def order_accounts(accounts):
    """작업순서 강제: 1등급>2등급>3등급>4등급>광고이력 있는 계정>나머지.
    grade=ElevenSellerGrade 최신값, 광고이력=St11ProductDaily에 행 존재."""
    from apps.cpc.models import ElevenSellerGrade, St11ProductDaily
    # 계정별 최신 등급 (collected_at 최신 1건)
    grade_map = {}
    for r in ElevenSellerGrade.objects.order_by('eleven_id', '-collected_at').values('eleven_id', 'grade'):
        grade_map.setdefault(r['eleven_id'], r['grade'])
    adhist = set(St11ProductDaily.objects.values_list('eleven_id', flat=True).distinct())

    def rank(eid):
        g = grade_map.get(eid)
        if g in (1, 2, 3, 4):
            return (g, eid)            # 1~4등급: 등급 순
        if eid in adhist:
            return (5, eid)            # 광고이력 있는 계정
        return (6, eid)                # 나머지
    return sorted(accounts, key=rank)


def run_strategy(accounts, campaigns, on_start=8, on_end=16, weekdays=None,
                 execute=False, run_id=None, source='manual', max_groups=0):
    """여러 계정 × 선택 캠페인에 스케줄 전략 적용. accounts/campaigns=list."""
    if weekdays is None:
        weekdays = {1, 2, 3, 4, 5}
    weekdays = set(int(w) for w in weekdays)
    if not run_id:
        run_id = time.strftime('%Y%m%d%H%M%S')
    accounts = order_accounts(accounts)   # 1등급>2>3>4>광고이력>나머지 강제 정렬
    mode = '실제적용' if execute else '드라이런(찾기만)'
    _log(run_id, 'START', f'시작 — 계정 {len(accounts)}개 / 모드={mode}')
    _log(run_id, 'INFO', f'작업순서(등급우선): {", ".join(accounts)}')

    ok, reason = guard.preflight('11번가광고전략', wait=True, wait_timeout=300, platform='11st')
    if not ok:
        _log(run_id, 'ERROR', f'전역락/접속 불가 — {reason}')
        _log(run_id, 'DONE', '중단')
        return run_id

    pw = {x.login_id: x.password_enc for x in CrawlerAccount.objects.filter(platform='11st')}
    try:
        for eid in accounts:
            driver = None
            try:
                driver = create_driver(kill_existing=False)
                t = time.time(); sn = _do_login(driver, eid, pw.get(eid, ''))
                _log(run_id, 'INFO', f'로그인 {time.time()-t:.1f}s sn={sn}', eid)
                if not sn:
                    _log(run_id, 'ERROR', '로그인 실패', eid); continue
                driver.implicitly_wait(0); driver.set_page_load_timeout(40)
                _drain_alerts(driver, login_id=eid)
                run_account(driver, run_id, eid, campaigns, on_start, on_end, weekdays, execute, max_groups)
            except Exception as e:
                _log(run_id, 'ERROR', f'계정 처리 오류: {e}', eid)
            finally:
                if driver:
                    try: driver.quit()
                    except Exception: pass
    finally:
        guard.release_global_lock()
        try: stop_display()
        except Exception: pass
    _log(run_id, 'DONE', f'완료 ({mode})')
    return run_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eid', required=True, help='계정(콤마로 여러개)')
    ap.add_argument('--campaigns', required=True, help='캠페인 이름(콤마로 여러개)')
    ap.add_argument('--on-start', type=int, default=8)
    ap.add_argument('--on-end', type=int, default=16)
    ap.add_argument('--weekdays', default='1,2,3,4,5', help='ON 요일 1=월..7=일')
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--max-groups', type=int, default=0, help='진단용: 처음 N개 그룹만(0=전체)')
    a = ap.parse_args()
    accounts = [x.strip() for x in a.eid.split(',') if x.strip()]
    campaigns = [x.strip() for x in a.campaigns.split(',') if x.strip()]
    weekdays = {int(x) for x in a.weekdays.split(',') if x.strip()}
    run_strategy(accounts, campaigns, a.on_start, a.on_end, weekdays, a.execute, max_groups=a.max_groups)


if __name__ == '__main__':
    main()

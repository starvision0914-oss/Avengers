"""11번가 광고센터 — 지정 상품번호의 광고를 OFF (소재 단위).
구조: 광고관리 → 캠페인 → 광고그룹 → 상품목록(행별 ON/OFF). 상품명 셀 앞 10자리=상품번호.
대상 상품번호 집합을 받아 전 캠페인/그룹/페이지를 돌며 매칭 행을 체크 → '선택 OFF' 클릭.

안전장치:
- 기본 DRY-RUN(찾기만, 클릭 없음). --execute 줄 때만 실제 OFF.
- preflight 전역락(동시크롤 금지). OTP 포함 로그인 재사용.
- 매칭/처리 건수 로깅. 페이지·그룹 끝까지 순회.

실행:
  탐색(드라이런):  /usr/bin/python3 crawlers/eleven_ad_off.py --eid tmxkql27 --codes /path/codes.txt
  실제 OFF:        /usr/bin/python3 crawlers/eleven_ad_off.py --eid tmxkql27 --codes /path/codes.txt --execute
codes.txt = 상품번호 한 줄에 하나(또는 콤마). CSV(계정,상품번호…)면 --csv-col 로 컬럼 지정.
"""
import os, sys, time, re, argparse, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()
from apps.cpc.models import CrawlerAccount
from apps.cpc import eleven_block_guard as guard
from crawlers.eleven_crawler import _do_login, _drain_alerts
from crawlers.browser import create_driver, stop_display
from selenium.webdriver.common.by import By

ADOFFICE = 'https://adoffice.11st.co.kr/'

def log(m): print(time.strftime('%H:%M:%S '), m, flush=True)

# 상품 목록 행에서 (상품번호, ON/OFF버튼요소, 행체크박스, 현재상태) 추출하는 JS
SCAN_ROWS = r"""
var out=[];
var trs=document.querySelectorAll('table tbody tr');
for(var i=0;i<trs.length;i++){
  var tr=trs[i];
  var tds=tr.querySelectorAll('td');
  // 상품명 셀: '상품명' 컬럼 (이미지 다음). 앞 10자리 숫자가 상품번호.
  var nameCell='';
  for(var j=0;j<tds.length;j++){var t=(tds[j].textContent||'').trim(); if(/^\d{10}/.test(t)){nameCell=t;break;}}
  var m=nameCell.match(/^(\d{10})/);
  if(!m) continue;
  var cb=tr.querySelector("input[type=checkbox]");
  // 상태 텍스트(운영중/중지 등)
  var status='';
  for(var j=0;j<tds.length;j++){var t=(tds[j].textContent||'').trim(); if(t==='운영중'||t==='중지'||t.indexOf('OFF')>=0){status=t;break;}}
  out.push({idx:i, pno:m[1], status:status, hasCb: !!cb});
}
return out;
"""

def find_links(driver):
    """현재 테이블 첫 컬럼들의 행 링크(캠페인/그룹 진입용) 텍스트+클릭가능 여부"""
    return driver.execute_script(r"""
      var trs=document.querySelectorAll('table tbody tr'); var out=[];
      for(var i=0;i<trs.length;i++){var a=trs[i].querySelector('a'); if(a) out.push(i);}
      return out;""")

def click_row_link(driver, row_idx):
    return driver.execute_script("""
      var ri=arguments[0];
      var trs=document.querySelectorAll('table tbody tr');
      if(ri>=trs.length) return false;
      var a=trs[ri].querySelector('a'); if(!a) return false; a.click(); return true;
    """, row_idx)

def click_text_button(driver, label):
    els=[e for e in driver.find_elements(By.XPATH, f"//button[normalize-space(text())='{label}']") if e.is_displayed()]
    if els: driver.execute_script("arguments[0].click();", els[0]); return True
    return False

def get_page_buttons(driver):
    """페이지네이션 숫자 버튼 목록"""
    return driver.execute_script(r"""
      return Array.from(document.querySelectorAll('button')).filter(function(b){
        return b.offsetParent!==null && /^\d+$/.test((b.textContent||'').trim());
      }).map(function(b){return (b.textContent||'').trim();});""")

def process_product_list(driver, targets, execute, stats):
    """현재 '상품 목록' 화면에서 페이지를 돌며 매칭 상품을 OFF.
    stats['done'](전역 처리완료 상품번호)로 중복 카운트/클릭 방지.
    한 페이지 스캔에 '새 상품번호'가 없으면 페이지 끝으로 보고 종료."""
    seen=set()      # 이 그룹에서 본 상품번호
    page=1
    while page <= 60:
        time.sleep(1.2)
        rows=driver.execute_script(SCAN_ROWS)
        pnos=[r['pno'] for r in rows]
        new=[p for p in pnos if p not in seen]
        if page>1 and not new:
            break  # 새 상품 없음 → 마지막 페이지 반복 → 종료
        seen.update(pnos)
        # 아직 처리 안 한 매칭만
        match=[r for r in rows if r['pno'] in targets and r['pno'] not in stats['done']]
        if match:
            log(f"      매칭 {len(match)}개: {[r['pno'] for r in match][:6]}{'…' if len(match)>6 else ''}")
            if execute:
                for r in match:
                    driver.execute_script("""
                      var tr=document.querySelectorAll('table tbody tr')[arguments[0]];
                      if(tr){var cb=tr.querySelector('input[type=checkbox]'); if(cb && !cb.checked){cb.click();}}
                    """, r['idx'])
                time.sleep(0.5)
                if click_text_button(driver, '선택 OFF'):
                    time.sleep(2)
                    for ok in ['확인','예','OK']:
                        if click_text_button(driver, ok): time.sleep(1); break
                    stats['off']+=len(match)
                    log(f"      → 선택 OFF 실행 ({len(match)}개)")
                else:
                    log("      ⚠️ '선택 OFF' 버튼 못찾음")
            for r in match: stats['done'].add(r['pno'])
            stats['matched']+=len(match)
        # 다음 페이지 숫자 버튼 클릭
        page+=1
        if not click_text_button(driver, str(page)):
            break

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--eid', required=True)
    ap.add_argument('--codes', required=True, help='상품번호 파일(텍스트/CSV)')
    ap.add_argument('--csv-col', type=int, default=1, help='CSV일때 상품번호 컬럼(0base)')
    ap.add_argument('--execute', action='store_true', help='실제 OFF 실행(미지정시 드라이런)')
    a=ap.parse_args()
    # 대상 상품번호 로드 (해당 eid 행만)
    targets=set()
    import csv as _csv
    with open(a.codes, encoding='utf-8-sig') as f:
        if a.codes.endswith('.csv'):
            rd=_csv.reader(f); next(rd, None)
            for row in rd:
                if len(row)>a.csv_col and (not row[0] or row[0]==a.eid):
                    m=re.match(r'\d{10}', str(row[a.csv_col]).strip())
                    if m: targets.add(m.group(0))
        else:
            for line in f:
                for tok in re.split(r'[,\s]+', line.strip()):
                    if re.fullmatch(r'\d{10}', tok): targets.add(tok)
    mode='실제OFF' if a.execute else '드라이런(찾기만)'
    log(f"[{a.eid}] 대상 상품번호 {len(targets)}개 / 모드={mode}")
    if not targets: log('대상 없음'); return
    ok, reason = guard.preflight('광고OFF')
    if not ok: log(f'⏭️ 건너뜀 — {reason}'); return
    pw={x.login_id:x.password_enc for x in CrawlerAccount.objects.filter(platform='11st')}.get(a.eid,'')
    stats={'matched':0,'off':0,'done':set()}
    driver=None
    try:
        driver=create_driver(kill_existing=False)
        t=time.time(); sn=_do_login(driver, a.eid, pw)
        log(f"[{a.eid}] 로그인 {time.time()-t:.1f}s sn={sn}")
        if not sn: log('로그인 실패'); return
        driver.implicitly_wait(0); driver.set_page_load_timeout(40)
        _drain_alerts(driver, login_id=a.eid)
        driver.get(ADOFFICE); time.sleep(6)
        # 광고관리
        els=[e for e in driver.find_elements(By.XPATH, "//*[normalize-space(text())='광고관리']") if e.is_displayed()]
        if els: driver.execute_script("arguments[0].click();", els[0]); time.sleep(4)
        # 캠페인 목록
        camp_n=len(find_links(driver))
        log(f"  캠페인 {camp_n}개")
        for ci in range(camp_n):
            # 캠페인 목록 재진입
            els=[e for e in driver.find_elements(By.XPATH, "//*[normalize-space(text())='광고관리']") if e.is_displayed()]
            if els: driver.execute_script("arguments[0].click();", els[0]); time.sleep(3)
            if not click_row_link(driver, ci): continue
            time.sleep(4)
            camp_url=driver.current_url
            grp_n=len(find_links(driver))
            log(f"  [캠페인 {ci+1}/{camp_n}] 광고그룹 {grp_n}개")
            for gi in range(grp_n):
                driver.get(camp_url); time.sleep(3)
                if not click_row_link(driver, gi): continue
                time.sleep(4)
                log(f"    [그룹 {gi+1}/{grp_n}] 상품목록 스캔…")
                process_product_list(driver, targets, a.execute, stats)
        log(f"\n=== [{a.eid}] 완료 — 매칭 {stats['matched']}개 / OFF {stats['off']}개 ({mode}) ===")
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        guard.release_global_lock()
        try: stop_display()
        except Exception: pass

if __name__ == '__main__':
    main()

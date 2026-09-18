"""옥션광고센터(ad.esmplus.com) 일반광고 그룹별 노출요일/시간 전략 — L코드(도매마트) 상품이 있는
광고그룹만 자동으로 찾아서 지정한 요일·시간대로 맞춘다(2026-09-18).

흐름: 계정 로그인 → 일반광고 탭(전체보기) → 그룹 목록(계정당 수십~수백 개) 순회 →
그룹 안 들어가서 상품번호(hdnSiteGoodsNo) 수집 → 로컬 DB(GmarketMyProduct)에서 그 상품번호들의
판매자코드가 LCE_ 로 시작하는지(도매마트 L코드) 확인 → L코드 있으면 노출요일/시간(SellerStrategy)
설정 화면을 열어 지정 요일 8~16시(기본)만 켜지도록 맞추고 저장.

그룹이 계정당 수백 개라 한 번에 다 못 돌리므로 GmarketAdGroupLcodeStatus를 체크포인트로 써서
이어서 진행한다(check_domemart_lcodes.py와 동일 원칙) — run_scan_apply(limit=...)를 계속 호출하는
바깥 루프(백그라운드)가 전체를 천천히 돈다.
"""
import re
import time
import logging
from django.utils import timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger('crawler')

BID_URL = 'https://ad.esmplus.com/cpc/bidmng/bidmanagement'
_LCE_RE = re.compile(r'^LCE_(?:SX|MX)_L\d{7}', re.IGNORECASE)

# 노출요일/시간 그리드의 요일 컬럼 순서(td.cell 0-index): 월,화,수,목,금,토,일
_WEEKDAY_COLS = [1, 2, 3, 4, 5, 6, 7]   # ISO: 1=월..7=일, 그리드 td 순서와 동일


def _log(fn, m):
    logger.info(m)
    if fn:
        fn(m)


def _get_group_names(driver, log_fn=None):
    """일반광고 탭(전체보기 상태)에서 전체 그룹명 목록."""
    from crawlers.gmarket_cpc1_control_crawler import _go_cpc1_tab
    _go_cpc1_tab(driver)
    time.sleep(1)
    rows = driver.find_elements(By.CSS_SELECTOR, '#tbGroupAdStateList tr')
    names = []
    for r in rows:
        tds = r.find_elements(By.TAG_NAME, 'td')
        if len(tds) < 2:
            continue
        name = tds[1].text.strip()
        if name:
            names.append(name)
    _log(log_fn, f'  그룹 {len(names)}개 조회')
    return names


def _open_group(driver, group_name, log_fn=None):
    """그룹명 클릭해서 상세 페이지 진입. 성공 여부 반환.
    이전 그룹 상세 페이지에 남아있을 수 있으므로 매번 목록으로 먼저 돌아간다(2026-09-18 버그 수정 —
    안 돌아가면 두 번째 그룹부터 계속 '못 찾음'으로 실패했음). driver.back()이 목록 탭 풀 리로드
    (_go_cpc1_tab, ~5~6초)보다 훨씬 빨라 우선 시도하고, 목록이 안 뜨면만 풀 리로드로 폴백
    (2026-09-18 속도개선 — 그룹당 ~30초에서 단축 목적, 사용자요청)."""
    from crawlers.gmarket_cpc1_control_crawler import _go_cpc1_tab
    if 'BidGroupManagement' in driver.current_url:
        driver.back()
        time.sleep(0.8)
        try:
            WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.ID, 'tbGroupAdStateList')))
        except Exception:
            _go_cpc1_tab(driver)
            time.sleep(1)
    els = driver.find_elements(By.XPATH, f"//strong[normalize-space()={_xq(group_name)}]")
    if not els:
        _log(log_fn, f'  ⚠ 그룹 못 찾음: {group_name}')
        return False
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', els[0])
    els[0].click()
    time.sleep(1)   # 2026-09-18 속도개선: WebDriverWait이 실제 대기를 담당하므로 고정대기 축소
    try:
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.ID, 'tbBidAdStateList')))
    except Exception:
        pass
    return True


def _xq(s):
    """XPath 문자열 리터럴 안전 인용(따옴표 포함 그룹명 대비)."""
    if "'" not in s:
        return f"'{s}'"
    if '"' not in s:
        return f'"{s}"'
    parts = s.split("'")
    return "concat('" + "', \"'\", '".join(parts) + "')"


def _get_group_product_nos(driver):
    """현재 그룹 상세 페이지의 개별 키워드 테이블에서 상품번호(hdnSiteGoodsNo) 수집."""
    els = driver.find_elements(By.CSS_SELECTOR, "#tbBidAdStateList input[name='hdnSiteGoodsNo']")
    nos = sorted({e.get_attribute('value') for e in els if e.get_attribute('value')})
    return nos


def _check_lcode(login_id, product_nos):
    """로컬 DB에서 이 상품번호들의 판매자코드가 도매마트 L코드(LCE_)인지 확인."""
    from apps.cpc.models import GmarketMyProduct
    if not product_nos:
        return []
    rows = (GmarketMyProduct.objects
            .filter(account__login_id=login_id, product_no__in=product_nos)
            .values_list('seller_product_code', flat=True))
    return sorted({c for c in rows if c and _LCE_RE.match(c.strip())})


def _open_expose_modal(driver, log_fn=None):
    """상세 페이지에서 '노출요일/시간' 행의 노출수정 버튼 클릭."""
    try:
        btn = driver.find_element(
            By.XPATH, "//tr[.//*[contains(text(),'노출요일') and contains(text(),'시간')]]//*[contains(text(),'노출수정')]")
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', btn)
        btn.click()
        time.sleep(1.5)
        WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.ID, 'scheduleGrid')))
        return True
    except Exception as e:
        _log(log_fn, f'  ⚠ 노출설정 팝업 못 엶: {e}')
        return False


def _apply_exposure(driver, on_start, on_end, weekdays, log_fn=None):
    """scheduleGrid에서 지정 요일(weekdays, ISO 1=월..7=일) × on_start~on_end 시간만 ON,
    그 요일의 나머지 시간은 OFF로 맞추고 저장. 지정 안 된(weekdays에 없는) 요일 컬럼은 건드리지 않음.
    반환: 변경 있었는지 여부."""
    grid = driver.find_element(By.ID, 'scheduleGrid')
    rows = grid.find_elements(By.CSS_SELECTOR, 'tbody tr')[1:]  # 첫 행은 빈 템플릿
    if len(rows) != 24:
        _log(log_fn, f'  ⚠ 시간행 24개 아님({len(rows)}) — 건너뜀(안전)')
        return False
    changed = False
    for wd in weekdays:
        if wd not in _WEEKDAY_COLS:
            continue
        col = _WEEKDAY_COLS.index(wd)  # 0=월..6=일
        for hour in range(24):
            tds = rows[hour].find_elements(By.CSS_SELECTOR, 'td.cell')
            cell = tds[col]
            is_on = 'is-active' in (cell.get_attribute('class') or '')
            want_on = on_start <= hour < on_end
            if is_on != want_on:
                driver.execute_script('arguments[0].scrollIntoView({block:"center"});', cell)
                cell.click()
                time.sleep(0.1)
                changed = True
    if not changed:
        _log(log_fn, '  변경 없음(이미 목표 상태)')
        return False
    save_btn = driver.find_element(By.XPATH, "//button[contains(@onclick,'SellerStrategy.SetExposeStrategy')]")
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', save_btn)
    save_btn.click()
    time.sleep(1.5)
    try:
        alert = driver.switch_to.alert
        _log(log_fn, f'  저장 알럿: {alert.text}')
        alert.accept()
        time.sleep(1)
    except Exception:
        pass
    return True


def _disable_weekday_schedule(driver, log_fn=None):
    """노출요일/시간 자체를 '사용안함'으로 꺼서 요일 제한을 통째로 없앤다(2026-09-18 사용자요청
    — 그리드 셀 하나하나 비교/클릭하는 것보다 훨씬 빠름). 이미 '사용안함'이면 변경 없음(False).
    반환: 변경했으면 True."""
    try:
        radio_n = driver.find_element(By.CSS_SELECTOR, "input[name='scheduleWkdSetting'][data-status='N']")
    except Exception as e:
        _log(log_fn, f'  ⚠ 사용안함 라디오 못 찾음: {e}')
        return False
    if radio_n.is_selected():
        return False   # 이미 사용안함 — 변경 불필요
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', radio_n)
    try:
        radio_n.click()
    except Exception:
        driver.execute_script('arguments[0].click();', radio_n)
    time.sleep(0.3)
    save_btn = driver.find_element(By.XPATH, "//button[contains(@onclick,'SellerStrategy.SetExposeStrategy')]")
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', save_btn)
    save_btn.click()
    time.sleep(1.5)
    try:
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        time.sleep(1)
        if '요일을' in text or '선택' in text:
            _log(log_fn, f'  ⚠ 저장 거부됨: {text}')
            return False
    except Exception:
        pass
    return True


def _fix_friday_from_monday(driver, log_fn=None):
    """현재 열린 노출설정 팝업에서 금(4번째 컬럼)을 월(0번째 컬럼) 패턴과 동일하게 맞추고 저장.
    (2026-09-18 사용자요청 — 금토일만 꺼진 채 등록된 그룹들이 많이 발견됨, L코드 무관 전체 대상)
    금요일 헤더 체크박스(#exposureFri)가 먼저 켜져 있어야 시간 셀 저장이 허용된다 — 안 켜진 채
    시간 셀만 클릭하고 저장하면 "요일을 선택하지 않은 경우 시간전략을 설정할 수 없습니다" 알럿으로
    막힘(2026-09-18 실측 확인). 반환: 변경했으면 True."""
    # 금요일 헤더 체크박스 — label 클릭(체크박스 자체는 시각적으로 숨겨져 있을 수 있어 label이 더 안전)
    try:
        fri_chk = driver.find_element(By.ID, 'exposureFri')
        if not fri_chk.is_selected():
            driver.find_element(By.XPATH, "//label[@for='exposureFri']").click()
            time.sleep(0.2)
    except Exception as e:
        _log(log_fn, f'  ⚠ 금요일 헤더 체크박스 못 찾음: {e}')

    grid = driver.find_element(By.ID, 'scheduleGrid')
    rows = grid.find_elements(By.CSS_SELECTOR, 'tbody tr')[1:]
    if len(rows) != 24:
        _log(log_fn, f'  ⚠ 시간행 24개 아님({len(rows)}) — 건너뜀(안전)')
        return False
    changed = False
    for hour in range(24):
        tds = rows[hour].find_elements(By.CSS_SELECTOR, 'td.cell')
        mon_on = 'is-active' in (tds[0].get_attribute('class') or '')
        fri_on = 'is-active' in (tds[4].get_attribute('class') or '')
        if mon_on != fri_on:
            driver.execute_script('arguments[0].scrollIntoView({block:"center"});', tds[4])
            tds[4].click()
            time.sleep(0.1)
            changed = True
    if not changed:
        return False
    save_btn = driver.find_element(By.XPATH, "//button[contains(@onclick,'SellerStrategy.SetExposeStrategy')]")
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', save_btn)
    save_btn.click()
    time.sleep(1.5)
    try:
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        time.sleep(1)
        if '요일을' in text or '선택' in text:
            _log(log_fn, f'  ⚠ 저장 거부됨: {text}')
            return False
    except Exception:
        pass
    return True


def run_fix_friday_all_groups(login_id, log_fn=None):
    """login_id의 일반광고 그룹 전체(L코드 무관)를 순회하며 금요일 노출을 월요일 패턴과 맞춘다.
    한 계정을 통째로(수백 개) 처리하는 1회성 작업 — 체크포인트 없음(재실행해도 이미 맞는 그룹은
    변경없음으로 그냥 넘어가므로 안전, 멱등)."""
    from apps.cpc.models import CrawlerAccount
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver
    from crawlers.gmarket_cpc1_control_crawler import _login

    ok, reason = guard.preflight(f'옥션전략금요일수정_{login_id}', platform='gmarket', wait=True)
    if not ok:
        _log(log_fn, f'⛔ preflight 차단: {reason}')
        return {'ok': False, 'skipped': reason}

    summary = {'groups': 0, 'fixed': 0, 'failed': 0}
    d = None
    try:
        d = create_driver(kill_existing=False)
        d.set_page_load_timeout(45)
        acc = CrawlerAccount.objects.filter(platform='gmarket', login_id=login_id).first()
        if not acc or not _login(d, login_id, acc.password_enc or ''):
            _log(log_fn, f'[{login_id}] ❌ 로그인 실패')
            return {'ok': False, 'skipped': 'login_failed'}
        names = _get_group_names(d, log_fn)
        _log(log_fn, f'[{login_id}] 전체 {len(names)}개 그룹 점검 시작')
        for i, name in enumerate(names, 1):
            try:
                if not _open_group(d, name, log_fn):
                    summary['failed'] += 1
                    continue
                summary['groups'] += 1
                if not _open_expose_modal(d, log_fn):
                    summary['failed'] += 1
                    continue
                did = _disable_weekday_schedule(d, log_fn)
                if did:
                    summary['fixed'] += 1
                    _log(log_fn, f'  ✅ ({i}/{len(names)}) {name} 노출요일/시간 사용안함 처리')
                # 대시보드(옥션광고센터 전략설정 탭)가 진행상황을 볼 수 있도록 같은 상태테이블에 기록
                # (2026-09-18 — 원래 L코드스캔 전용이던 테이블을 이 방식에서도 같이 씀).
                try:
                    from apps.cpc.models import GmarketAdGroupLcodeStatus
                    GmarketAdGroupLcodeStatus.objects.update_or_create(
                        login_id=login_id, group_name=name,
                        defaults={'has_lcode': True, 'strategy_applied': True,
                                  'checked_at': timezone.now(),
                                  'applied_at': timezone.now()})
                except Exception:
                    pass
                # 팝업을 굳이 안 닫아도 다음 그룹에서 driver.back()으로 페이지 자체가 바뀌며
                # 같이 사라짐(2026-09-18 속도개선 — 닫기 클릭+대기 1스텝 생략).
            except Exception as e:
                _log(log_fn, f'  ❌ ({i}/{len(names)}) {name} 예외: {e}')
                summary['failed'] += 1
                # 알럿이 뜬 채로 남아있으면 다음 그룹 클릭도 전부 연쇄실패하므로 여기서 정리
                try:
                    driver_alert = d.switch_to.alert
                    driver_alert.accept()
                except Exception:
                    pass
            if i % 20 == 0:
                _log(log_fn, f'  진행: {i}/{len(names)} (수정 {summary["fixed"]}건)')
    finally:
        if d:
            try:
                d.quit()
            except Exception:
                pass
        try:
            guard.release_global_lock(platform='gmarket')
        except Exception:
            pass

    msg = f'🔧 [{login_id}] 노출요일/시간 사용안함 일괄처리 완료 — 점검 {summary["groups"]} / 수정 {summary["fixed"]} / 실패 {summary["failed"]}'
    _log(log_fn, msg)
    try:
        from apps.cpc import eleven_block_guard as guard2
        guard2._send_telegram_alert(msg)
    except Exception:
        pass
    return {'ok': True, **summary}


def run_scan_apply(schedule, limit=30, log_fn=None):
    """schedule: GmarketAdStrategySchedule 인스턴스. limit=이번 호출에서 새로 확인할 그룹 수(계정 통틀어).
    반환: {'accounts': N, 'groups_checked': N, 'lcode_found': N, 'applied': N}."""
    from apps.cpc.models import CrawlerAccount, GmarketAdGroupLcodeStatus, protected_login_ids
    from apps.cpc import eleven_block_guard as guard
    from crawlers.browser import create_driver
    from crawlers.gmarket_cpc1_control_crawler import _login

    if schedule.accounts:
        login_ids = list(schedule.accounts)
    else:
        protected = protected_login_ids('gmarket')
        login_ids = list(CrawlerAccount.objects.filter(platform='gmarket', is_active=True)
                          .exclude(login_id__in=protected).values_list('login_id', flat=True))

    ok, reason = guard.preflight('옥션광고센터전략스캔', platform='gmarket', wait=True)
    if not ok:
        _log(log_fn, f'⛔ preflight 차단: {reason}')
        return {'ok': False, 'skipped': reason}

    summary = {'accounts': 0, 'groups_checked': 0, 'lcode_found': 0, 'applied': 0}
    remaining = limit
    try:
        for login_id in login_ids:
            if remaining <= 0:
                break
            d = None
            try:
                d = create_driver(kill_existing=False)
                d.set_page_load_timeout(45)
                acc = CrawlerAccount.objects.filter(platform='gmarket', login_id=login_id).first()
                if not acc or not _login(d, login_id, acc.password_enc or ''):
                    _log(log_fn, f'[{login_id}] ❌ 로그인 실패 — 건너뜀')
                    continue
                summary['accounts'] += 1
                names = _get_group_names(d, log_fn)
                known = {s.group_name: s for s in GmarketAdGroupLcodeStatus.objects.filter(login_id=login_id)}
                # 미확인 그룹 먼저, 그 다음 오래된 것(L코드 있는 것만 재적용 확인 대상)
                never = [n for n in names if n not in known]
                stale = [n for n in names if n in known and known[n].has_lcode
                         and not known[n].strategy_applied]
                pending = (never + stale)[:remaining]
                if not pending:
                    _log(log_fn, f'[{login_id}] 확인할 그룹 없음(전부 체크됨)')
                    continue
                _log(log_fn, f'[{login_id}] 이번 회차 {len(pending)}개 그룹 확인')
                for name in pending:
                    if not _open_group(d, name, log_fn):
                        continue
                    product_nos = _get_group_product_nos(d)
                    seller_codes = _check_lcode(login_id, product_nos)
                    has_lcode = bool(seller_codes)
                    summary['groups_checked'] += 1
                    remaining -= 1
                    applied = known.get(name).strategy_applied if name in known else False
                    if has_lcode:
                        summary['lcode_found'] += 1
                        _log(log_fn, f'  ✅ L코드 발견: {name} {seller_codes}')
                        if schedule.enabled:
                            ok_modal = _open_expose_modal(d, log_fn)
                            if ok_modal:
                                weekdays = schedule.weekdays or [1, 2, 3, 4, 5]
                                did = _apply_exposure(d, schedule.on_start, schedule.on_end, weekdays, log_fn)
                                applied = True
                                if did:
                                    summary['applied'] += 1
                                # 팝업 닫기
                                try:
                                    d.find_element(By.XPATH, "//h1[contains(text(),'노출설정')]/following::button[1]").click()
                                except Exception:
                                    pass
                    GmarketAdGroupLcodeStatus.objects.update_or_create(
                        login_id=login_id, group_name=name,
                        defaults={'product_nos': product_nos, 'seller_codes': seller_codes,
                                  'has_lcode': has_lcode, 'strategy_applied': applied,
                                  'checked_at': timezone.now(),
                                  'applied_at': timezone.now() if applied else None})
                    if remaining <= 0:
                        break
            except Exception as e:
                _log(log_fn, f'[{login_id}] ❌ 예외: {e}')
            finally:
                if d:
                    try:
                        d.quit()
                    except Exception:
                        pass
                guard.is_blocked()
    finally:
        try:
            guard.release_global_lock(platform='gmarket')
        except Exception:
            pass

    schedule.last_run_at = timezone.now()
    schedule.save(update_fields=['last_run_at'])
    msg = (f'🎯 [옥션광고센터 전략 스캔] 계정 {summary["accounts"]} / 그룹확인 {summary["groups_checked"]} / '
           f'L코드발견 {summary["lcode_found"]} / 적용 {summary["applied"]}')
    _log(log_fn, msg)
    return {'ok': True, **summary}

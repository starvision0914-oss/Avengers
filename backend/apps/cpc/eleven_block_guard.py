"""11번가 차단 회피용 글로벌 가드.

핵심 아이디어:
- 어떤 작업(OpenAPI/셀레늄 grade/cost/office)이든 차단 신호를 받으면
  파일 락 (`/tmp/avengers_11st_blocked_until`) 에 차단 해제 시각을 기록한다.
- 모든 11st 작업은 매 요청 전에 이 파일을 확인하고, 시각이 미래라면 즉시 중단한다.
- 차단 신호:
  * HTTP 429/503/502 응답
  * `RemoteDisconnected`, `ConnectTimeout`, TCP 단계 실패
  * 셀레늄에서 11st 도메인 페이지 도달 실패가 연속 발생
- 차단 감지 시 기본 30분, 강한 신호(429 5회 이상)면 60분 동결.
- `last_synced` 신선도 체크 헬퍼도 함께 제공한다.
"""
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BLOCK_FILE = Path('/tmp/avengers_11st_blocked_until')
DEFAULT_BLOCK_MINUTES = 30
HARD_BLOCK_MINUTES = 60

# === 플랫폼별 분리 (11번가/지마켓/… 동시 크롤 지원) ===
# 11번가는 기존 경로를 그대로 유지(11st bash 크론 호환). 다른 플랫폼은 platform 접미사로 분리.
# 결과: 플랫폼마다 독립 락·독립 차단상태·독립 도달성 점검 → 11st ∥ gmarket 동시 실행 가능.
def _block_file(platform='11st'):
    return BLOCK_FILE if platform == '11st' else Path(f'/tmp/avengers_{platform}_blocked_until')

def _lock_path(platform='11st'):
    # 11st는 레거시 경로 유지(기존 11st bash 크론이 cut -f1로 pid를 읽음)
    return Path('/tmp/avengers_crawl_chrome.lock') if platform == '11st' \
        else Path(f'/tmp/avengers_crawl_chrome_{platform}.lock')

# 플랫폼별 사전점검 도달성 URL (없으면 11st로 폴백)
_REACH_URL = {
    '11st': 'https://www.11st.co.kr/',
    'gmarket': 'https://www.gmarket.co.kr/',
    'gmarket_b': 'https://www.gmarket.co.kr/',   # 2개조 동시 백필용 별도 락(접속점검은 지마켓 동일)
    'auction': 'https://www.auction.co.kr/',
    'coupang': 'https://www.coupang.com/',
    'smartstore': 'https://smartstore.naver.com/',
}

# 영구정지 계정 — AD OFFICE 접속 불가(광고비/ROAS 확인 안 됨). 정지 해제될 때까지
# AD OFFICE 크롤·ROAS(로하스) 적자판단에서 제외한다. 해제되면 이 목록에서 빼면 됨.
PERMA_BANNED_EIDS = {'rejoice43', 'tmxkqlwus12', 'rejoice777'}


def is_perma_banned(eid):
    return eid in PERMA_BANNED_EIDS


def exclude_perma_banned(qs):
    """CrawlerAccount 쿼리셋에서 영구정지 계정 제외."""
    return qs.exclude(login_id__in=PERMA_BANNED_EIDS)

# 차단 신호로 간주할 에러 키워드 (서버 측 차단/거부만)
BLOCK_KEYWORDS = (
    'ConnectTimeout', 'ConnectionError', 'Connection refused',
    'NewConnectionError', 'Max retries exceeded',
    'Remote end closed', 'Connection aborted',
    'RemoteDisconnected',
    '429', '503', '502', '504',
)

# Chrome/Selenium 로컬 에러 (서버 차단이 아닌 인프라 문제)
LOCAL_CHROME_KEYWORDS = (
    'Timed out receiving message from renderer',
    'chrome not reachable', 'session deleted',
    'invalid session id', 'DevToolsActivePort',
    'disconnected: not connected to DevTools',
    'HTTPConnectionPool', 'localhost',
    'Failed to establish a new connection',
)


def _now():
    return datetime.now()


def is_blocked(platform='11st'):
    """현재 차단 상태인지 확인. (blocked, remaining_seconds, until_dt) 튜플 반환."""
    bf = _block_file(platform)
    if not bf.exists():
        return False, 0, None
    try:
        until_str = bf.read_text(encoding='utf-8').strip()
        until = datetime.fromisoformat(until_str)
    except Exception:
        # 손상된 파일은 무시하고 차단 해제로 간주
        try:
            bf.unlink()
        except Exception:
            pass
        return False, 0, None

    now = _now()
    if until <= now:
        # 차단 해제됨 — 파일 정리
        try:
            bf.unlink()
        except Exception:
            pass
        return False, 0, None

    remaining = (until - now).total_seconds()
    return True, int(remaining), until


def _send_telegram_alert(message):
    """긴급 알림을 텔레그램으로 발송"""
    try:
        import django
        django.setup()
        from apps.cpc.models import TelegramConfig, TelegramRecipient
        import urllib.request
        import json
        cfg = TelegramConfig.objects.first()
        if not cfg or not cfg.bot_token:
            return
        recipients = TelegramRecipient.objects.filter(is_active=True)
        for r in recipients:
            data = json.dumps({'chat_id': r.chat_id, 'text': message}).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage',
                data=data, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f'텔레그램 알림 발송 실패: {e}')


def set_blocked(minutes=DEFAULT_BLOCK_MINUTES, reason='', platform='11st'):
    """차단 상태 기록. 이미 더 긴 차단이 있으면 그것을 유지."""
    now = _now()
    new_until = now + timedelta(minutes=minutes)

    blocked, _, current_until = is_blocked(platform)
    if blocked and current_until and current_until > new_until:
        # 더 긴 기존 차단 유지
        return current_until

    try:
        _block_file(platform).write_text(new_until.isoformat(), encoding='utf-8')
    except Exception as e:
        logger.warning('차단 락 파일 쓰기 실패: %s', e)

    msg = f'⛔ {platform} 글로벌 차단 모드 — {minutes}분 동결 ({new_until:%H:%M:%S} 까지). 사유: {reason}'
    logger.warning(msg)
    print(msg, flush=True)
    _send_telegram_alert(f'🚨 [{platform} 크롤러 긴급]\n\n{msg}\n\n로그인 시도를 중단했습니다.\n{new_until:%H:%M:%S} 이후 자동 재개됩니다.')
    return new_until


def clear_block(platform='11st'):
    """수동 차단 해제 (관리자용)."""
    try:
        bf = _block_file(platform)
        if bf.exists():
            bf.unlink()
            return True
    except Exception:
        pass
    return False


def is_block_signal(error_or_status):
    """예외 객체/문자열/상태코드를 받아 차단 신호인지 판정.
    Chrome 로컬 에러(renderer timeout 등)는 차단 신호로 간주하지 않는다."""
    if isinstance(error_or_status, int):
        return error_or_status in (429, 502, 503, 504)
    s = str(error_or_status)
    if any(k in s for k in LOCAL_CHROME_KEYWORDS):
        return False
    return any(k in s for k in BLOCK_KEYWORDS)


def report_signal(error_or_status, source=''):
    """차단 신호 발견 시 호출. 자동으로 set_blocked 처리.
    HTTP 429/503은 강한 신호로 간주 → 60분 동결."""
    if isinstance(error_or_status, int) and error_or_status in (429, 503):
        return set_blocked(HARD_BLOCK_MINUTES, f'{source}: HTTP {error_or_status}')
    return set_blocked(DEFAULT_BLOCK_MINUTES, f'{source}: {str(error_or_status)[:120]}')


def guard_or_raise(source=''):
    """차단 중이면 RuntimeError 발생. 작업 시작 전 호출."""
    blocked, remaining, until = is_blocked()
    if blocked:
        msg = f'⛔ 11번가 글로벌 차단 중 ({remaining}초 남음, {until:%H:%M:%S} 까지). [{source}] 작업 중단.'
        logger.warning(msg)
        raise RuntimeError(msg)


def guard_and_skip(source=''):
    """차단 중이면 True 반환 (호출자가 스킵 처리). RuntimeError 안 발생."""
    blocked, remaining, until = is_blocked()
    if blocked:
        logger.warning(
            '⛔ 11번가 글로벌 차단 중 (%d초 남음, %s 까지). [%s] 스킵.',
            remaining, until.strftime('%H:%M:%S') if until else '?', source
        )
        return True
    return False


# === 신선도 체크 ===
def is_recently_synced(last_dt, hours=6):
    """last_dt 가 hours 시간 이내면 True (스킵 권고)."""
    if last_dt is None:
        return False
    if isinstance(last_dt, str):
        try:
            last_dt = datetime.fromisoformat(last_dt.replace('Z', '+00:00'))
        except Exception:
            return False
    # tz-aware(예: Django USE_TZ의 UTC 저장)면 aware끼리 비교해야 한다.
    # 예전엔 tzinfo를 떼고 KST datetime.now()와 비교 → UTC↔KST 9시간 오차로
    # 방금 수집한 계정도 '9시간 전'으로 계산돼 신선도 스킵이 전혀 동작하지 않았다(매번 전체 재수집).
    if getattr(last_dt, 'tzinfo', None) is not None:
        from django.utils import timezone as _tz
        return (_tz.now() - last_dt) < timedelta(hours=hours)
    return (_now() - last_dt) < timedelta(hours=hours)


# === 엔드포인트 쿨다운 ===
COOLDOWN_DIR = Path('/tmp')


def _cooldown_path(name):
    return COOLDOWN_DIR / f'avengers_11st_cooldown_{name}'


def cooldown_remaining(name, minutes=5):
    """쿨다운 남은 초 (없으면 0)."""
    p = _cooldown_path(name)
    if not p.exists():
        return 0
    try:
        last = datetime.fromtimestamp(p.stat().st_mtime)
    except Exception:
        return 0
    elapsed = (_now() - last).total_seconds()
    remaining = minutes * 60 - elapsed
    return max(0, int(remaining))


def mark_cooldown(name):
    """엔드포인트 호출 시각 기록."""
    p = _cooldown_path(name)
    try:
        p.write_text(str(int(time.time())), encoding='utf-8')
    except Exception as e:
        logger.warning('쿨다운 파일 쓰기 실패: %s', e)


# === 실패 알림 게이팅 ===
# 11번가 수집 실패의 ~94%는 다음 회차에 자동 회복되는 일시적 오류다.
# 매 실패마다 텔레그램을 보내면 스팸이 되므로:
#   - 같은 (계정,카테고리)가 ALERT_AFTER_CONSEC 회 연속 실패(=회복 못 함)했을 때만,
#   - 그리고 직전 알림 후 ALERT_COOLDOWN_HOURS 이내면 또 보내지 않는다(1일 1회).
# 성공하면 연속 실패 카운터를 0으로 리셋한다.
ALERT_STATE_FILE = Path('/tmp/avengers_11st_alert_state.json')
ALERT_AFTER_CONSEC = 3      # 연속 3회 이상 실패한 계정만 알림(일시적 실패 94%는 다음회차 회복 → 스팸 방지)
ALERT_COOLDOWN_HOURS = 24   # 같은 건은 24시간에 1회만


def _load_alert_state():
    import json
    try:
        return json.loads(ALERT_STATE_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save_alert_state(state):
    import json
    try:
        ALERT_STATE_FILE.write_text(json.dumps(state), encoding='utf-8')
    except Exception as e:
        logger.warning('알림 상태 파일 쓰기 실패: %s', e)


def notify_success(account_id, category='cost'):
    """수집 성공 시 호출 — 해당 (계정,카테고리)의 연속 실패 카운터 리셋."""
    state = _load_alert_state()
    key = f'{account_id}:{category}'
    if key in state:
        del state[key]
        _save_alert_state(state)


def notify_failure(account_id, category, message, seller_name=''):
    """수집 실패 시 호출 — 연속 실패가 임계치 이상이고 쿨다운이 지났을 때만 텔레그램 발송.
    일시적(1회) 실패는 조용히 넘어가 알림 스팸을 막는다."""
    state = _load_alert_state()
    key = f'{account_id}:{category}'
    rec = state.get(key, {'consec': 0, 'last_alert': None})
    rec['consec'] = int(rec.get('consec', 0)) + 1

    should_alert = rec['consec'] >= ALERT_AFTER_CONSEC
    if should_alert and rec.get('last_alert'):
        try:
            last = datetime.fromisoformat(rec['last_alert'])
            if (_now() - last) < timedelta(hours=ALERT_COOLDOWN_HOURS):
                should_alert = False
        except Exception:
            pass

    if should_alert:
        label = {'cost': '광고비', 'product': '상품', 'connect': '접속'}.get(category, category)
        who = f'{account_id} ({seller_name})' if seller_name else account_id
        _send_telegram_alert(
            f'⚠️ [11번가 {label} 수집실패]\n계정: {who}\n'
            f'연속 {rec["consec"]}회 실패 (자동회복 안 됨)\n사유: {str(message)[:150]}')
        rec['last_alert'] = _now().isoformat()
        logger.warning(f'[{key}] 연속 {rec["consec"]}회 실패 → 텔레그램 알림 발송')
    else:
        logger.info(f'[{key}] 실패 {rec["consec"]}회 (임계 미만/쿨다운 — 알림 보류)')

    state[key] = rec
    _save_alert_state(state)


# ===== 플랫폼별 단일 크롤 락 + 사전 점검 (동시 크롤로 인한 IP 차단 방지) =====
# 같은 플랫폼의 크롤러들끼리는 '동일한' 락 파일을 공유해 직렬화(사이트별 IP차단 방지)하되,
# 서로 다른 플랫폼(11st ∥ gmarket ∥ …)은 각자 다른 락이라 '동시에' 돌 수 있다.
# 11st는 레거시 경로(/tmp/avengers_crawl_chrome.lock)를 유지해 기존 11st bash 크론과 호환.
# 형식은 'pid|name|time'이며, bash cron은 첫 필드(cut -d'|' -f1)로 pid를 읽어 호환.
GLOBAL_LOCK = _lock_path('11st')   # 하위호환용 별칭(11st 레거시 경로)


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def acquire_global_lock(name, platform='11st'):
    """플랫폼별 단일 실행 락. 같은 플랫폼의 다른 크롤이 잡고 있으면 (False, holder)."""
    lock = _lock_path(platform)
    if lock.exists():
        try:
            parts = lock.read_text(encoding='utf-8').strip().split('|')
            pid = int(parts[0]); holder = parts[1] if len(parts) > 1 else '?'
        except Exception:
            pid, holder = 0, '?'
        if pid and _pid_alive(pid):
            return False, holder            # 같은 플랫폼의 다른 크롤 실행 중
        try:
            lock.unlink()                   # 죽은 락 회수
        except Exception:
            pass
    try:
        lock.write_text(f'{os.getpid()}|{name}|{_now().isoformat()}', encoding='utf-8')
    except Exception:
        pass
    return True, name


def release_global_lock(platform='11st'):
    try:
        lock = _lock_path(platform)
        if lock.exists():
            lock.unlink()
    except Exception:
        pass


def live_reachable(timeout=10, platform='11st'):
    """해당 플랫폼 사이트에 실제로 닿는지 단건 확인 (HTTP 응답이 오면 도달)."""
    import urllib.request
    import urllib.error
    url = _REACH_URL.get(platform, _REACH_URL['11st'])
    try:
        urllib.request.urlopen(
            urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}),
            timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def notify_problem(name, message):
    """예약 크롤 '심각' 문제 알림 — 하루 1회/이름 게이팅(텔레그램 스팸 방지)."""
    import json as _json
    p = Path('/tmp/avengers_problem_alert.json')
    try:
        state = _json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception:
        state = {}
    today = _now().date().isoformat()
    if state.get(name) == today:
        return  # 오늘 이미 통지함 → 중복 발송 안 함
    state[name] = today
    try:
        p.write_text(_json.dumps(state), encoding='utf-8')
    except Exception:
        pass
    _send_telegram_alert(f'🔴 [예약크롤 {name}] {message}')


def preflight(name, wait=False, wait_timeout=1800, poll=20, platform='11st'):
    """크롤 시작 전 통합 점검. (ok, reason). 모든 점검은 platform 단위로 분리된다.
    ① 이미 차단 중 → 중단  ② 해당 플랫폼 접속 불가 → 차단설정+중단  ③ 같은 플랫폼 다른 크롤 실행 중 → 중단.
    서로 다른 플랫폼(11st ∥ gmarket)은 각자 락이라 동시 실행 가능.
    wait=True(예약 크롤): ③에서 건너뛰지 않고 락이 풀릴 때까지 최대 wait_timeout초 대기 후 재시도.
    통과 시 전역 락을 잡으므로, 끝나면 반드시 release_global_lock(platform) 호출할 것."""
    import time as _time
    blocked, remain, _ = is_blocked(platform)
    if blocked:
        return False, f'이미 차단 중 ({remain // 60}분 남음)'
    if not live_reachable(platform=platform):
        set_blocked(reason=f'{name}: 사전점검 {platform} 접속불가', platform=platform)
        _send_telegram_alert(f'🔴 [{platform} 사전점검] {name} 시작 전 접속불가 — 크롤 중단, 차단모드 진입')
        return False, f'{platform} 접속불가'
    ok, holder = acquire_global_lock(name, platform)
    if ok:
        return True, 'ok'
    if not wait:
        return False, f'같은 플랫폼 다른 크롤 실행 중({holder}) — 동시실행 금지'
    # 예약 크롤: 락이 풀릴 때까지 대기(같은 플랫폼 다른 크롤 종료 후 줄서서 실행)
    waited = 0
    while waited < wait_timeout:
        _time.sleep(poll)
        waited += poll
        blocked, remain, _ = is_blocked(platform)
        if blocked:
            return False, f'대기 중 차단 발생 ({remain // 60}분 남음)'
        ok, holder = acquire_global_lock(name, platform)
        if ok:
            return True, f'ok (락 대기 {waited}s)'
    return False, f'락 대기 시간초과({wait_timeout}s, 직전 holder={holder})'

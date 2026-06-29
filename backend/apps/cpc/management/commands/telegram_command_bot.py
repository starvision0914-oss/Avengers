"""텔레그램 명령봇 — 등록된 사장님 chat_id의 명령을 받아 실행하고 답장.
getUpdates 롱폴링 방식. PM2(avengers-telegram-bot)로 상시 구동.
보안: TelegramRecipient(is_active) chat_id만 명령 허용, 그 외 무시."""
import json
import logging
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger('crawler')
OFFSET_FILE = Path('/tmp/avengers_tg_offset')
BACKEND = '/home/rejoice888/Avengers/backend'

HELP = (
    '🤖 Avengers 명령봇\n\n'
    '/차단 — 11번가 차단 상태\n'
    '/매출 — 2026 매출 요약\n'
    '/커버리지 — 71계정 수집 현황\n'
    '/크롤중지 — 모든 크롤 즉시 중지\n'
    '/광고비크롤 — 광고비 수집 시작\n'
    '/상품크롤 — 상품ROAS 수집 시작\n'
    '/help — 도움말'
)


def _api(token, method, **params):
    url = f'https://api.telegram.org/bot{token}/{method}'
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def _send(token, chat_id, text):
    try:
        _api(token, 'sendMessage', chat_id=chat_id, text=text)
    except Exception as e:
        logger.warning(f'[tgbot] 발송실패: {e}')


def _read_offset():
    try:
        return int(OFFSET_FILE.read_text().strip())
    except Exception:
        return 0


def _write_offset(v):
    try:
        OFFSET_FILE.write_text(str(v))
    except Exception:
        pass


# ---- 명령 핸들러 ----
def _live_11st_reachable():
    """11번가에 실제로 닿는지 단건 테스트. (reachable, detail)"""
    import urllib.request
    try:
        r = urllib.request.urlopen(
            urllib.request.Request('https://www.11st.co.kr/', headers={'User-Agent': 'Mozilla/5.0'}),
            timeout=12)
        return True, f'HTTP {r.status}'
    except urllib.error.HTTPError as e:
        return True, f'HTTP {e.code}'   # 응답이 오면 도달은 됨
    except Exception as e:
        return False, type(e).__name__


def cmd_block(_arg):
    from apps.cpc.eleven_block_guard import is_blocked
    b, r, u = is_blocked()
    live, detail = _live_11st_reachable()
    if not live:
        guard = f'\n(자체타이머: {r // 60}분 남음)' if b else ''
        return f'🔴 11번가 접속 불가 — IP 차단 의심 ({detail}){guard}'
    if b:
        return f'🟡 11번가 접속은 되나 자체 쿨다운 중 ({r // 60}분 남음)'
    return '🟢 11번가 접속 정상 (차단 아님)'


def cmd_sales(_arg):
    from apps.sales.models import SalesRecord
    from django.db.models import Sum, Count
    q = SalesRecord.objects.filter(platform='11st', order_date__year=2026)
    total = abs(q.aggregate(s=Sum('total_price'))['s'] or 0)
    cnt = q.count()
    accs = q.values('seller__seller_id').distinct().count()
    return f'💰 11번가 2026 매출\n합계 {total:,}원\n{cnt:,}건 / {accs}계정'


def cmd_coverage(_arg):
    from apps.cpc.models import St11ProductDaily, ElevenCostHistory, CrawlerAccount
    active = list(CrawlerAccount.objects.filter(platform='11st', is_active=True).values_list('login_id', flat=True))
    p = set(St11ProductDaily.objects.filter(stat_date__year=2026).values_list('eleven_id', flat=True))
    c = set(ElevenCostHistory.objects.filter(transaction_datetime__year=2026).values_list('seller_id', flat=True))
    n = len(active)
    return (f'📊 2026 수집 현황 (활성 {n}계정)\n'
            f'광고비: {len([a for a in active if a in c])}/{n}\n'
            f'상품ROAS: {len([a for a in active if a in p])}/{n}')


def cmd_stop(_arg):
    for pat in ['crawl_11st', 'crawl_gmarket', 'finish_11st', 'sync_products_for_account',
                'chrome.*user-data-dir=/tmp/tmp', 'chromedriver', 'Xvfb']:
        subprocess.run(['pkill', '-9', '-f', pat], capture_output=True)
    Path('/tmp/avengers_crawl_chrome.lock').unlink(missing_ok=True)
    return '🛑 모든 크롤/크롬 중지 완료'


def _start_crawl(cmd_args, label):
    from apps.cpc.eleven_block_guard import is_blocked
    b, r, _ = is_blocked()
    if b:
        return f'⚠️ 차단 중({r // 60}분 남음)이라 시작하지 않았습니다. 해제 후 다시 시도하세요.'
    subprocess.Popen(['/usr/bin/python3', 'manage.py'] + cmd_args, cwd=BACKEND,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f'▶️ {label} 시작했습니다.'


def cmd_cost(_arg):
    return _start_crawl(['crawl_11st_cost'], '광고비 수집')


def cmd_product(_arg):
    return _start_crawl(['crawl_11st_product_daily', '--from', '2026-01-01'], '상품ROAS 수집')


HANDLERS = {
    '차단': cmd_block, '차단확인': cmd_block, 'status': cmd_block, '상태': cmd_block,
    '매출': cmd_sales, '매출확인': cmd_sales,
    '커버리지': cmd_coverage, '현황': cmd_coverage,
    '크롤중지': cmd_stop, '중지': cmd_stop, 'stop': cmd_stop,
    '광고비크롤': cmd_cost, '광고비': cmd_cost,
    '상품크롤': cmd_product, '상품roas': cmd_product,
    'help': lambda a: HELP, '도움말': lambda a: HELP, '명령': lambda a: HELP, 'start': lambda a: HELP,
}


class Command(BaseCommand):
    help = '텔레그램 명령봇 (getUpdates 롱폴링)'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=2)

    def handle(self, *args, **opts):
        from apps.cpc.models import TelegramConfig, TelegramRecipient
        cfg = TelegramConfig.objects.first()
        if not cfg or not cfg.bot_token:
            self.stderr.write('봇 토큰 없음 — 종료')
            return
        token = cfg.bot_token
        logger.info('[tgbot] 시작')
        offset = _read_offset()
        while True:
            try:
                from django.db import close_old_connections
                close_old_connections()
                allowed = set(str(c) for c in TelegramRecipient.objects.filter(is_active=True).values_list('chat_id', flat=True))
                res = _api(token, 'getUpdates', offset=offset + 1, timeout=30)
                for upd in res.get('result', []):
                    offset = upd['update_id']
                    _write_offset(offset)
                    msg = upd.get('message') or upd.get('edited_message') or {}
                    chat_id = str((msg.get('chat') or {}).get('id', ''))
                    text = (msg.get('text') or '').strip()
                    if not text:
                        continue
                    if chat_id not in allowed:
                        logger.info(f'[tgbot] 미등록 chat {chat_id} 무시: {text[:30]}')
                        continue
                    # 캡차 릴레이 훅: /tmp/captcha_pending 있을 때만 답장을 캡차로 인식
                    import os as _os, re as _re
                    if _os.path.exists('/tmp/captcha_pending'):
                        cap = text[2:].strip() if text.startswith('캡차') else text.strip()
                        if text.startswith('캡차') or _re.fullmatch(r'[A-Za-z0-9]{3,12}', cap):
                            with open('/tmp/captcha_answer.txt', 'w') as _f:
                                _f.write(cap)
                            _send(token, chat_id, f'✅ 캡차 "{cap}" 수신 — 로그인 시도합니다')
                            logger.info(f'[tgbot] 캡차 수신 기록: {cap}')
                            continue
                    raw = text.lstrip('/').split()
                    key = raw[0].lower() if raw else ''
                    arg = ' '.join(raw[1:]) if len(raw) > 1 else ''
                    handler = HANDLERS.get(key)
                    try:
                        reply = handler(arg) if handler else f'❓ 모르는 명령: {text}\n\n{HELP}'
                    except Exception as e:
                        reply = f'⚠️ 실행 오류: {str(e)[:150]}'
                        logger.warning(f'[tgbot] 명령오류 {key}: {e}')
                    _send(token, chat_id, reply)
            except Exception as e:
                logger.warning(f'[tgbot] 루프오류: {str(e)[:120]}')
                time.sleep(5)
            time.sleep(opts['interval'])

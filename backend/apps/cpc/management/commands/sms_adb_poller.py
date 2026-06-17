"""
SMS adb 폴링 데몬

폰의 SMS inbox(content://sms/inbox)를 5초마다 직접 쿼리해서
새 SMS를 감지하면 ReceivedSmsMessage에 저장하고 Redis publish + 텔레그램 전송.

NotificationListener 우회 — 메시지 앱 알림 차단 상태에서도 동작.
조건: USB가 꽂혀 있고 adb authorized 상태.
"""
import re
import time
import logging
import subprocess
from datetime import datetime, timezone as dt_tz, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger('crawler')


def _adb_query_inbox(since_id=0):
    """폰 SMS inbox에서 since_id 이후 새 SMS만 쿼리"""
    try:
        cmd = [
            'adb', 'shell', 'content', 'query',
            '--uri', 'content://sms/inbox',
            '--projection', '_id:address:body:date:read',
        ]
        if since_id > 0:
            cmd += ['--where', f'"_id > {since_id}"']
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            err = (out.stderr or '').strip()
            # --where 미지원 시 전체 쿼리 fallback
            if 'Unknown option' in err or 'usage:' in err.lower():
                cmd2 = [
                    'adb', 'shell', 'content', 'query',
                    '--uri', 'content://sms/inbox',
                    '--projection', '_id:address:body:date:read',
                ]
                out = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
                if out.returncode != 0:
                    return None, (out.stderr or '').strip()
                return out.stdout, None
            return None, err
        return out.stdout, None
    except subprocess.TimeoutExpired:
        return None, 'adb timeout'
    except FileNotFoundError:
        return None, 'adb not found'
    except Exception as e:
        return None, str(e)


# Row: 0 _id=24211, address=01077610914, body=..., date=1775893330431, read=0
ROW_RE = re.compile(
    r'Row:\s*\d+\s+_id=(?P<id>\d+),\s*address=(?P<addr>[^,]*),\s*body=(?P<body>.*?),\s*date=(?P<date>\d+),\s*read=(?P<read>\d+)',
    re.DOTALL,
)


def _parse_inbox(text):
    """adb content query 출력 파싱. 여러 줄 body 지원."""
    rows = []
    if not text:
        return rows
    # Row: 단위로 분리
    chunks = re.split(r'(?=Row:\s*\d+\s)', text)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk.startswith('Row:'):
            continue
        m = ROW_RE.search(chunk)
        if not m:
            continue
        try:
            rows.append({
                'id': int(m.group('id')),
                'address': m.group('addr').strip(),
                'body': m.group('body').strip(),
                'date_ms': int(m.group('date')),
                'read': m.group('read') == '1',
            })
        except Exception:
            continue
    return rows


def _adb_query_kakao_notifications():
    """폰의 dumpsys notification에서 카카오톡 메시지 추출.
    카카오톡 알림이 활성화되어 있어야 한다.
    Returns: list of dict {key, title, text, big_text, when}
    """
    try:
        cmd = ['adb', 'shell', 'dumpsys', 'notification', '--noredact']
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if out.returncode != 0:
            return []
        text = out.stdout
    except Exception:
        return []

    results = []
    # NotificationRecord ... pkg=com.kakao.talk ... 블록 단위로 분리
    blocks = re.split(r'NotificationRecord\(', text)
    for blk in blocks:
        if 'pkg=com.kakao.talk' not in blk:
            continue
        # 블록 종료 (다음 NotificationRecord 또는 빈 줄 두 개)
        m_key = re.search(r'key=([^\s]+)', blk)
        m_title = re.search(r'android\.title=String \(([^)]*)\)', blk)
        m_text = re.search(r'android\.text=String \(([^)]*)\)', blk)
        m_big = re.search(r'android\.bigText=(?:String|SpannableString)\s*\(([^)]*)\)', blk)
        m_when = re.search(r'when=(\d+)', blk)
        results.append({
            'key': (m_key.group(1) if m_key else ''),
            'title': (m_title.group(1) if m_title else ''),
            'text': (m_text.group(1) if m_text else ''),
            'big_text': (m_big.group(1) if m_big else ''),
            'when_ms': int(m_when.group(1)) if m_when else 0,
        })
    return results


# 카카오톡 알림 dedup용 (메모리 캐시)
_kakao_seen_keys = set()


def _process_kakao_notifications(my_phone, ReceivedSmsMessage, _publish_sms_event, _forward_sms_to_telegram, stdout):
    """카카오톡 알림 → SMS 데이터 변환 → DB INSERT"""
    notifs = _adb_query_kakao_notifications()
    inserted = 0
    for n in notifs:
        if n['key'] in _kakao_seen_keys:
            continue
        body = n['big_text'] or n['text']
        title = n['title'] or '카카오톡'
        if not body:
            continue
        # 인증번호 패턴이 있는 카카오 메시지만 SMS화 (소음 줄임)
        # 11번가/네이버/구글 등 인증 메시지 패턴
        is_otp = bool(re.search(r'(인증|verification|확인|코드|code)', body, re.I)) or \
                 bool(re.search(r'\b\d{6}\b', body))
        if not is_otp:
            _kakao_seen_keys.add(n['key'])
            continue
        # 중복 방지: 같은 (제목, 본문) 5분 내
        from datetime import timedelta
        recent = ReceivedSmsMessage.objects.filter(
            checkphone_number=f'kakao:{title}'[:20],
            message=body,
            received_at__gte=timezone.now() - timedelta(minutes=5),
        ).exists()
        if recent:
            _kakao_seen_keys.add(n['key'])
            continue

        when_dt = datetime.fromtimestamp(n['when_ms'] / 1000.0, tz=dt_tz.utc) if n['when_ms'] else timezone.now()
        sms = ReceivedSmsMessage.objects.create(
            csphone_number=my_phone,
            checkphone_number=f'kakao:{title}'[:20],
            message=body,
            msg_type='KAKAO',
            receive_time=when_dt,
        )
        stdout.write(f'[adb-poller] +KAKAO id={sms.id} title={title!r} text={body[:50]!r}')
        try:
            _publish_sms_event(sms.id)
        except Exception:
            pass
        try:
            _forward_sms_to_telegram(sms)
        except Exception:
            pass
        _kakao_seen_keys.add(n['key'])
        inserted += 1
    return inserted


def _get_my_phone():
    """이 폰의 주인 번호 (smsApp settings.xml에서)"""
    try:
        out = subprocess.run(
            ['adb', 'shell', 'run-as', 'com.example.smsreceiverapp', 'cat', 'shared_prefs/settings.xml'],
            capture_output=True, text=True, timeout=5,
        )
        m = re.search(r'name="my_phone_number">([^<]+)<', out.stdout)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ''


class Command(BaseCommand):
    help = 'adb로 폰 SMS inbox를 폴링하여 새 SMS를 자동 수신 (NotificationListener 우회)'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=5, help='폴링 간격(초). 기본 5')
        parser.add_argument('--once', action='store_true', help='1회 실행 후 종료 (테스트용)')
        parser.add_argument('--bootstrap-recent', type=int, default=10,
                            help='시작 시 최근 N건은 무시 (기존 SMS 가져올 때 0 으로)')

    def handle(self, *args, **options):
        from apps.cpc.models import ReceivedSmsMessage
        from apps.cpc.views import _publish_sms_event, _forward_sms_to_telegram

        interval = options['interval']
        once = options['once']
        bootstrap_recent = options['bootstrap_recent']

        my_phone = _get_my_phone()
        # run-as 불가(release 빌드)시 DB에서 폰 번호 가져오기
        if not my_phone:
            from apps.cpc.models import SmsDeviceHeartbeat
            hb = SmsDeviceHeartbeat.objects.order_by('-last_seen_at').first()
            if hb:
                my_phone = hb.phone_number
        if not my_phone:
            from apps.cpc.models import SmsPhoneSetting
            ps = SmsPhoneSetting.objects.filter(is_active=True).first()
            if ps:
                my_phone = ps.phone_number
        self.stdout.write(self.style.SUCCESS(f'[adb-poller] 시작 (간격 {interval}s, 내폰={my_phone})'))

        # DB에 저장된 가장 큰 device_sms_id에서 시작 (재기동 시 중복 방지)
        last_db_id = ReceivedSmsMessage.objects.filter(
            device_sms_id__isnull=False
        ).order_by('-device_sms_id').values_list('device_sms_id', flat=True).first() or 0

        # 첫 실행 시: DB에 device_sms_id가 없으면 폰의 현재 max에서 bootstrap만큼 빼고 시작
        if last_db_id == 0:
            out, err = _adb_query_inbox()
            if err:
                self.stdout.write(self.style.ERROR(f'[adb-poller] 첫 쿼리 실패: {err}'))
            elif out:
                rows = _parse_inbox(out)
                if rows:
                    max_id = max(r['id'] for r in rows)
                    last_db_id = max(0, max_id - bootstrap_recent)
                    self.stdout.write(f'[adb-poller] 부트스트랩 last_id={last_db_id} (폰 max={max_id})')
        else:
            self.stdout.write(f'[adb-poller] DB 마지막 device_sms_id={last_db_id} 부터 재개')

        consecutive_errors = 0

        while True:
            try:
                out, err = _adb_query_inbox(since_id=last_db_id)
                if err:
                    consecutive_errors += 1
                    if consecutive_errors % 12 == 1:
                        self.stdout.write(self.style.WARNING(f'[adb-poller] adb 오류: {err}'))
                    if once:
                        break
                    time.sleep(interval)
                    continue

                consecutive_errors = 0
                rows = _parse_inbox(out or '')
                # device_sms_id 기준으로 신규만, 오래된 것부터
                new_rows = sorted([r for r in rows if r['id'] > last_db_id], key=lambda x: x['id'])

                for r in new_rows:
                    body = r['body']
                    addr = r['address']
                    device_id = r['id']
                    if not body:
                        last_db_id = max(last_db_id, device_id)
                        continue

                    # device_sms_id로 정확 dedup
                    if ReceivedSmsMessage.objects.filter(device_sms_id=device_id).exists():
                        last_db_id = max(last_db_id, device_id)
                        continue

                    receive_dt = datetime.fromtimestamp(r['date_ms'] / 1000.0, tz=dt_tz.utc)

                    # Fuzzy dedup: NotificationListener가 먼저 잡았을 수 있음.
                    # BiDi 마커(⁨ ⁩) 제거 후 (number, message) + 최근 5분 매칭이면 device_sms_id만 백필하고 스킵
                    from datetime import timedelta
                    norm_addr = re.sub(r'[\u2068\u2069]', '', addr).strip()
                    recent_qs = ReceivedSmsMessage.objects.filter(
                        message=body,
                        received_at__gte=timezone.now() - timedelta(minutes=5),
                    )
                    fuzzy_match = None
                    for cand in recent_qs:
                        cand_addr = re.sub(r'[\u2068\u2069]', '', cand.checkphone_number or '').strip()
                        if cand_addr == norm_addr:
                            fuzzy_match = cand
                            break
                    if fuzzy_match:
                        # 같은 SMS — 백필만 하고 INSERT 안 함
                        if fuzzy_match.device_sms_id is None:
                            fuzzy_match.device_sms_id = device_id
                            fuzzy_match.save(update_fields=['device_sms_id'])
                        last_db_id = max(last_db_id, device_id)
                        continue

                    msg_bytes = len(body.encode('utf-8'))
                    msg_type = 'LMS' if msg_bytes > 80 else 'SMS'

                    sms = ReceivedSmsMessage.objects.create(
                        csphone_number=addr,
                        checkphone_number=my_phone,
                        message=body,
                        msg_type=msg_type,
                        receive_time=receive_dt,
                        device_sms_id=device_id,
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'[adb-poller] +SMS id={sms.id} (phone _id={device_id}) from={addr} msg={body[:40]!r}'
                    ))
                    try:
                        _publish_sms_event(sms.id)
                    except Exception:
                        pass
                    try:
                        _forward_sms_to_telegram(sms)
                    except Exception:
                        pass

                    last_db_id = max(last_db_id, device_id)

                # 카카오톡 알림도 함께 폴링
                try:
                    _process_kakao_notifications(my_phone, ReceivedSmsMessage,
                                                  _publish_sms_event, _forward_sms_to_telegram,
                                                  self.stdout)
                except Exception as e:
                    if consecutive_errors == 0:
                        self.stdout.write(self.style.WARNING(f'[adb-poller] kakao 폴링 오류: {e}'))

                if once:
                    break
                time.sleep(interval)

            except KeyboardInterrupt:
                self.stdout.write('\n[adb-poller] 종료')
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[adb-poller] 루프 오류: {e}'))
                if once:
                    break
                time.sleep(interval)

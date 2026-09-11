"""11번가 광고비 시간별 증가 감지 → 그 계정 캠페인을 조사해 8~16시(평일)만 노출되도록
전략설정을 즉시 자동 적용하는 가드. 지마켓의 cron_gmarket_hourly_ad_guard.sh(증가시 광고OFF)와
같은 취지지만, 11번가는 완전 OFF가 아니라 "전략설정(노출 스케줄)"으로 8~16시만 켜지게 제한한다
(2026-09-07 사용자 요청 — "전략설정이 안 되어 있어서 그런 거잖아? 구축해줘").

흐름:
  1) 직전 --window-min(기본 70)분 CPC 증가가 있던 계정을 ElevenCostHistory에서 찾는다
     (notify_11st_adcost_hourly와 동일 판정 로직).
  2) 계정마다 crawlers.eleven_ad_strategy.list_campaigns()로 실제 캠페인 이름을 라이브 조회.
  3) run_strategy()로 그 계정의 전체 캠페인에 on_start~on_end(기본 8~16시)·평일 전략을 실제 적용.
  4) St11AdStrategySchedule(단일 레코드)에 계정/캠페인을 누적 병합 + enabled=True로 저장
     (apply_st11_ad_strategy 안전망 재적용 대상에도 포함되게).
  5) 텔레그램으로 결과 통지.

사용:
  python manage.py guard_11st_ad_schedule_on_spike               # 실제 적용
  python manage.py guard_11st_ad_schedule_on_spike --dry-run     # 대상 계정만 출력
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '11번가 CPC 증가 감지 계정에 8~16시 전략설정 자동 적용(가드)'

    def add_arguments(self, parser):
        parser.add_argument('--window-min', type=int, default=70, help='증가분 판정 창(분), 기본 70')
        parser.add_argument('--on-start', type=int, default=8)
        parser.add_argument('--on-end', type=int, default=16)
        parser.add_argument('--dry-run', action='store_true', help='대상 계정/캠페인만 찾고 실제 적용 없음')
        parser.add_argument('--accounts', nargs='*', help='자동감지 대신 특정 계정만 지정(테스트용)')
        parser.add_argument('--cooldown-hours', type=int, default=6,
                             help='이미 적용된(sched.accounts 포함) 계정은 마지막 적용 후 이 시간(기본 6h) '
                                  '이내면 재적용을 건너뜀 — CPC가 늘어도 이미 스케줄이 걸려있으면 정상 동작이므로 '
                                  '매시간 같은 계정을 처음부터 전부(수백개 그룹) 재적용하는 낭비를 막는다 '
                                  '(2026-09-11: rejoice666 1건이 3시간36분째 안 끝나 다른 11번가 크롤을 막은 사고 이후 도입).')

    def handle(self, *args, **o):
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Sum
        from apps.cpc.models import (ElevenCostHistory, CrawlerAccount, St11AdStrategyLog,
                                      St11AdStrategySchedule, protected_login_ids)
        from apps.cpc import eleven_block_guard as guard
        from crawlers.eleven_ad_strategy import list_campaigns, run_strategy

        on_start, on_end = o['on_start'], o['on_end']
        weekdays = [1, 2, 3, 4, 5]

        if o.get('accounts'):
            spiking = list(o['accounts'])
        else:
            now = timezone.localtime()
            win = now - timedelta(minutes=o['window_min'])
            ids = list(CrawlerAccount.objects.filter(platform='11st', is_active=True)
                       .values_list('login_id', flat=True))
            q = (ElevenCostHistory.objects
                 .filter(transaction_type='CPC', transaction_datetime__gte=win, seller_id__in=ids)
                 .values('seller_id').annotate(s=Sum('amount')))
            spiking = [r['seller_id'] for r in q if abs(r['s'] or 0) > 0]

        protected = protected_login_ids('11st')
        spiking = [e for e in spiking if e not in protected and not guard.is_perma_banned(e)]

        if not spiking:
            self.stdout.write('증가 감지된 계정 없음 — 종료')
            return

        sched = St11AdStrategySchedule.objects.order_by('id').first()
        if not sched:
            sched = St11AdStrategySchedule(name='스파이크 가드(자동)', accounts=[], campaigns=[],
                                           on_start=on_start, on_end=on_end, weekdays=weekdays, enabled=False)

        # 쿨다운(2026-09-11 도입): 이미 스케줄이 걸려있는 계정(sched.accounts)은 최근에 적용된 지
        # cooldown_hours 이내면 건너뛴다. CPC가 계속 늘어도 이미 8~16시 전략이 걸려있으면 정상 동작이라
        # 매시간 처음부터 재적용(계정당 수백 개 그룹, 각 15~20초)할 필요가 없다 — rejoice666 1건이
        # 3시간36분째 안 끝나 다른 11번가 크롤(광고비 수집 포함)까지 락으로 막은 사고 이후 추가.
        if not o.get('accounts'):
            cooldown = timedelta(hours=o['cooldown_hours'])
            already = set(sched.accounts or [])
            if sched.last_applied_at and (timezone.localtime() - sched.last_applied_at) < cooldown:
                skipped = [e for e in spiking if e in already]
                if skipped:
                    self.stdout.write(
                        f'쿨다운 스킵({o["cooldown_hours"]}h 이내 이미 적용됨): {", ".join(skipped)}')
                spiking = [e for e in spiking if e not in already]

        if not spiking:
            self.stdout.write('쿨다운으로 전부 스킵 — 종료')
            return
        self.stdout.write(f'대상 계정({len(spiking)}): {", ".join(spiking)}')
        if o['dry_run']:
            return

        applied, results = [], []
        for eid in spiking:
            run_id, spiked_campaigns = list_campaigns(eid)
            # St11AdofficeCampaign은 upsert 전용(이미 있는 이름은 collected_at을 안 건드림)이라
            # collected_at으로 "이번 조회분만" 걸러내면 재실행시 0건이 되는 버그가 있었다(2026-09-07).
            # 대신 이번 run_id의 St11AdStrategyLog(status='CAMP') 기록에서 이름을 직접 뽑는다 —
            # list_campaigns()가 매 호출마다 찾은 캠페인명을 전부 CAMP 로그로 남기므로 항상 최신.
            names = list(
                St11AdStrategyLog.objects.filter(run_id=run_id, status='CAMP')
                .order_by('id').values_list('detail', flat=True).distinct()
            )
            if not names:
                self.stdout.write(f'[{eid}] 캠페인 조회 실패/없음 — 건너뜀 (run_id={run_id})')
                results.append(f'{eid}: 캠페인 없음')
                continue
            # 2026-09-11(사용자 요청): 계정 전체가 아니라 실제로 총비용이 늘어난 캠페인만 좁혀서 적용
            # — list_campaigns()가 St11AdofficeCampaign의 직전 저장값과 비교해 찾아준다.
            # 처음 보는 캠페인(직전값 없음)이라 비교 불가한 경우는 안전하게 전체 캠페인으로 폴백.
            targets = [n for n in names if n in spiked_campaigns] or names
            narrowed = len(targets) < len(names)
            self.stdout.write(
                f'[{eid}] 캠페인 {len(names)}개 중 {len(targets)}개'
                + (' (증가 캠페인만 좁힘)' if narrowed else ' (전체 — 직전값 없어 비교불가/전부증가)')
                + f' → {on_start}~{on_end}시 전략 적용')
            run_strategy([eid], targets, on_start=on_start, on_end=on_end, weekdays=weekdays,
                        execute=True, source='spike_guard')
            applied.append((eid, targets))
            names = targets
            results.append(f'{eid}: 캠페인 {len(names)}개 적용')

            merged_accounts = set(sched.accounts or []) | {eid}
            merged_campaigns = set(sched.campaigns or []) | set(names)
            sched.accounts = sorted(merged_accounts)
            sched.campaigns = sorted(merged_campaigns)

        if applied:
            sched.on_start, sched.on_end, sched.weekdays = on_start, on_end, weekdays
            sched.enabled = True
            sched.last_applied_at = timezone.now()
            sched.save()

        msg = (f'🛡 [11번가 광고비 증가감지 → {on_start}~{on_end}시 전략 자동적용]\n'
               + '\n'.join(results))
        self.stdout.write(msg)
        try:
            guard._send_telegram_alert(msg)
        except Exception as e:
            self.stderr.write(f'텔레그램 발송 실패: {e}')

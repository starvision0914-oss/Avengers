"""
로또 자동 평가 — 매주 토요일 21시 cron으로 실행 예정 (추첨 ~20:45 직후).

작업
1) 네이버 폴백으로 최신 회차 동기화 시도 (이미 dhlottery WAF 차단됨)
2) 저장된 모든 LottoPrediction 평가 (등수 자동 판정)
3) 결과 요약을 표준출력 + 로그파일 누적
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.lotto import services
from apps.lotto.models import LottoHistory, LottoPrediction

LOG_FILE = Path('/tmp/lotto_saturday_eval.log')
SUMMARY_FILE = Path('/tmp/lotto_saturday_summary.json')


class Command(BaseCommand):
    help = '매주 토요일 20시 — 최신 회차 동기화 + 저장된 예측 일괄 평가'

    def add_arguments(self, parser):
        parser.add_argument('--skip-sync', action='store_true', help='동기화 생략')
        parser.add_argument('--prediction-id', type=int, default=None,
                            help='특정 예측만 평가')

    def handle(self, *args, **opts):
        started_at = datetime.now()
        header = f'═════ 로또 자동 평가 {started_at.strftime("%Y-%m-%d %H:%M:%S")} ═════'
        self._out(header)

        # 1) 동기화
        if not opts['skip_sync']:
            self._out('[1/2] 최신 회차 동기화 시도...')
            try:
                r = services.sync(max_to_fetch=10)
                self._out(f"     저장 {r['saved']}건, 차단 {r['blocked']}, source={r.get('source')}, "
                          f"DB={r.get('min')}~{r.get('max')} ({r.get('count')}회)")
                if r.get('log'):
                    for ln in r['log'][-5:]:
                        self._out(f'     · {ln}')
            except Exception as e:
                self._out(f'     동기화 오류: {type(e).__name__}: {e}')
        else:
            self._out('[1/2] 동기화 스킵 (--skip-sync)')

        # 2) 예측 평가
        if opts['prediction_id']:
            preds = LottoPrediction.objects.filter(id=opts['prediction_id'])
        else:
            preds = LottoPrediction.objects.all()
        self._out(f'[2/2] 평가 대상: {preds.count()}개 예측')

        latest = LottoHistory.objects.order_by('-drw_no').first()
        latest_drw = latest.drw_no if latest else 0
        self._out(f'     DB 최신 회차: {latest_drw}회')

        rank_tally = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 0: 0}
        pending = 0
        results = []
        for p in preds:
            if p.target_round > latest_drw:
                pending += 1
                continue
            r = services.check_prediction(p.id)
            if r.get('pending'):
                pending += 1
                continue
            wc = r.get('win_count', {})
            for rk in range(0, 6):
                rank_tally[rk] = rank_tally.get(rk, 0) + wc.get(rk, 0)
            best = r.get('best_rank')
            best_label = r.get('best_rank_label', '미당첨')
            self._out(
                f'  · #{p.id} ({p.target_round}회) {len(p.combinations)}조합 → 최고 {best_label} '
                f'(1등 {wc.get(1,0)}/2등 {wc.get(2,0)}/3등 {wc.get(3,0)}/'
                f'4등 {wc.get(4,0)}/5등 {wc.get(5,0)}/미당첨 {wc.get(0,0)})'
            )
            results.append({
                'prediction_id': p.id,
                'target_round': p.target_round,
                'best_rank': best,
                'best_rank_label': best_label,
                'win_count': wc,
            })

        # 요약
        self._out('─' * 60)
        self._out(
            f'총 평가 {len(results)}개 (대기 {pending}개) | '
            f'1등 {rank_tally[1]} · 2등 {rank_tally[2]} · 3등 {rank_tally[3]} · '
            f'4등 {rank_tally[4]} · 5등 {rank_tally[5]} · 미당첨 {rank_tally[0]}'
        )

        finished_at = datetime.now()
        summary = {
            'started_at': started_at.isoformat(),
            'finished_at': finished_at.isoformat(),
            'latest_round': latest_drw,
            'evaluated': len(results),
            'pending': pending,
            'rank_tally': rank_tally,
            'results': results,
        }
        try:
            SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                    encoding='utf-8')
            self._out(f'요약 저장: {SUMMARY_FILE}')
        except Exception as e:
            self._out(f'요약 저장 실패: {e}')

    def _out(self, msg):
        self.stdout.write(msg)
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')
        except Exception:
            pass

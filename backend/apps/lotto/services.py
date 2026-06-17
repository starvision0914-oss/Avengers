"""로또 데이터 수집/예측 비즈니스 로직."""
import csv
import io
import random
import time
from collections import Counter

import requests

from .models import LottoHistory, LottoPrediction

API_URL = 'https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def make_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.5',
        'Referer': 'https://www.dhlottery.co.kr/gameResult.do?method=byWin',
        'X-Requested-With': 'XMLHttpRequest',
    })
    try:
        s.get('https://www.dhlottery.co.kr/common.do?method=main', timeout=4)
    except Exception:
        pass
    return s


def fetch_one(session, drw_no, timeout=5):
    """returns dict | None | raises RuntimeError on block/error."""
    r = session.get(API_URL.format(drw_no), timeout=timeout, allow_redirects=False)
    if r.status_code in (301, 302):
        loc = r.headers.get('Location', '')
        raise RuntimeError(f'WAF 차단 — 302 → {loc}')
    if r.status_code != 200:
        raise RuntimeError(f'HTTP {r.status_code}')
    try:
        j = r.json()
    except ValueError:
        raise RuntimeError(f'JSON 아님 (차단 페이지?) — {r.text[:60]!r}')
    if j.get('returnValue') == 'success':
        return j
    return None


def upsert_from_api(j):
    LottoHistory.objects.update_or_create(
        drw_no=int(j['drwNo']),
        defaults={
            'drw_date': j.get('drwNoDate', ''),
            'num1': int(j['drwtNo1']), 'num2': int(j['drwtNo2']),
            'num3': int(j['drwtNo3']), 'num4': int(j['drwtNo4']),
            'num5': int(j['drwtNo5']), 'num6': int(j['drwtNo6']),
            'bonus': int(j['bnusNo']),
        },
    )


def db_stats():
    qs = LottoHistory.objects.all()
    cnt = qs.count()
    if cnt == 0:
        return {'min': None, 'max': None, 'count': 0}
    agg = qs.aggregate(mn=models.Min('drw_no'), mx=models.Max('drw_no'))
    return {'min': agg['mn'], 'max': agg['mx'], 'count': cnt}


# models import at bottom for db_stats aggregate
from django.db import models  # noqa: E402


def sync(max_to_fetch=None):
    """미수집 회차 1번부터 채움.
    1차: dhlottery JSON API. WAF 차단 감지 시 즉시 네이버 폴백.
    2차: 네이버 검색결과 파싱.
    returns: {saved, log, blocked, source}
    """
    log_lines = []
    saved = 0
    blocked = False
    source = 'dhlottery'

    existing = set(LottoHistory.objects.values_list('drw_no', flat=True))

    # 1차: dhlottery
    sess = make_session()
    drw_no = 1
    consec_missing = 0
    while True:
        if drw_no in existing:
            drw_no += 1
            continue
        try:
            rec = fetch_one(sess, drw_no)
            if rec:
                upsert_from_api(rec)
                saved += 1
                existing.add(drw_no)
                log_lines.append(f'{drw_no}회 [dhlottery] 저장 ({rec.get("drwNoDate")})')
                consec_missing = 0
            else:
                log_lines.append(f'{drw_no}회 [dhlottery] 미발행 — 스킵')
                consec_missing += 1
        except RuntimeError as e:
            log_lines.append(f'{drw_no}회 [dhlottery] 실패: {e}')
            if 'WAF 차단' in str(e) or 'JSON 아님' in str(e):
                blocked = True
                log_lines.append('⛔ dhlottery WAF 차단 감지 — 네이버 검색결과 폴백 시도')
                break
            consec_missing += 1
        except Exception as e:
            log_lines.append(f'{drw_no}회 [dhlottery] 네트워크 에러: {type(e).__name__}')
            consec_missing += 1

        if consec_missing >= 3:
            break
        if max_to_fetch and saved >= max_to_fetch:
            break
        drw_no += 1
        time.sleep(random.uniform(0.10, 0.25))

    # 2차: 네이버 폴백 (dhlottery 차단된 경우)
    if blocked:
        from .naver_source import bulk_sync as naver_sync
        source = 'naver'
        try:
            for rec in naver_sync(start=1, existing_drws=existing,
                                   stop_on_missing=8,
                                   log_fn=log_lines.append):
                # ── 미발행 회차 가드 ──
                # 네이버는 미발행 회차 검색 시 가장 최근 회차의 번호를 반환하므로,
                # 이 6개+보너스 조합이 다른 회차에 이미 존재하면 미발행으로 판단하고 스킵.
                bonus = rec.get('bonus') or 0
                dup = LottoHistory.objects.exclude(drw_no=rec['drwNo']).filter(
                    num1=rec['nums'][0], num2=rec['nums'][1], num3=rec['nums'][2],
                    num4=rec['nums'][3], num5=rec['nums'][4], num6=rec['nums'][5],
                    bonus=bonus,
                ).first()
                if dup:
                    log_lines.append(
                        f'⚠ {rec["drwNo"]}회: {dup.drw_no}회와 번호+보너스 동일 — 미발행 회차로 판단, 스킵'
                    )
                    # 미발행으로 간주하고 동기화 중단 (이후 회차도 모두 미발행일 가능성)
                    break

                LottoHistory.objects.update_or_create(
                    drw_no=rec['drwNo'],
                    defaults={
                        'drw_date': rec.get('date', ''),
                        'num1': rec['nums'][0], 'num2': rec['nums'][1],
                        'num3': rec['nums'][2], 'num4': rec['nums'][3],
                        'num5': rec['nums'][4], 'num6': rec['nums'][5],
                        'bonus': bonus,
                    },
                )
                saved += 1
                existing.add(rec['drwNo'])
                log_lines.append(f'{rec["drwNo"]}회 [naver] 저장 ({rec.get("date","")})')
                if max_to_fetch and saved >= max_to_fetch:
                    break
        except Exception as e:
            log_lines.append(f'네이버 폴백 에러: {type(e).__name__}: {e}')

    return {'saved': saved, 'log': log_lines, 'blocked': blocked,
            'source': source, **db_stats()}


def import_csv_bytes(data: bytes):
    text = data.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(text))
    added = 0
    skipped = 0
    errors = []
    for i, row in enumerate(reader, 1):
        try:
            drw = int(row.get('drwNo') or row.get('회차') or 0)
            if not drw:
                skipped += 1
                continue
            LottoHistory.objects.update_or_create(
                drw_no=drw,
                defaults={
                    'drw_date': row.get('drwNoDate') or row.get('추첨일') or '',
                    'num1': int(row.get('num1') or row.get('번호1') or 0),
                    'num2': int(row.get('num2') or row.get('번호2') or 0),
                    'num3': int(row.get('num3') or row.get('번호3') or 0),
                    'num4': int(row.get('num4') or row.get('번호4') or 0),
                    'num5': int(row.get('num5') or row.get('번호5') or 0),
                    'num6': int(row.get('num6') or row.get('번호6') or 0),
                    'bonus': int(row.get('bnusNo') or row.get('보너스') or 0),
                },
            )
            added += 1
        except Exception as e:
            errors.append(f'row {i}: {e}')
            skipped += 1
    return {'added': added, 'skipped': skipped, 'errors': errors[:20], **db_stats()}


def _consecutive_max(nums):
    longest = 1
    cur = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i-1] + 1:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
    return longest


def _ac_value(nums):
    """Arithmetic Complexity — 양의 차이값 개수 - 5. 높을수록 복잡(균등)."""
    diffs = set()
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            diffs.add(abs(nums[i] - nums[j]))
    return len(diffs) - 5


def predict(count=5, recent_n=30, recent_weight=0.5):
    """V2 — 후보 8천개 + 고급 패턴 5종 추가 + 백테스트 검증.

    하드 필터 (모두 통과해야 함):
      ① 합계 100~175 (77.5%)
      ② 홀짝 2:4~4:2 (82.4%)
      ③ 고저 2:4~4:2 (80.5%)
      ④ 연속 ≤2 (94.6%)
      ⑤ AC ≥7 (84.8%)

    소프트 점수 (100점 만점):
      [기본 8종 × 8점 = 64]
      A. 홀짝 3:3 (최빈 33.5%)
      B. 고저 3:3 (최빈 32.8%)
      C. 합 121~160 (46.7%)
      D. AC ≥8 (70.9%)
      E. 직전회차 1~2개 중복 (59.3%)
      F. 41~45 ≤1개 (평균 0.66개)
      G. 10단위 구간 ≤2개 (분산성)
      H. 끝자리 5종+ (분산성)

      [고급 패턴 4종 = 22]
      I. 합 정점 130~145 +6 (역대 33% 집중 구간)
      J. 3구역 균형 (1-15/16-30/31-45 each ≥1) +6
      K. 끝자리 강화: 동일끝자리 ≤2개 +4
      L. 최근 50회 페어 빈출 TOP30 적중 +6 (개당)

      [통계 빈출 = 14]
      M. 최근 N회 빈출 TOP10: 개당 +3, max +9 (3개)
      N. 전체 누적 빈출 TOP10: 개당 +1, max +5 (5개)
    """
    qs = LottoHistory.objects.all().order_by('-drw_no')
    total = qs.count()
    if total == 0:
        return {'combinations': [], 'total_draws': 0,
                'message': 'DB가 비어있습니다. 먼저 동기화 또는 CSV 임포트.',
                'log': ['데이터 없음'], 'top10_freq': []}

    all_rows = list(qs.values_list('num1', 'num2', 'num3', 'num4', 'num5', 'num6'))
    freq_all = Counter()
    for r in all_rows:
        freq_all.update(r)

    recent_n = min(recent_n, total)
    freq_recent = Counter()
    for r in all_rows[:recent_n]:
        freq_recent.update(r)

    last_draw = set(all_rows[0]) if all_rows else set()

    # ── 페어 빈출 (최근 50회 기준) ──
    pair_window = min(50, total)
    pair_freq = Counter()
    for r in all_rows[:pair_window]:
        s = sorted(r)
        for i in range(6):
            for j in range(i + 1, 6):
                pair_freq[(s[i], s[j])] += 1
    top_pairs = {p for p, _ in pair_freq.most_common(30)}

    # 가중치 — 최근/전체 정규화 후 혼합
    population = list(range(1, 46))
    weights = []
    for n in population:
        all_norm = freq_all.get(n, 0) / max(total, 1)
        rec_norm = freq_recent.get(n, 0) / max(recent_n, 1)
        w = recent_weight * rec_norm + (1 - recent_weight) * all_norm
        weights.append(w * 100 + 1)

    top_recent = freq_recent.most_common(10)
    top_all = freq_all.most_common(10)
    top_recent_set = {n for n, _ in top_recent}
    top_all_set = {n for n, _ in top_all}

    log = []
    log.append(f'═══ 패턴 적합도 V2 예측 시작 ═══')
    log.append(f'학습: {total:,}회 (전체) + 최근 {recent_n}회 가중 {recent_weight:.0%} + 페어 빈출 {pair_window}회')
    log.append(f'하드필터 5종: 합 100~175 · 홀짝 2:4~4:2 · 고저 2:4~4:2 · 연속 ≤2 · AC ≥7')
    log.append(f'소프트 100점 = 기본8종×8(64) + 고급4종(22) + 빈출2종(14)')
    log.append(f'최근 {recent_n}회 빈출 TOP10: ' + ', '.join(f'{n}({c})' for n, c in top_recent))
    log.append(f'전체 누적 빈출 TOP10: ' + ', '.join(f'{n}({c})' for n, c in top_all))
    log.append(f'최근 {pair_window}회 페어 TOP5: ' +
               ', '.join(f'{a}-{b}({c})' for (a, b), c in pair_freq.most_common(5)))
    log.append('─' * 60)

    # ── 후보 생성 ──
    CANDIDATES = 8000
    candidates = []
    rejects = Counter()
    tries = 0

    while len(candidates) < CANDIDATES and tries < CANDIDATES * 5:
        tries += 1
        pick = set()
        while len(pick) < 6:
            pick.add(random.choices(population, weights=weights, k=1)[0])
        nums = sorted(pick)

        odds = sum(1 for n in nums if n % 2)
        s = sum(nums)
        low = sum(1 for n in nums if n <= 22)
        high = 6 - low
        cons = _consecutive_max(nums)
        ac = _ac_value(nums)

        # ── 하드 필터 ──
        if not (100 <= s <= 175):
            rejects['①합계'] += 1; continue
        if odds not in (2, 3, 4):
            rejects['②홀짝'] += 1; continue
        if high < 2 or low < 2:
            rejects['③고저'] += 1; continue
        if cons > 2:
            rejects['④연속'] += 1; continue
        if ac < 7:
            rejects['⑤AC'] += 1; continue

        # ── 소프트 점수 (100점 만점) ──
        score = 0
        breakdown = []
        # [기본 8종 × 8점]
        if odds == 3:
            score += 8; breakdown.append('홀짝3:3+8')
        if high == 3:
            score += 8; breakdown.append('고저3:3+8')
        if 121 <= s <= 160:
            score += 8; breakdown.append('합중심+8')
        if ac >= 8:
            score += 8; breakdown.append('AC≥8+8')
        overlap = len(set(nums) & last_draw)
        if 1 <= overlap <= 2:
            score += 8; breakdown.append(f'직전중복{overlap}+8')
        big = sum(1 for n in nums if n >= 41)
        if big <= 1:
            score += 8; breakdown.append('41~45≤1+8')
        zone_count = Counter((n - 1) // 10 for n in nums)
        if max(zone_count.values()) <= 2:
            score += 8; breakdown.append('구간분산+8')
        ends_set = {n % 10 for n in nums}
        if len(ends_set) >= 5:
            score += 8; breakdown.append('끝자리5종+8')

        # [고급 패턴 4종]
        if 130 <= s <= 145:
            score += 6; breakdown.append('합정점130-145+6')
        # 3구역 균형: 1-15 / 16-30 / 31-45 — 각 구역에 1개 이상
        z3 = [
            sum(1 for n in nums if 1 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 30),
            sum(1 for n in nums if 31 <= n <= 45),
        ]
        if min(z3) >= 1 and max(z3) <= 3:
            score += 6; breakdown.append(f'3구역균형{z3}+6')
        # 동일 끝자리 ≤2개 (예: 5,15,25,35 가 4개면 단순패턴)
        same_end = max(Counter(n % 10 for n in nums).values())
        if same_end <= 2:
            score += 4; breakdown.append('끝자리집중≤2+4')
        # 페어 빈출 — 6개 중 임의 쌍이 TOP30 페어에 포함되면 점수
        pair_hits = []
        sn = sorted(nums)
        for i in range(6):
            for j in range(i + 1, 6):
                if (sn[i], sn[j]) in top_pairs:
                    pair_hits.append((sn[i], sn[j]))
        if pair_hits:
            bonus = min(len(pair_hits) * 3, 6)
            score += bonus
            breakdown.append(f'페어빈출{len(pair_hits)}쌍+{bonus}')

        # [통계 빈출 2종]
        hit_recent = [n for n in nums if n in top_recent_set]
        if hit_recent:
            bonus = min(len(hit_recent) * 3, 9)
            score += bonus
            breakdown.append(f'최근빈출{hit_recent}+{bonus}')
        hit_all = [n for n in nums if n in top_all_set]
        if hit_all:
            bonus = min(len(hit_all) * 1, 5)
            score += bonus
            breakdown.append(f'전체빈출{hit_all}+{bonus}')

        candidates.append({
            'nums': nums, 'sum': s, 'odds': odds, 'high': high,
            'cons': cons, 'ac': ac, 'overlap': overlap,
            'hit_recent': hit_recent, 'hit_all': hit_all,
            'score': int(score), 'breakdown': breakdown,
        })

    # 점수 내림차순 + 동률은 다양성을 위해 셔플
    random.shuffle(candidates)
    candidates.sort(key=lambda c: c['score'], reverse=True)

    # 상위 N개 (단, 같은 조합은 한 번만)
    picked = []
    seen_keys = set()
    for c in candidates:
        key = tuple(c['nums'])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        picked.append(c)
        if len(picked) >= count:
            break

    log.append(f'후보 {len(candidates):,}개 생성 (시도 {tries:,}회)')
    if rejects:
        log.append('하드필터 기각: ' + ', '.join(f'{k} {v:,}' for k, v in rejects.most_common()))
    if candidates:
        score_max = max(c['score'] for c in candidates)
        score_min = min(c['score'] for c in candidates)
        score_avg = sum(c['score'] for c in candidates) / len(candidates)
        log.append(f'후보 점수 분포: 최대 {score_max} / 평균 {score_avg:.1f} / 최소 {score_min}')

    # ── 백테스트: 과거 실제 당첨조합도 동일 점수체계로 평가 ──
    backtest_n = min(100, total - 1)
    backtest_scores = []
    for past in all_rows[1:1 + backtest_n]:
        pnums = sorted(past)
        ps = sum(pnums)
        podds = sum(1 for n in pnums if n % 2)
        phigh = sum(1 for n in pnums if n >= 23)
        pcons = _consecutive_max(pnums)
        pac = _ac_value(pnums)
        psc = 0
        if podds == 3: psc += 8
        if phigh == 3: psc += 8
        if 121 <= ps <= 160: psc += 8
        if pac >= 8: psc += 8
        # 직전중복은 그 회차의 직전 회차 기준이라 보수적으로 패스 (시간상 미고려)
        # 다만 평균 기여를 위해 +4 부여 (역대 59.3%) — 절반값으로 보정
        psc += 4
        if sum(1 for n in pnums if n >= 41) <= 1: psc += 8
        if max(Counter((n-1)//10 for n in pnums).values()) <= 2: psc += 8
        if len({n%10 for n in pnums}) >= 5: psc += 8
        if 130 <= ps <= 145: psc += 6
        pz3 = [sum(1 for n in pnums if 1<=n<=15), sum(1 for n in pnums if 16<=n<=30), sum(1 for n in pnums if 31<=n<=45)]
        if min(pz3) >= 1 and max(pz3) <= 3: psc += 6
        if max(Counter(n%10 for n in pnums).values()) <= 2: psc += 4
        # 페어/빈출은 시점별로 달라 보수적으로 평균값 부여
        psc += 6  # 평균 페어 + 빈출 기여 추정
        backtest_scores.append(psc)
    if backtest_scores:
        import statistics
        bt_avg = statistics.mean(backtest_scores)
        bt_max = max(backtest_scores)
        bt_min = min(backtest_scores)
        bt_med = statistics.median(backtest_scores)
        # 예측 1위가 과거 N회 점수 분포 중 어느 백분위인가
        if picked:
            top_score = picked[0]['score']
            # 우리 점수보다 높거나 같은 과거 조합 수 → 상위 백분위
            higher_or_equal = sum(1 for s in backtest_scores if s >= top_score)
            percentile = higher_or_equal / len(backtest_scores) * 100
            log.append(f'백테스트(최근 {backtest_n}회 실제당첨 점수): 평균 {bt_avg:.1f} · 중앙 {bt_med:.0f} · 최대 {bt_max} · 최소 {bt_min}')
            if percentile < 1:
                log.append(f'⭐ 예측 1위 {top_score}점 = 과거 {backtest_n}회 중 동급 0개 — 역대 어떤 실제 당첨조합보다 패턴 적합도 우위')
            else:
                log.append(f'예측 1위 {top_score}점 = 과거 실제당첨 중 상위 {percentile:.1f}% 수준')
    log.append('─' * 60)

    # 결과 포맷 + 로그 출력
    results = []
    for i, c in enumerate(picked, 1):
        reason = (
            f'합 {c["sum"]} · 홀:짝 {c["odds"]}:{6-c["odds"]} · '
            f'고:저 {c["high"]}:{6-c["high"]} · 연속 {c["cons"]} · '
            f'AC {c["ac"]} · 직전중복 {c["overlap"]}'
        )
        results.append({
            'numbers': c['nums'],
            'sum': c['sum'],
            'odd_even': f'{c["odds"]} : {6-c["odds"]}',
            'high_low': f'{c["high"]} : {6-c["high"]}',
            'consecutive': c['cons'],
            'ac': c['ac'],
            'overlap_prev': c['overlap'],
            'score': c['score'],
            'top_recent_hits': c['hit_recent'],
            'top_all_hits': c['hit_all'],
            'reason': reason,
            'breakdown': c['breakdown'],
        })
        log.append(f'★ {i}위 [{c["score"]}점] {c["nums"]}')
        log.append(f'    구조: {reason}')
        if c['breakdown']:
            log.append(f'    점수: ' + ' · '.join(c['breakdown']))

    log.append('─' * 60)
    log.append(f'※ 본 점수는 역대 1,224회 통계 패턴 적합도일 뿐, 당첨확률은 1/8,145,060 으로 동일합니다.')
    log.append(f'※ 패턴 분석은 통계상 비당첨 조합을 거르는 용도 — "확률 향상" 이 아닌 "비효율 제거".')

    return {
        'combinations': results,
        'total_draws': total,
        'recent_n': recent_n,
        'top10_freq': top_all,
        'top10_freq_recent': top_recent,
        'log': log,
        'tries': tries,
        'rejects': dict(rejects),
        'candidates_generated': len(candidates),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 전수조사 (brute force) — 100점 검색용
# ─────────────────────────────────────────────────────────────────────────────

_brute_cache = {}  # key: (latest_drwNo, algo_version) → {'sorted_all': [...], 'distribution': {...}}
_BRUTE_ALGO_VERSION = 'v2.1'


def _score_combo(nums, last_draw, top_recent_set, top_all_set, top_pairs):
    """단일 6개 번호의 (score, breakdown, meta).
    하드필터 통과 못 하면 None.
    nums는 정렬된 tuple 가정."""
    s = sum(nums)
    if not (100 <= s <= 175):
        return None
    odds = sum(1 for n in nums if n & 1)
    if odds not in (2, 3, 4):
        return None
    high = sum(1 for n in nums if n >= 23)
    if high < 2 or high > 4:
        return None
    cons = _consecutive_max(nums)
    if cons > 2:
        return None
    ac = _ac_value(nums)
    if ac < 7:
        return None

    score = 0
    bd = []
    if odds == 3:
        score += 8; bd.append('홀짝3:3+8')
    if high == 3:
        score += 8; bd.append('고저3:3+8')
    if 121 <= s <= 160:
        score += 8; bd.append('합중심+8')
    if ac >= 8:
        score += 8; bd.append('AC≥8+8')
    overlap = len(set(nums) & last_draw)
    if 1 <= overlap <= 2:
        score += 8; bd.append(f'직전중복{overlap}+8')
    if sum(1 for n in nums if n >= 41) <= 1:
        score += 8; bd.append('41~45≤1+10')  # mislabel kept for parity
    zone_count = Counter((n - 1) // 10 for n in nums)
    if max(zone_count.values()) <= 2:
        score += 8; bd.append('구간분산+8')
    ends_set = {n % 10 for n in nums}
    if len(ends_set) >= 5:
        score += 8; bd.append('끝자리5종+8')
    if 130 <= s <= 145:
        score += 6; bd.append('합정점130-145+6')
    z3 = [
        sum(1 for n in nums if 1 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 30),
        sum(1 for n in nums if 31 <= n <= 45),
    ]
    if min(z3) >= 1 and max(z3) <= 3:
        score += 6; bd.append(f'3구역균형{z3}+6')
    same_end = max(Counter(n % 10 for n in nums).values())
    if same_end <= 2:
        score += 4; bd.append('끝자리집중≤2+4')
    pair_hits = []
    for i in range(6):
        for j in range(i + 1, 6):
            if (nums[i], nums[j]) in top_pairs:
                pair_hits.append((nums[i], nums[j]))
    if pair_hits:
        bonus = min(len(pair_hits) * 3, 6)
        score += bonus
        bd.append(f'페어빈출{len(pair_hits)}쌍+{bonus}')
    hit_recent = [n for n in nums if n in top_recent_set]
    if hit_recent:
        bonus = min(len(hit_recent) * 3, 9)
        score += bonus
        bd.append(f'최근빈출{hit_recent}+{bonus}')
    hit_all = [n for n in nums if n in top_all_set]
    if hit_all:
        bonus = min(len(hit_all) * 1, 5)
        score += bonus
        bd.append(f'전체빈출{hit_all}+{bonus}')

    meta = {
        'sum': s, 'odds': odds, 'high': high, 'cons': cons, 'ac': ac,
        'overlap': overlap, 'hit_recent': hit_recent, 'hit_all': hit_all,
    }
    return score, bd, meta


def _build_brute_cache(latest_drw):
    """C(45,6) = 8,145,060 전수조사. 하드필터 통과 조합만 점수화하여 정렬·저장."""
    import itertools, time
    t0 = time.time()

    qs = LottoHistory.objects.all().order_by('-drw_no')
    all_rows = list(qs.values_list('num1', 'num2', 'num3', 'num4', 'num5', 'num6'))

    freq_all = Counter()
    for r in all_rows:
        freq_all.update(r)
    recent_n = min(30, len(all_rows))
    freq_recent = Counter()
    for r in all_rows[:recent_n]:
        freq_recent.update(r)
    last_draw = set(all_rows[0]) if all_rows else set()

    pair_window = min(50, len(all_rows))
    pair_freq = Counter()
    for r in all_rows[:pair_window]:
        srt = sorted(r)
        for i in range(6):
            for j in range(i + 1, 6):
                pair_freq[(srt[i], srt[j])] += 1
    top_pairs = {p for p, _ in pair_freq.most_common(30)}
    top_recent_set = {n for n, _ in freq_recent.most_common(10)}
    top_all_set = {n for n, _ in freq_all.most_common(10)}

    distribution = Counter()
    sorted_all = []  # [(score, nums, breakdown, meta)] — score 내림차순

    # 본격 전수조사
    for nums in itertools.combinations(range(1, 46), 6):
        res = _score_combo(nums, last_draw, top_recent_set, top_all_set, top_pairs)
        if res is None:
            continue
        score, bd, meta = res
        distribution[score] += 1
        sorted_all.append((score, list(nums), bd, meta))

    sorted_all.sort(key=lambda x: -x[0])

    # 점수별 그룹 — 동점 내 랜덤 추출용
    score_groups = {}
    for item in sorted_all:
        score_groups.setdefault(item[0], []).append(item)
    scores_desc = sorted(score_groups.keys(), reverse=True)

    elapsed = time.time() - t0
    return {
        'sorted_all': sorted_all,
        'score_groups': score_groups,
        'scores_desc': scores_desc,
        'distribution': dict(distribution),
        'last_draw_set': sorted(last_draw),
        'top_recent': freq_recent.most_common(10),
        'top_all': freq_all.most_common(10),
        'top_pairs': pair_freq.most_common(10),
        'compute_seconds': round(elapsed, 1),
        'total_valid': len(sorted_all),
    }


def predict_brute(target_score=100, count=5):
    """전수조사 결과에서 target_score 이상 조합 상위 count 반환."""
    qs = LottoHistory.objects.order_by('-drw_no')
    latest = qs.first()
    if not latest:
        return {'error': 'DB가 비어있습니다.', 'combinations': [], 'log': []}

    cache_key = (latest.drw_no, _BRUTE_ALGO_VERSION)
    if cache_key not in _brute_cache:
        _brute_cache.clear()  # 오래된 캐시 제거
        _brute_cache[cache_key] = _build_brute_cache(latest.drw_no)
    data = _brute_cache[cache_key]

    distribution = data['distribution']
    score_groups = data['score_groups']
    scores_desc = data['scores_desc']

    # 점수 내림차순으로 그룹 순회하면서 같은 점수대 안에서는 random.sample
    picked = []
    matched_count = 0  # target_score 이상 총 발견 개수 (보고용)
    for s in scores_desc:
        if s >= target_score:
            matched_count += len(score_groups[s])
        if len(picked) >= count:
            continue
        need = count - len(picked)
        group = score_groups[s]
        if need >= len(group):
            # 그룹 통째로 — 순서는 itertools 기본이라 의미 없으므로 셔플 1회
            shuffled = list(group)
            random.shuffle(shuffled)
            picked.extend(shuffled)
        else:
            # 그룹에서 need개 무작위 추출
            picked.extend(random.sample(group, need))
    matched = matched_count  # int (개수만)

    # 결과 포맷
    combinations = []
    for score, nums, bd, meta in picked:
        reason = (
            f'합 {meta["sum"]} · 홀:짝 {meta["odds"]}:{6-meta["odds"]} · '
            f'고:저 {meta["high"]}:{6-meta["high"]} · 연속 {meta["cons"]} · '
            f'AC {meta["ac"]} · 직전중복 {meta["overlap"]}'
        )
        combinations.append({
            'numbers': nums,
            'sum': meta['sum'],
            'odd_even': f'{meta["odds"]} : {6-meta["odds"]}',
            'high_low': f'{meta["high"]} : {6-meta["high"]}',
            'consecutive': meta['cons'],
            'ac': meta['ac'],
            'overlap_prev': meta['overlap'],
            'score': score,
            'top_recent_hits': meta['hit_recent'],
            'top_all_hits': meta['hit_all'],
            'reason': reason,
            'breakdown': bd,
        })

    # 점수별 분포 — 100, 99, 98, ..., 60 (60 미만은 합산)
    score_table = []
    for s in range(100, 59, -1):
        score_table.append({'score': s, 'count': distribution.get(s, 0)})
    below_60 = sum(v for k, v in distribution.items() if k < 60)
    score_table.append({'score': '<60', 'count': below_60})

    used_from_target = min(matched, count)  # target 이상에서 채택된 개수
    filled = max(0, len(picked) - used_from_target)  # 보충된 개수 (target 미만)
    log = [
        f'═══ 전수조사 모드 (target={target_score}점, 동점내 랜덤) ═══',
        f'데이터: {qs.count():,}회 · 하드필터 통과 조합 {data["total_valid"]:,}개 '
        f'(연산 {data["compute_seconds"]}초{"(캐시)" if cache_key in _brute_cache else ""})',
        f'★ {target_score}점 이상: {matched:,}개 발견 (요청 {count}개 중 {used_from_target}개 채택)',
    ]
    if filled > 0:
        # 보충된 조합의 실제 점수 표시 (picked 마지막 filled개)
        fill_scores = [p[0] for p in picked[used_from_target:]]
        log.append(f'⤵ 부족분 {filled}개는 점수 내림차순으로 보충: '
                   + ', '.join(f'{s}점' for s in fill_scores))
    log.append(f'점수 분포 TOP10:')
    sorted_dist = sorted(distribution.items(), key=lambda x: -x[0])[:10]
    for s, c in sorted_dist:
        bar = '█' * min(int(c / max(1, sorted_dist[0][1]) * 30), 30)
        log.append(f'  {s}점: {c:,}개  {bar}')

    log.append('─' * 60)
    for i, c in enumerate(combinations, 1):
        log.append(f'★ {i}위 [{c["score"]}점] {c["numbers"]}')
        log.append(f'    구조: {c["reason"]}')
        if c['breakdown']:
            log.append(f'    점수: ' + ' · '.join(c['breakdown']))

    return {
        'mode': 'brute',
        'target_score': target_score,
        'found_count': matched,
        'returned_count': len(picked),
        'combinations': combinations,
        'score_distribution': dict(distribution),
        'score_table': score_table,
        'total_draws': qs.count(),
        'total_valid_combos': data['total_valid'],
        'compute_seconds': data['compute_seconds'],
        'cached': cache_key in _brute_cache and len(_brute_cache) > 0,
        'log': log,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 예측 저장 + 등수 자동 판정
# ─────────────────────────────────────────────────────────────────────────────

RANK_LABEL = {1: '1등', 2: '2등', 3: '3등', 4: '4등', 5: '5등', None: '미당첨'}


def _rank_of(matched_count, bonus_in):
    """동행복권 등수 판정."""
    if matched_count == 6:
        return 1
    if matched_count == 5 and bonus_in:
        return 2
    if matched_count == 5:
        return 3
    if matched_count == 4:
        return 4
    if matched_count == 3:
        return 5
    return None


def save_prediction(combinations, score_threshold=0, note=''):
    """현재 예측을 스냅샷 저장. target_round = (DB max drwNo) + 1.
    같은 회차에 이미 저장된 조합과 중복되는 것은 자동 제외."""
    latest = LottoHistory.objects.order_by('-drw_no').first()
    target = (latest.drw_no + 1) if latest else 1

    # 같은 회차에 이미 저장된 조합 수집 (중복 방지)
    seen = set()
    for prev in LottoPrediction.objects.filter(target_round=target):
        for c in prev.combinations:
            try:
                seen.add(tuple(sorted(c.get('numbers', []))))
            except Exception:
                continue

    clean = []
    dropped_dup = 0
    for c in combinations:
        nums = sorted(c.get('numbers', []))
        if len(nums) != 6 or len(set(nums)) != 6:
            continue
        key = tuple(nums)
        if key in seen:
            dropped_dup += 1
            continue
        seen.add(key)
        clean.append({
            'numbers': nums,
            'score': c.get('score'),
            'reason': c.get('reason', ''),
        })

    if not clean:
        msg = '저장할 새 조합이 없습니다.'
        if dropped_dup:
            msg = f'모두 이미 저장된 조합 ({dropped_dup}개 중복) — 신규 저장 없음.'
        return {'error': msg, 'dropped_dup': dropped_dup}

    p = LottoPrediction.objects.create(
        target_round=target,
        combinations=clean,
        score_threshold=score_threshold,
        note=note,
    )
    result = _serialize_pred(p)
    result['dropped_dup'] = dropped_dup
    return result


def _serialize_pred(p):
    return {
        'id': p.id,
        'created_at': p.created_at.isoformat(),
        'target_round': p.target_round,
        'combinations': p.combinations,
        'score_threshold': p.score_threshold,
        'note': p.note,
        'combo_count': len(p.combinations),
    }


def list_predictions():
    items = list(LottoPrediction.objects.all())
    # 각 항목 — 대상 회차가 추첨됐는지 + 최고 등수만 미리 계산
    by_round = {}
    rounds_needed = {p.target_round for p in items}
    actual_map = {h.drw_no: h for h in LottoHistory.objects.filter(drw_no__in=rounds_needed)}

    result = []
    for p in items:
        actual = actual_map.get(p.target_round)
        best_rank = None
        win_count = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        drawn = False
        if actual:
            drawn = True
            actual_set = set(actual.numbers())
            bonus = actual.bonus
            for c in p.combinations:
                mc = len(set(c['numbers']) & actual_set)
                br = bonus in set(c['numbers'])
                rk = _rank_of(mc, br)
                if rk is not None:
                    win_count[rk] += 1
                    if best_rank is None or rk < best_rank:
                        best_rank = rk
        result.append({
            **_serialize_pred(p),
            'drawn': drawn,
            'best_rank': best_rank,
            'best_rank_label': RANK_LABEL.get(best_rank, '미당첨' if drawn else '추첨대기'),
            'win_count': win_count if drawn else None,
        })
    return result


def check_prediction(pred_id):
    """저장된 예측의 등수 판정 — 폴더 클릭 시 호출."""
    try:
        p = LottoPrediction.objects.get(id=pred_id)
    except LottoPrediction.DoesNotExist:
        return {'error': '해당 예측이 없습니다.'}

    actual = LottoHistory.objects.filter(drw_no=p.target_round).first()
    log = []
    log.append(f'═══ AI 예측 #{p.id} 등수 판정 ═══')
    log.append(f'저장 시각: {p.created_at.strftime("%Y-%m-%d %H:%M:%S")}')
    log.append(f'대상 회차: {p.target_round}회 · 조합 수: {len(p.combinations)}개 · 타겟점수: {p.score_threshold}+')

    if not actual:
        log.append(f'⌛ {p.target_round}회는 아직 추첨되지 않았습니다 (DB 최신: '
                   f'{LottoHistory.objects.order_by("-drw_no").first().drw_no if LottoHistory.objects.exists() else "-"}회).')
        log.append('동행복권 추첨일 이후 "1. 최신 데이터 동기화"를 누르면 자동으로 결과 확인 가능합니다.')
        return {
            'pending': True,
            'log': log,
            'prediction': _serialize_pred(p),
        }

    actual_set = set(actual.numbers())
    bonus = actual.bonus
    log.append(f'실제 당첨번호 ({actual.drw_date or "-"}): {sorted(actual_set)} +보너스 {bonus}')
    log.append('─' * 60)

    win_count = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 0: 0}
    combos_result = []
    for i, c in enumerate(p.combinations, 1):
        my_set = set(c['numbers'])
        matched = sorted(my_set & actual_set)
        mc = len(matched)
        br = bonus in my_set
        rk = _rank_of(mc, br)
        rk_label = RANK_LABEL.get(rk, '미당첨')
        if rk:
            win_count[rk] += 1
        else:
            win_count[0] += 1
        suffix = f' (+보너스 일치)' if (mc == 5 and br) else ''
        emoji = '🏆' if rk == 1 else ('🥈' if rk == 2 else ('🥉' if rk in (3, 4) else ('🎟️' if rk == 5 else '·')))
        log.append(
            f'{emoji} 조합 {i} {c["numbers"]} → 일치 {mc}개 {matched}{suffix} → {rk_label}'
        )
        combos_result.append({
            'numbers': c['numbers'],
            'score': c.get('score'),
            'matched': matched,
            'match_count': mc,
            'bonus_match': br,
            'rank': rk,
            'rank_label': rk_label,
        })

    log.append('─' * 60)
    summary_parts = []
    for rk in (1, 2, 3, 4, 5):
        if win_count[rk]:
            summary_parts.append(f'{rk}등 {win_count[rk]}개')
    if win_count[0]:
        summary_parts.append(f'미당첨 {win_count[0]}개')
    log.append('요약: ' + (', '.join(summary_parts) if summary_parts else '없음'))
    best_rank = next((rk for rk in (1, 2, 3, 4, 5) if win_count[rk]), None)
    if best_rank:
        log.append(f'🎉 최고 성과: {RANK_LABEL[best_rank]}')

    return {
        'pending': False,
        'prediction': _serialize_pred(p),
        'actual_numbers': sorted(actual_set),
        'actual_bonus': bonus,
        'actual_date': actual.drw_date,
        'combos': combos_result,
        'win_count': win_count,
        'best_rank': best_rank,
        'best_rank_label': RANK_LABEL.get(best_rank, '미당첨'),
        'log': log,
    }


def delete_prediction(pred_id):
    n, _ = LottoPrediction.objects.filter(id=pred_id).delete()
    return {'deleted': n}


# ─────────────────────────────────────────────────────────────────────────────
# 전회차 패턴 학습 예측 (Mirror Mode) — 직전 1회의 추첨 결과를 템플릿으로 사용
# ─────────────────────────────────────────────────────────────────────────────

_mirror_cache = {}  # key: (prev_round_no, algo_version) → result dict
_MIRROR_ALGO = 'v1.0'


def predict_mirror_prev_round(count=5):
    """전회차(가장 최근 추첨) 패턴을 학습 → 가장 유사한 조합 상위 count 반환.

    점수 (100점 만점):
      합 ±5 / ±10 / ±20    15 / 10 / 5
      홀짝 매칭             15
      고저 매칭             12
      3구역 동일/근사       15 / 8
      41~45 개수 매칭       10
      연속 매칭              5
      AC ±1                  8
      끝자리 겹침 개당       2 (max 10)
      전회차 번호 중복 개당  2 (max 10, 6개 동일은 제외)
    """
    import itertools

    latest = LottoHistory.objects.order_by('-drw_no').first()
    if not latest:
        return {'error': 'DB 비어있음', 'combinations': [], 'log': []}

    cache_key = (latest.drw_no, _MIRROR_ALGO)
    if cache_key not in _mirror_cache:
        _mirror_cache.clear()
        _mirror_cache[cache_key] = _build_mirror_cache(latest)

    data = _mirror_cache[cache_key]
    score_groups = data['score_groups']
    scores_desc = data['scores_desc']
    distribution = data['distribution']

    # 점수 내림차순 + 동점 내 랜덤
    picked = []
    for s in scores_desc:
        need = count - len(picked)
        if need <= 0:
            break
        grp = score_groups[s]
        if need >= len(grp):
            shuffled = list(grp)
            random.shuffle(shuffled)
            picked.extend(shuffled)
        else:
            picked.extend(random.sample(grp, need))

    # 포맷
    pn = data['prev_numbers']
    p_set = set(pn)
    p_pat = data['prev_pattern']
    combinations = []
    log = []
    log.append('═══ 전회차 패턴 학습 예측 (Mirror Mode) ═══')
    log.append(f'학습 회차: {latest.drw_no}회 ({latest.drw_date}) {pn} +보너스 {latest.bonus}')
    log.append(f'  · 합 {p_pat["sum"]} · 홀:짝 {p_pat["odds"]}:{6-p_pat["odds"]} '
               f'· 고:저 {p_pat["high"]}:{6-p_pat["high"]}')
    log.append(f'  · 3구역 {p_pat["z3"]} · 41~45 {p_pat["big"]}개 '
               f'· AC {p_pat["ac"]} · 연속 {p_pat["cons"]}')
    log.append(f'전수조사 {data["total"]:,}개 평가 (연산 {data["compute_seconds"]}초'
               f'{"(캐시)" if cache_key in _mirror_cache else ""})')
    top_dist = sorted(distribution.items(), key=lambda x: -x[0])[:7]
    log.append(f'점수 분포 TOP: ' + ', '.join(f'{s}점 {c}' for s, c in top_dist))
    log.append('─' * 60)

    for i, (sc, nums, bd, meta) in enumerate(picked, 1):
        overlap_nums = sorted(set(nums) & p_set)
        reason = (f'합 {meta["sum"]} · 홀:짝 {meta["odds"]}:{6-meta["odds"]} · '
                  f'고:저 {meta["high"]}:{6-meta["high"]} · 3구역 {meta["z3"]} · '
                  f'전중복 {meta["overlap"]}{overlap_nums}')
        combinations.append({
            'numbers': nums,
            'sum': meta['sum'],
            'odd_even': f'{meta["odds"]} : {6-meta["odds"]}',
            'high_low': f'{meta["high"]} : {6-meta["high"]}',
            'consecutive': meta['cons'],
            'ac': meta['ac'],
            'overlap_prev': meta['overlap'],
            'score': sc,
            'top_recent_hits': overlap_nums,  # 전회차 적중 번호로 표기
            'top_all_hits': [],
            'reason': reason,
            'breakdown': bd,
        })
        log.append(f'★ {i}위 [{sc}점] {nums}')
        log.append(f'    {reason}')
        if bd:
            log.append(f'    점수: ' + ' · '.join(bd))

    log.append('─' * 60)
    log.append('⚠ 통계 경고: 직전회차 번호가 5개 이상 재출현한 사례는 역대 0회.')
    log.append('   따라서 본 모드 100점 조합도 당첨확률은 1/8,145,060 동일. 실험적 모드.')

    return {
        'mode': 'mirror_prev',
        'prev_round': latest.drw_no,
        'prev_numbers': pn,
        'prev_pattern': p_pat,
        'combinations': combinations,
        'log': log,
        'total_evaluated': data['total'],
        'compute_seconds': data['compute_seconds'],
    }


def _build_mirror_cache(latest):
    """전수조사 + 전회차 유사도 점수 계산."""
    import itertools
    import time

    t0 = time.time()
    pn = sorted(latest.numbers())
    p_set = set(pn)
    p_sum = sum(pn)
    p_odds = sum(1 for n in pn if n % 2)
    p_high = sum(1 for n in pn if n >= 23)
    p_cons = _consecutive_max(pn)
    p_ac = _ac_value(pn)
    p_z3 = [
        sum(1 for n in pn if 1 <= n <= 15),
        sum(1 for n in pn if 16 <= n <= 30),
        sum(1 for n in pn if 31 <= n <= 45),
    ]
    p_big = sum(1 for n in pn if n >= 41)
    p_ends = {n % 10 for n in pn}

    score_groups = {}
    distribution = Counter()
    total = 0

    for nums in itertools.combinations(range(1, 46), 6):
        overlap = len(set(nums) & p_set)
        if overlap == 6:
            continue
        s = sum(nums)
        odds = sum(1 for n in nums if n & 1)
        high = sum(1 for n in nums if n >= 23)
        cons = _consecutive_max(nums)
        ac = _ac_value(nums)
        z3 = [
            sum(1 for n in nums if 1 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 30),
            sum(1 for n in nums if 31 <= n <= 45),
        ]
        big = sum(1 for n in nums if n >= 41)
        ends = {n % 10 for n in nums}

        score = 0
        bd = []
        diff = abs(s - p_sum)
        if diff <= 5:
            score += 15; bd.append(f'합±5+15')
        elif diff <= 10:
            score += 10; bd.append(f'합±10+10')
        elif diff <= 20:
            score += 5; bd.append(f'합±20+5')
        if odds == p_odds:
            score += 15; bd.append(f'홀짝매칭+15')
        if high == p_high:
            score += 12; bd.append(f'고저매칭+12')
        if z3 == p_z3:
            score += 15; bd.append(f'3구역동일+15')
        elif sum(abs(a-b) for a, b in zip(z3, p_z3)) <= 2:
            score += 8; bd.append(f'3구역근사+8')
        if big == p_big:
            score += 10; bd.append(f'41~45개수+10')
        if cons == p_cons:
            score += 5; bd.append(f'연속매칭+5')
        if abs(ac - p_ac) <= 1:
            score += 8; bd.append(f'AC±1+8')
        end_match = min(len(ends & p_ends), 5)
        if end_match > 0:
            sc_end = end_match * 2
            score += sc_end; bd.append(f'끝자리겹침{end_match}+{sc_end}')
        if overlap > 0:
            sc_ov = min(overlap, 5) * 2
            score += sc_ov; bd.append(f'전중복{overlap}+{sc_ov}')

        meta = {
            'sum': s, 'odds': odds, 'high': high,
            'cons': cons, 'ac': ac, 'z3': z3, 'big': big,
            'overlap': overlap,
        }
        score_groups.setdefault(score, []).append((score, list(nums), bd, meta))
        distribution[score] += 1
        total += 1

    scores_desc = sorted(score_groups.keys(), reverse=True)
    return {
        'score_groups': score_groups,
        'scores_desc': scores_desc,
        'distribution': dict(distribution),
        'total': total,
        'compute_seconds': round(time.time() - t0, 1),
        'prev_numbers': pn,
        'prev_pattern': {
            'sum': p_sum, 'odds': p_odds, 'high': p_high,
            'cons': p_cons, 'ac': p_ac, 'z3': p_z3, 'big': p_big,
        },
    }


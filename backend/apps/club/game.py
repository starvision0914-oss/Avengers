import datetime
import random

from django.utils import timezone

from .models import BATTING_STATS, PITCHING_STATS

SCOUT_COST = 500
DAILY_ALLOWANCE = 300
TRAIN_BASE_COST = 100
REAL_PLAYER_CHANCE = 0.2

STAT_LABELS = {
    "contact": "컨택",
    "power": "파워",
    "speed": "주루",
    "fielding": "수비",
    "throwing": "송구",
    "control": "제구",
    "velocity": "구속",
    "stamina": "체력",
    "breaking": "변화구",
}

GRADE_WEIGHTS = {"common": 70, "rare": 22, "hero": 6, "legend": 2}

GRADE_STAT_RANGE = {
    "common": (20, 40),
    "rare": (35, 55),
    "hero": (50, 70),
    "legend": (65, 85),
}

GRADE_POTENTIAL_RANGE = {
    "common": (50, 65),
    "rare": (60, 75),
    "hero": (72, 85),
    "legend": (82, 99),
}

GRADE_SELL_MULTIPLIER = {"common": 1.0, "rare": 1.5, "hero": 2.2, "legend": 3.5}

SURNAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]
GIVEN_SYLLABLES = [
    "민", "준", "서", "지", "우", "현", "훈", "성", "재", "호",
    "도", "규", "석", "찬", "빈", "율", "산", "혁", "태", "강",
]


def generate_player_name():
    surname = random.choice(SURNAMES)
    given = random.choice(GIVEN_SYLLABLES) + random.choice(GIVEN_SYLLABLES)
    return surname + given


def roll_grade():
    grades = list(GRADE_WEIGHTS.keys())
    weights = list(GRADE_WEIGHTS.values())
    return random.choices(grades, weights=weights, k=1)[0]


def roll_new_player(position=None, grade=None):
    from .models import POSITION_CHOICES

    grade = grade or roll_grade()
    position = position or random.choice([p[0] for p in POSITION_CHOICES])
    lo, hi = GRADE_STAT_RANGE[grade]
    plo, phi = GRADE_POTENTIAL_RANGE[grade]
    potential = random.randint(plo, phi)

    stat_names = PITCHING_STATS if position == "P" else BATTING_STATS
    stats = {name: min(random.randint(lo, hi), potential) for name in stat_names}

    return {
        "name": generate_player_name(),
        "position": position,
        "grade": grade,
        "age": random.randint(18, 27),
        "potential": potential,
        "stats": stats,
    }


def train_cost(player, stat_name):
    current = getattr(player, stat_name)
    return int(TRAIN_BASE_COST + current * 15)


def train_success_chance(player, stat_name):
    current = getattr(player, stat_name)
    if current >= player.potential:
        return 0.0
    ratio = current / player.potential
    return max(0.15, 0.9 - ratio * 0.6)


def attempt_training(player, stat_name):
    """Returns (success: bool, delta: int)."""
    current = getattr(player, stat_name)
    if current >= player.potential:
        return False, 0
    chance = train_success_chance(player, stat_name)
    if random.random() > chance:
        return False, 0
    gain = random.randint(1, 3)
    new_value = min(current + gain, player.potential)
    delta = new_value - current
    setattr(player, stat_name, new_value)
    return True, delta


def sell_price(player):
    multiplier = GRADE_SELL_MULTIPLIER[player.grade]
    return int(player.overall * 20 * multiplier)


# FA 트레이드: 원작의 'FA 트레이드' 시스템을 단순화 — 영입풀(team=None)의 실제 선수를
# 우리팀 선수와 같은 포지션으로 맞바꿀 수 있다. 대상 선수가 더 강하면 차액만큼 캐시를
# 지불하고, 더 약하면 차액만큼 환급받는다.
TRADE_UPGRADE_MULTIPLIER = 300
TRADE_DOWNGRADE_MULTIPLIER = 150


def trade_cost(source, target):
    """양수면 지불할 비용, 음수면 환급받는 금액(절댓값)."""
    diff = target.overall - source.overall
    if diff >= 0:
        return diff * TRADE_UPGRADE_MULTIPLIER
    return diff * TRADE_DOWNGRADE_MULTIPLIER


def perform_trade(team, source, target):
    source.team = None
    source.save()
    target.team = team
    target.save()


# 레벨/경험치: 원작 야구9단처럼 선수 레벨은 최대 10. 경기 출전·훈련으로 경험치를 쌓아
# 레벨업하면 능력치가 잠재력 한도까지 소폭 상승한다. 레벨10 도달 후에는 '카드 승급'으로
# 등급을 한 단계 올리고 다시 1레벨부터 성장시킬 수 있다.
MAX_LEVEL = 10
LEVEL_UP_STAT_GAIN = (1, 3)
TRAIN_EXP_GAIN = 15
MATCH_EXP_GAIN = 10
HIT_EXP_BONUS = 5
HOME_RUN_EXP_BONUS = 10
PITCHER_WIN_EXP_BONUS = 15

GRADE_PROGRESSION = ["common", "rare", "hero", "legend"]
BREAKTHROUGH_COST = {"common": 3000, "rare": 8000, "hero": 20000}


def level_exp_threshold(level):
    return level * 100


def add_exp(player, amount):
    """경험치를 더하고 필요하면 레벨업까지 자동 처리. 레벨업 발생 횟수를 반환."""
    if player.level >= MAX_LEVEL:
        return 0

    player.exp += amount
    level_ups = 0
    while player.level < MAX_LEVEL and player.exp >= level_exp_threshold(player.level):
        player.exp -= level_exp_threshold(player.level)
        player.level += 1
        level_ups += 1
        for stat_name in player.stat_fields:
            current = getattr(player, stat_name)
            gain = random.randint(*LEVEL_UP_STAT_GAIN)
            setattr(player, stat_name, min(current + gain, player.potential))

    if player.level >= MAX_LEVEL:
        player.exp = 0
    return level_ups


def can_breakthrough(player):
    return player.level >= MAX_LEVEL and player.grade in BREAKTHROUGH_COST


def breakthrough_cost(player):
    return BREAKTHROUGH_COST.get(player.grade, 0)


def perform_breakthrough(player):
    """카드 승급: 등급을 한 단계 올리고 잠재력을 재설정, 레벨/경험치를 초기화한다."""
    if not can_breakthrough(player):
        return False

    next_grade = GRADE_PROGRESSION[GRADE_PROGRESSION.index(player.grade) + 1]
    lo, hi = GRADE_POTENTIAL_RANGE[next_grade]
    player.grade = next_grade
    player.potential = max(player.potential, random.randint(lo, hi))

    for stat_name in player.stat_fields:
        current = getattr(player, stat_name)
        setattr(player, stat_name, min(current + 3, player.potential))

    player.level = 1
    player.exp = 0
    player.save()
    return True


# 원작 야구9단의 7단계 리그 승강 구조(루키~슈퍼) + 최상위 MLB 티어 추가
LEAGUE_ORDER = ["rookie", "amateur", "semipro", "pro", "master", "world", "super", "mlb"]
LEAGUE_PROMOTION_POINTS = 100

# 원작 야구9단의 '레벨캡'을 재현: 선발 라인업 9명의 레벨(1~10, 실제 성장치) 합계가
# 리그별 상한을 넘으면 그 라인업으로는 경기에 나갈 수 없음. 9명×레벨10 만점 = 90이 이론상 최댓값이라
# 그 범위 안에서 리그가 오를수록 완화되도록 재산정 (원작 레벨캡 수치는 훨씬 큰 별도 스케일이라 그대로 못 씀)
LEVEL_CAP = {
    "rookie": 30, "amateur": 35, "semipro": 40, "pro": 45,
    "master": 55, "world": 65, "super": 75, "mlb": 90,
}

MATCH_COOLDOWN = datetime.timedelta(hours=1)

OPPONENT_RATING_RANGE = {
    "rookie": (15, 30),
    "amateur": (25, 40),
    "semipro": (35, 50),
    "pro": (45, 60),
    "master": (55, 72),
    "world": (65, 82),
    "super": (75, 95),
    "mlb": (88, 99),
}

MATCH_WIN_POINTS = (8, 15)
MATCH_LOSE_POINTS = (0, 4)
MATCH_WIN_CASH = {
    "rookie": (100, 250), "amateur": (200, 400), "semipro": (300, 550),
    "pro": (400, 800), "master": (700, 1300), "world": (1100, 2000), "super": (1800, 3200),
    "mlb": (3000, 5500),
}
MATCH_LOSE_CASH = {
    "rookie": (20, 60), "amateur": (40, 100), "semipro": (60, 150),
    "pro": (80, 200), "master": (150, 320), "world": (250, 480), "super": (400, 700),
    "mlb": (700, 1200),
}

CPU_TEAM_PREFIXES = ["번개", "황금", "폭풍", "강철", "질풍", "불꽃", "야생", "은하", "천둥", "바람"]
CPU_TEAM_SUFFIXES = ["유니콘즈", "매머드", "이글스", "타이탄즈", "레이더스", "드래곤즈", "판다스", "그리즐리스"]

# 시즌제: 100경기를 채우면 시즌 종료 → 상위 리그(MLB/슈퍼/월드)는
# 그 리그 8팀 중 정해진 순위 밖이면 강등 (원작 야구9단 포스트시즌 승강 규칙을 단순화)
SEASON_LENGTH = 100
SEASON_FIELD_SIZE = 8
RELEGATION_KEEP = {"mlb": 1, "super": 2, "world": 3}
SEASON_AWARD_CASH = 10000
SEASON_AWARD_CATEGORIES = [
    ("hits", "안타왕"),
    ("home_runs", "홈런왕"),
    ("rbi", "타점왕"),
    ("stolen_bases", "도루왕"),
]


def evaluate_season(team):
    """시즌 종료 시 상위리그(MLB/슈퍼/월드) 잔류 여부 판정. 강등되면 (True, rank)를 반환."""
    tier = team.league_tier
    if tier not in RELEGATION_KEEP:
        return False, None

    lo, hi = OPPONENT_RATING_RANGE[tier]
    rating = team_rating(team)
    field = [rating] + [random.randint(lo, hi) for _ in range(SEASON_FIELD_SIZE - 1)]
    field.sort(reverse=True)
    rank = field.index(rating) + 1

    keep_n = RELEGATION_KEEP[tier]
    if rank > keep_n:
        current_index = LEAGUE_ORDER.index(tier)
        team.league_tier = LEAGUE_ORDER[max(0, current_index - 1)]
        team.league_points = 0
        return True, rank
    return False, rank


def award_season_leaders(team):
    """시즌 종료 시 우리팀 안타/홈런/타점/도루 1위에게 캐시 선물. [(부문, 선수, 캐시)] 반환."""
    players = list(team.players.all())
    awards = []
    for field, label in SEASON_AWARD_CATEGORIES:
        candidates = [p for p in players if getattr(p, field) > 0]
        if not candidates:
            continue
        leader = max(candidates, key=lambda p: getattr(p, field))
        team.cash += SEASON_AWARD_CASH
        awards.append({"label": label, "player": leader, "value": getattr(leader, field), "cash": SEASON_AWARD_CASH})
    return awards


def process_season_end(team):
    """경기 후 시즌 경기수를 누적하고, 다 채웠으면 시즌을 마감한다. 시즌 종료 결과 dict 또는 None."""
    team.season_matches += 1
    if team.season_matches < SEASON_LENGTH:
        return None

    relegated, rank = evaluate_season(team)
    awards = award_season_leaders(team)
    team.season_matches = 0

    return {
        "relegated": relegated,
        "rank": rank,
        "awards": awards,
        "new_tier": team.get_league_tier_display(),
    }


def generate_cpu_team_name():
    return random.choice(CPU_TEAM_PREFIXES) + " " + random.choice(CPU_TEAM_SUFFIXES)


def pick_opponent_team():
    """실제 KBO 구단 중 하나를 골라 그 팀 소속 실제 선수(전 연도 버전 포함)로 라인업을 구성.
    9자리를 못 채울 만큼 인원이 부족하면 다른 실제 선수로 채워 공석이 없도록 한다."""
    from .models import Player

    real_teams = list(
        Player.objects.filter(is_real=True)
        .exclude(real_team="")
        .values_list("real_team", flat=True)
        .distinct()
    )
    if not real_teams:
        return None, []

    name = random.choice(real_teams)
    roster = list(Player.objects.filter(is_real=True, real_team=name))

    if len(roster) < 10:
        have_ids = {p.pk for p in roster}
        extra = list(
            Player.objects.filter(is_real=True)
            .exclude(pk__in=have_ids)
            .order_by("?")[: 10 - len(roster)]
        )
        roster += extra

    return name, roster


def roster_rating(players):
    if not players:
        return 0
    lineup = sorted(players, key=lambda p: p.overall, reverse=True)[:9]
    return round(sum(p.overall for p in lineup) / len(lineup))


# 투수진: 실제 KBO처럼 5선발 로테이션 + 중간계투 + 셋업(홀드) + 마무리(세이브) 구조
PITCHER_ROLE_ORDER = ["SP", "MID", "SETUP", "CL"]
ROLE_LABELS = {"SP": "선발", "MID": "중간계투", "SETUP": "셋업(홀드)", "CL": "마무리"}


def auto_pitching_staff(pitchers, sp_count=5, mid_count=2):
    """역할이 지정되지 않은 투수진을 능력치 순으로 자동 배치 (CPU 상대팀·미배정 투수용)."""
    ranked = sorted(pitchers, key=lambda p: p.overall, reverse=True)
    staff = {"SP": ranked[:sp_count], "MID": [], "SETUP": [], "CL": []}
    rest = ranked[sp_count:]
    staff["MID"] = rest[:mid_count]
    rest = rest[mid_count:]
    if rest:
        staff["SETUP"] = [rest[0]]
        rest = rest[1:]
    if rest:
        staff["CL"] = [rest[0]]
    return staff


def team_pitching_staff(players):
    """투수진 역할 구성: 선수가 직접 지정한 pitcher_role을 우선 쓰고, 미배정 투수는 자동 보충."""
    pitchers = [p for p in players if p.position == "P"]
    staff = {role: [] for role in PITCHER_ROLE_ORDER}
    unassigned = []
    for p in pitchers:
        if p.pitcher_role in staff:
            staff[p.pitcher_role].append(p)
        else:
            unassigned.append(p)

    for role in staff:
        # 사용자가 지정한 role_order(1이 1순위, 작을수록 우선)를 먼저 따르고,
        # 순서 미지정(0)인 선수는 뒤로 밀려 능력치 순으로 정렬됨
        staff[role].sort(key=lambda p: (p.role_order if p.role_order > 0 else 9999, -p.overall))

    if not staff["SP"] and unassigned:
        auto = auto_pitching_staff(unassigned)
        for role in PITCHER_ROLE_ORDER:
            if not staff[role]:
                staff[role] = auto[role]

    return staff


def staff_display(staff):
    """템플릿에서 쓰기 쉽도록 역할별 투수진을 [{code, label, players}] 목록으로 변환."""
    return [
        {"code": role, "label": ROLE_LABELS[role], "players": staff.get(role, [])}
        for role in PITCHER_ROLE_ORDER
    ]


def choose_starting_pitcher(team, staff):
    """5선발 로테이션: 팀 통산 경기수를 기준으로 순서대로 돌아가며 선발 등판."""
    sp_list = staff.get("SP") or []
    if not sp_list:
        return None
    idx = (team.wins + team.losses) % len(sp_list)
    return sp_list[idx]


def build_lineup(players, bench_limit=3):
    """포지션별로 같은 포지션 선수 중 OVR 최고를 선발로 배치. 그 포지션에 선수가 아예 없으면
    공석으로 두지 않고 아직 배치 안 된 다른 포지션 선수 중 OVR 최고로 채운다."""
    from .models import POSITION_CHOICES

    ranked = sorted(players, key=lambda p: p.overall, reverse=True)
    used_ids = set()
    starters = {}

    for code, _ in POSITION_CHOICES:
        candidates = [p for p in ranked if p.position == code and p.pk not in used_ids]
        if candidates:
            starters[code] = candidates[0]
            used_ids.add(candidates[0].pk)

    for code, _ in POSITION_CHOICES:
        if code not in starters:
            fillers = [p for p in ranked if p.pk not in used_ids]
            if fillers:
                starters[code] = fillers[0]
                used_ids.add(fillers[0].pk)

    lineup = []
    for code, label in POSITION_CHOICES:
        starter = starters.get(code)
        same_position = [p for p in players if p.position == code and p != starter]
        same_position.sort(key=lambda p: p.overall, reverse=True)
        lineup.append({
            "position": code,
            "label": label,
            "player": starter,
            "bench": same_position[:bench_limit],
        })
    return lineup


def resolve_lineup(team, bench_limit=3):
    """포지션별 라인업 계산: 유저가 지정한 선수가 있으면 그걸, 투수는 5선발 로테이션,
    나머지는 OVR 최고 선수를 자동 배치."""
    players = list(team.players.all())
    auto = build_lineup(players, bench_limit=bench_limit)
    staff = team_pitching_staff(players)
    rotation_starter = choose_starting_pitcher(team, staff)

    slots = {s.position: s.player for s in team.lineup_slots.select_related("player")}
    lineup = []
    for entry in auto:
        code = entry["position"]
        chosen = slots.get(code)
        if code == "P":
            # 투수는 수동 지정 대신 항상 5선발 로테이션을 따른다
            starter = rotation_starter or entry["player"]
        elif chosen and chosen.team_id == team.id and chosen.position == code:
            starter = chosen
        else:
            starter = entry["player"]

        same_position = sorted(
            (p for p in players if p.position == code),
            key=lambda p: p.overall, reverse=True,
        )
        bench = [p for p in same_position if p != starter][:bench_limit]
        lineup.append({"position": code, "label": entry["label"], "player": starter, "bench": bench})
    return lineup


def team_rating(team):
    lineup = resolve_lineup(team)
    players = [slot["player"] for slot in lineup if slot["player"]]
    return roster_rating(players)


def lineup_level_total(lineup):
    return sum(slot["player"].card_level for slot in lineup if slot["player"])


def match_cooldown_remaining(team):
    """다음 경기까지 남은 시간(timedelta). 바로 가능하면 timedelta(0)."""
    if not team.last_match_at:
        return datetime.timedelta(0)
    remaining = MATCH_COOLDOWN - (timezone.now() - team.last_match_at)
    return remaining if remaining.total_seconds() > 0 else datetime.timedelta(0)


def generate_boxscore(win):
    """9회 이닝 스코어보드 생성 (승패 결과와 어긋나지 않게 마지막회에서 보정)."""
    innings = 9
    home = [random.choices([0, 0, 0, 1, 1, 2, 3], k=1)[0] for _ in range(innings)]
    away = [random.choices([0, 0, 0, 1, 1, 2, 3], k=1)[0] for _ in range(innings)]

    home_total, away_total = sum(home), sum(away)
    if win and home_total <= away_total:
        home[-1] += (away_total - home_total) + random.randint(1, 2)
    elif not win and away_total <= home_total:
        away[-1] += (home_total - away_total) + random.randint(1, 2)

    return {
        "innings": list(range(1, innings + 1)),
        "home": home,
        "away": away,
        "home_total": sum(home),
        "away_total": sum(away),
    }


BATTING_EVENTS_BY_RUNS = {
    1: [("{name}의 적시타!", False), ("{name}의 솔로 홈런!", True), ("{name}의 희생플라이!", False)],
    2: [("{name}의 2루타로 2점 추가!", False), ("{name}의 투런 홈런!", True)],
    3: [("{name}의 3점 홈런!", True)],
}
SAVE_SITUATION_MARGIN = 3


def _pick_batter(lineup):
    batters = [slot["player"] for slot in lineup if slot["player"] and slot["position"] != "P"]
    if not batters:
        return None
    weights = [max(p.overall, 1) for p in batters]
    return random.choices(batters, weights=weights, k=1)[0]


def _pick_runner(lineup):
    """주루(speed) 스탯이 높을수록 도루를 더 자주 시도."""
    batters = [slot["player"] for slot in lineup if slot["player"] and slot["position"] != "P"]
    if not batters:
        return None
    weights = [max(p.speed, 1) for p in batters]
    return random.choices(batters, weights=weights, k=1)[0]


STEAL_ATTEMPT_CHANCE = 0.3


def _pitcher_label(p):
    """같은 이름의 다른 연도 카드(예: 곽빈 2019 vs 2026)를 구분하기 위해 연도를 붙인 표기."""
    if not p:
        return "-"
    return f"{p.name}({p.year})" if p.year else p.name


def _next_reliever(staff, role, used_ids, exclude_pk):
    candidates = [p for p in staff.get(role, []) if p.pk not in used_ids and p.pk != exclude_pk]
    if not candidates:
        return None
    return candidates[0]


def generate_play_events(home_lineup, home_staff, away_lineup, away_staff, boxscore, win):
    """이닝별 실황 텍스트 목록 (홈런/안타 타자, 투수 교체 등).
    투수 등판은 실제 야구처럼 선발(5~7회 소화) → 중간계투 → 셋업(8회) → 마무리(9회 세이브 상황) 순으로 진행."""
    home_pitcher = next((s["player"] for s in home_lineup if s["position"] == "P"), None)
    away_pitcher = next((s["player"] for s in away_lineup if s["position"] == "P"), None)
    home_used = {home_pitcher.pk} if home_pitcher else set()
    away_used = {away_pitcher.pk} if away_pitcher else set()

    home_exit_inning = random.randint(5, 7)
    away_exit_inning = random.randint(5, 7)
    home_setup_used = False
    away_setup_used = False
    running_home = 0
    running_away = 0

    events = []
    for idx, inn in enumerate(boxscore["innings"]):
        inning_events = []
        h, a = boxscore["home"][idx], boxscore["away"][idx]
        running_home += h
        running_away += a

        if h > 0:
            batter = _pick_batter(home_lineup)
            if batter:
                template, is_hr = random.choice(BATTING_EVENTS_BY_RUNS[min(h, 3)])
                kind = "homerun" if is_hr else "hit"
                inning_events.append({
                    "text": f"🔵 우리팀 — {template.format(name=batter.name)}",
                    "kind": kind, "side": "home", "player": batter.name,
                })
                batter.hits += 1
                batter.rbi += h
                if is_hr:
                    batter.home_runs += 1
                exp_gain = HIT_EXP_BONUS + (HOME_RUN_EXP_BONUS if is_hr else 0)
                level_ups = add_exp(batter, exp_gain)
                if level_ups:
                    inning_events.append({
                        "text": f"🆙 {batter.name} 레벨업! Lv{batter.level}", "kind": "levelup", "side": "home",
                    })
                batter.save()
        if a > 0:
            batter = _pick_batter(away_lineup)
            if batter:
                template, is_hr = random.choice(BATTING_EVENTS_BY_RUNS[min(a, 3)])
                kind = "homerun" if is_hr else "hit"
                inning_events.append({
                    "text": f"🔴 상대 — {template.format(name=batter.name)}",
                    "kind": kind, "side": "away", "player": batter.name,
                })

        if random.random() < STEAL_ATTEMPT_CHANCE:
            runner = _pick_runner(home_lineup)
            if runner:
                success_chance = 0.4 + runner.speed / 200
                if random.random() < success_chance:
                    runner.stolen_bases += 1
                    runner.save()
                    inning_events.append({
                        "text": f"🔵 우리팀 — {runner.name}의 도루 성공!",
                        "kind": "steal_success", "side": "home", "player": runner.name,
                    })
                else:
                    inning_events.append({
                        "text": f"🔵 우리팀 — {runner.name}의 도루 실패(아웃)",
                        "kind": "steal_fail", "side": "home", "player": runner.name,
                    })

        # 선발 → 중간계투 교체 (5~7회 중 랜덤하게 소화)
        if inn == home_exit_inning and home_pitcher:
            new_pitcher = _next_reliever(home_staff, "MID", home_used, home_pitcher.pk)
            if new_pitcher:
                inning_events.append({
                    "text": f"🔵 투수 교체: {_pitcher_label(home_pitcher)} → {_pitcher_label(new_pitcher)} (중간계투)",
                    "kind": "pitch_change", "side": "home", "player": new_pitcher.name,
                })
                home_used.add(new_pitcher.pk)
                add_exp(new_pitcher, MATCH_EXP_GAIN)
                new_pitcher.save()
                home_pitcher = new_pitcher

        if inn == away_exit_inning and away_pitcher:
            new_pitcher = _next_reliever(away_staff, "MID", away_used, away_pitcher.pk)
            if new_pitcher:
                inning_events.append({
                    "text": f"🔴 상대 투수 교체: {_pitcher_label(away_pitcher)} → {_pitcher_label(new_pitcher)} (중간계투)",
                    "kind": "pitch_change", "side": "away", "player": new_pitcher.name,
                })
                away_used.add(new_pitcher.pk)
                away_pitcher = new_pitcher

        # 8회: 셋업(홀드) 투입
        if inn == 8 and not home_setup_used:
            new_pitcher = _next_reliever(home_staff, "SETUP", home_used, home_pitcher.pk if home_pitcher else None)
            if new_pitcher:
                home_setup_used = True
                leading = running_home > running_away
                inning_events.append({
                    "text": f"🔵 투수 교체: {_pitcher_label(home_pitcher)} → {_pitcher_label(new_pitcher)} (셋업)",
                    "kind": "pitch_change", "side": "home", "player": new_pitcher.name,
                })
                home_used.add(new_pitcher.pk)
                if leading:
                    new_pitcher.holds += 1
                    inning_events.append({
                        "text": f"🔵 {new_pitcher.name} 홀드!", "kind": "note", "side": "home",
                    })
                add_exp(new_pitcher, MATCH_EXP_GAIN)
                new_pitcher.save()
                home_pitcher = new_pitcher

        if inn == 8 and not away_setup_used:
            new_pitcher = _next_reliever(away_staff, "SETUP", away_used, away_pitcher.pk if away_pitcher else None)
            if new_pitcher:
                away_setup_used = True
                inning_events.append({
                    "text": f"🔴 상대 투수 교체: {_pitcher_label(away_pitcher)} → {_pitcher_label(new_pitcher)} (셋업)",
                    "kind": "pitch_change", "side": "away", "player": new_pitcher.name,
                })
                away_used.add(new_pitcher.pk)
                away_pitcher = new_pitcher

        # 9회: 세이브 상황(1~3점차 리드)이면 마무리 투입
        if inn == 9:
            margin = running_home - running_away
            if win and 1 <= margin <= SAVE_SITUATION_MARGIN:
                closer = _next_reliever(home_staff, "CL", home_used, home_pitcher.pk if home_pitcher else None)
                if closer:
                    inning_events.append({
                        "text": f"🔵 투수 교체: {_pitcher_label(home_pitcher)} → {_pitcher_label(closer)} (마무리, 세이브 상황)",
                        "kind": "pitch_change", "side": "home", "player": closer.name,
                    })
                    home_used.add(closer.pk)
                    closer.saves += 1
                    inning_events.append({
                        "text": f"🔵 {closer.name} 세이브!", "kind": "note", "side": "home",
                    })
                    add_exp(closer, MATCH_EXP_GAIN + PITCHER_WIN_EXP_BONUS)
                    closer.save()
                    home_pitcher = closer

        events.append(inning_events)
    return events


def play_match(team):
    """경기 1회 실행: 결과에 따라 team의 캐시/승패/리그 포인트를 갱신하고 결과 dict를 반환."""
    your_rating = team_rating(team)

    opponent_name, opponent_roster = pick_opponent_team()
    lo, hi = OPPONENT_RATING_RANGE[team.league_tier]
    if opponent_roster:
        opp_rating = min(max(roster_rating(opponent_roster), lo), hi)
    else:
        opp_rating = random.randint(lo, hi)
        opponent_name = generate_cpu_team_name()

    your_lineup = resolve_lineup(team)
    opponent_lineup = build_lineup(opponent_roster)
    your_staff = team_pitching_staff(list(team.players.all()))
    opponent_staff = auto_pitching_staff([p for p in opponent_roster if p.position == "P"])

    diff = your_rating - opp_rating
    win_chance = max(0.1, min(0.9, 0.5 + diff / 100))
    win = random.random() < win_chance
    boxscore = generate_boxscore(win)
    boxscore["events"] = generate_play_events(
        your_lineup, your_staff, opponent_lineup, opponent_staff, boxscore, win
    )

    starting_pitcher = next((s["player"] for s in your_lineup if s["position"] == "P"), None)

    if win:
        points = random.randint(*MATCH_WIN_POINTS)
        cash = random.randint(*MATCH_WIN_CASH[team.league_tier])
        team.wins += 1
        if starting_pitcher:
            starting_pitcher.pitcher_wins += 1
    else:
        points = random.randint(*MATCH_LOSE_POINTS)
        cash = random.randint(*MATCH_LOSE_CASH[team.league_tier])
        team.losses += 1
        if starting_pitcher:
            starting_pitcher.pitcher_losses += 1

    # 출전 경험치: 선발 타자는 기본 경험치, 선발 투수는 승리 시 추가 경험치
    post_game_level_ups = []
    for slot in your_lineup:
        p = slot["player"]
        if not p or slot["position"] == "P":
            continue
        if add_exp(p, MATCH_EXP_GAIN):
            post_game_level_ups.append(p)
        p.save()

    if starting_pitcher:
        bonus = PITCHER_WIN_EXP_BONUS if win else 0
        if add_exp(starting_pitcher, MATCH_EXP_GAIN + bonus):
            post_game_level_ups.append(starting_pitcher)
        starting_pitcher.save()

    from .models import MatchLog

    MatchLog.objects.create(
        team=team,
        opponent_name=opponent_name,
        win=win,
        your_score=boxscore["home_total"],
        opp_score=boxscore["away_total"],
    )

    team.cash += cash
    team.league_points += points
    team.last_match_at = timezone.now()

    promoted = False
    current_index = LEAGUE_ORDER.index(team.league_tier)
    if team.league_points >= LEAGUE_PROMOTION_POINTS and current_index < len(LEAGUE_ORDER) - 1:
        team.league_tier = LEAGUE_ORDER[current_index + 1]
        team.league_points = 0
        promoted = True

    season_end = process_season_end(team)

    team.save()

    return {
        "win": win,
        "your_rating": your_rating,
        "opp_rating": opp_rating,
        "opponent_name": opponent_name,
        "points": points,
        "cash": cash,
        "promoted": promoted,
        "boxscore": boxscore,
        "your_lineup": your_lineup,
        "opponent_lineup": opponent_lineup,
        "season_end": season_end,
        "season_matches": team.season_matches,
        "post_game_level_ups": post_game_level_ups,
        "your_staff": staff_display(your_staff),
        "opponent_staff": staff_display(opponent_staff),
    }


def pick_real_player():
    from .models import Player

    return Player.objects.filter(is_real=True, team__isnull=True).order_by("?").first()


def real_player_pool_available():
    from .models import Player

    return Player.objects.filter(is_real=True, team__isnull=True).exists()


def scout_new_player(team):
    """영입 1회 실행: 실제 KBO 선수풀에서만 배정 (가상 선수는 더 이상 생성하지 않음)."""
    real_player = pick_real_player()
    if real_player:
        real_player.team = team
        real_player.save()
    return real_player

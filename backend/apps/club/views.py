from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_POST

from . import game
from .models import GRADE_CHOICES, LineupSlot, PITCHER_ROLE_CHOICES, POSITION_CHOICES, Player, Team

SORT_KEYS = {
    "name": lambda p: p.name,
    "year": lambda p: p.year or 0,
    "nickname": lambda p: p.nickname,
    "position": lambda p: p.position,
    "grade": lambda p: p.grade,
    "age": lambda p: p.age,
    "overall": lambda p: p.overall,
    "potential": lambda p: p.potential,
}


def get_team():
    team = Team.objects.first()
    if team is None:
        raise Http404("팀이 없습니다. 'python manage.py init_game'을 먼저 실행하세요.")
    return team


@xframe_options_exempt
def dashboard(request):
    team = get_team()
    players = list(team.players.all())
    players.sort(key=lambda p: p.overall, reverse=True)
    claimed_today = team.last_daily_claim == timezone.localdate()
    context = {
        "team": team,
        "roster_count": len(players),
        "best_players": players[:5],
        "claimed_today": claimed_today,
        "daily_allowance": game.DAILY_ALLOWANCE,
    }
    return render(request, "club/dashboard.html", context)


@xframe_options_exempt
@require_POST
def claim_daily(request):
    team = get_team()
    today = timezone.localdate()
    if team.last_daily_claim == today:
        messages.warning(request, "오늘은 이미 받았습니다.")
    else:
        team.cash += game.DAILY_ALLOWANCE
        team.last_daily_claim = today
        team.save()
        messages.success(request, f"일일 캐시 {game.DAILY_ALLOWANCE}원을 받았습니다.")
    return redirect("dashboard")


@xframe_options_exempt
def roster(request):
    team = get_team()
    grade_filter = request.GET.get("grade", "")
    position_filter = request.GET.get("position", "")
    year_filter = request.GET.get("year", "")
    query = request.GET.get("q", "").strip()
    min_ovr = request.GET.get("min_ovr", "").strip()
    sort = request.GET.get("sort", "overall")
    direction = request.GET.get("dir", "desc")

    players_qs = team.players.all()
    if grade_filter in dict(GRADE_CHOICES):
        players_qs = players_qs.filter(grade=grade_filter)
    if position_filter in dict(POSITION_CHOICES):
        players_qs = players_qs.filter(position=position_filter)
    if year_filter:
        players_qs = players_qs.filter(year=year_filter)
    if query:
        players_qs = players_qs.filter(Q(name__icontains=query) | Q(nickname__icontains=query))

    players = list(players_qs)

    if min_ovr:
        try:
            min_ovr_int = int(min_ovr)
            players = [p for p in players if p.overall >= min_ovr_int]
        except ValueError:
            pass

    sort_key = SORT_KEYS.get(sort, SORT_KEYS["overall"])
    players.sort(key=sort_key, reverse=(direction != "asc"))

    years = sorted({p.year for p in team.players.all() if p.year}, reverse=True)

    base_params = {}
    if grade_filter:
        base_params["grade"] = grade_filter
    if position_filter:
        base_params["position"] = position_filter
    if year_filter:
        base_params["year"] = year_filter
    if query:
        base_params["q"] = query
    if min_ovr:
        base_params["min_ovr"] = min_ovr

    sort_links = {}
    for field in SORT_KEYS:
        params = dict(base_params)
        params["sort"] = field
        params["dir"] = "asc" if (sort == field and direction == "desc") else "desc"
        sort_links[field] = "?" + urlencode(params)

    return render(request, "club/roster.html", {
        "team": team,
        "players": players,
        "grade_filter": grade_filter,
        "grade_choices": GRADE_CHOICES,
        "position_filter": position_filter,
        "position_choices": POSITION_CHOICES,
        "year_filter": year_filter,
        "years": years,
        "query": query,
        "min_ovr": min_ovr,
        "sort": sort,
        "dir": direction,
        "sort_links": sort_links,
    })


@xframe_options_exempt
@require_POST
def bulk_release_players(request):
    team = get_team()
    player_ids = request.POST.getlist("player_ids")
    players = Player.objects.filter(pk__in=player_ids, team=team)
    count = players.count()
    if count == 0:
        messages.warning(request, "선택된 선수가 없습니다.")
        return redirect("roster")

    total_price = sum(game.sell_price(p) for p in players)
    team.cash += total_price
    team.save()
    # 실제 KBO 선수는 유한한 자원이므로 완전 삭제 대신 자유계약 풀(team=None)로 되돌린다.
    # (가상 선수는 더 이상 생성되지 않으므로 이 방출 흐름에서 완전 삭제할 대상이 없다)
    players.update(team=None)
    messages.success(request, f"{count}명 방출 완료, {total_price:,}원을 받았습니다.")
    return redirect("roster")


@xframe_options_exempt
def player_detail(request, pk):
    team = get_team()
    player = get_object_or_404(Player, pk=pk, team=team)
    stat_rows = []
    for stat_name in player.stat_fields:
        stat_rows.append({
            "name": stat_name,
            "label": game.STAT_LABELS[stat_name],
            "value": getattr(player, stat_name),
            "cost": game.train_cost(player, stat_name),
            "chance": round(game.train_success_chance(player, stat_name) * 100),
            "maxed": getattr(player, stat_name) >= player.potential,
        })
    context = {
        "team": team,
        "player": player,
        "stat_rows": stat_rows,
        "sell_price": game.sell_price(player),
        "can_breakthrough": game.can_breakthrough(player),
        "breakthrough_cost": game.breakthrough_cost(player),
    }
    return render(request, "club/player_detail.html", context)


@xframe_options_exempt
@require_POST
def train_player(request, pk):
    team = get_team()
    player = get_object_or_404(Player, pk=pk, team=team)
    stat_name = request.POST.get("stat_name")
    if stat_name not in player.stat_fields:
        raise Http404("잘못된 스탯입니다.")

    cost = game.train_cost(player, stat_name)
    if team.cash < cost:
        messages.error(request, "캐시가 부족합니다.")
        return redirect("player_detail", pk=pk)

    team.cash -= cost
    team.save()
    success, delta = game.attempt_training(player, stat_name)
    level_ups = game.add_exp(player, game.TRAIN_EXP_GAIN)
    player.save()

    label = game.STAT_LABELS[stat_name]
    if success:
        messages.success(request, f"훈련 성공! {label} +{delta}")
    else:
        messages.warning(request, "훈련 실패... 캐시만 소모되었습니다.")
    if level_ups:
        messages.success(request, f"🆙 {player.name} 레벨업! Lv{player.level}")
    return redirect("player_detail", pk=pk)


@xframe_options_exempt
@require_POST
def breakthrough_player(request, pk):
    team = get_team()
    player = get_object_or_404(Player, pk=pk, team=team)

    if not game.can_breakthrough(player):
        messages.error(request, "카드 승급 조건을 만족하지 않습니다 (레벨10 + 전설 미만).")
        return redirect("player_detail", pk=pk)

    cost = game.breakthrough_cost(player)
    if team.cash < cost:
        messages.error(request, "캐시가 부족합니다.")
        return redirect("player_detail", pk=pk)

    team.cash -= cost
    team.save()
    old_grade = player.get_grade_display()
    game.perform_breakthrough(player)
    messages.success(request, f"🌟 카드 승급! {old_grade} → {player.get_grade_display()} (Lv1부터 재성장)")
    return redirect("player_detail", pk=pk)


@xframe_options_exempt
def trade_player(request, pk):
    team = get_team()
    source = get_object_or_404(Player, pk=pk, team=team)

    if request.method == "POST":
        target_id = request.POST.get("target_id")
        target = Player.objects.filter(
            pk=target_id, is_real=True, team__isnull=True, position=source.position
        ).first()
        if not target:
            messages.error(request, "대상 선수를 찾을 수 없습니다.")
            return redirect("trade_player", pk=pk)

        cost = game.trade_cost(source, target)
        if cost > 0 and team.cash < cost:
            messages.error(request, "캐시가 부족합니다.")
            return redirect("trade_player", pk=pk)

        team.cash -= cost
        team.save()
        source_name = source.name
        game.perform_trade(team, source, target)
        if cost > 0:
            messages.success(request, f"트레이드 완료! {source_name} → {target.name} (차액 {cost:,}원 지불)")
        else:
            messages.success(request, f"트레이드 완료! {source_name} → {target.name} (차액 {-cost:,}원 환급)")
        return redirect("player_detail", pk=target.pk)

    candidates = list(
        Player.objects.filter(is_real=True, team__isnull=True, position=source.position)
    )
    candidates.sort(key=lambda p: p.overall, reverse=True)
    for c in candidates:
        c.trade_cost_value = game.trade_cost(source, c)
        c.trade_cost_abs = abs(c.trade_cost_value)

    return render(request, "club/trade.html", {"team": team, "source": source, "candidates": candidates})


@xframe_options_exempt
@require_POST
def release_player(request, pk):
    team = get_team()
    player = get_object_or_404(Player, pk=pk, team=team)
    price = game.sell_price(player)
    team.cash += price
    team.save()
    name = player.name
    # 실제 KBO 선수는 유한한 자원이므로 완전 삭제 대신 자유계약 풀(team=None)로 되돌린다.
    player.team = None
    player.save()
    messages.success(request, f"{name} 선수를 방출하고 {price}원을 받았습니다.")
    return redirect("roster")


BATTING_POSITIONS = [c for c in POSITION_CHOICES if c[0] != "P"]


@xframe_options_exempt
def lineup(request):
    team = get_team()
    level_cap = game.LEVEL_CAP[team.league_tier]

    if request.method == "POST":
        auto = game.build_lineup(list(team.players.all()))
        auto_by_position = {s["position"]: s["player"] for s in auto}

        chosen = {}
        for code, _ in BATTING_POSITIONS:
            player_id = request.POST.get(f"slot_{code}")
            if player_id:
                chosen[code] = Player.objects.filter(pk=player_id, team=team, position=code).first()
            else:
                chosen[code] = auto_by_position.get(code)

        pitchers = list(team.players.filter(position="P"))
        valid_roles = dict(PITCHER_ROLE_CHOICES)
        for p in pitchers:
            role = request.POST.get(f"role_{p.pk}", "")
            p.pitcher_role = role if role in valid_roles else ""
            try:
                p.role_order = max(0, int(request.POST.get(f"order_{p.pk}", "0") or "0"))
            except ValueError:
                p.role_order = 0

        staff_preview = game.team_pitching_staff(pitchers)
        rotation_pick = game.choose_starting_pitcher(team, staff_preview)

        level_total = sum(p.card_level for p in chosen.values() if p) + (rotation_pick.card_level if rotation_pick else 0)
        if level_total > level_cap:
            messages.error(
                request,
                f"레벨캡 초과: 선발 레벨 합계 {level_total} > {team.get_league_tier_display()} 리그 상한 {level_cap}. "
                f"레벨 높은 선수를 빼고 저장해주세요.",
            )
            return redirect("lineup")

        for code, _ in BATTING_POSITIONS:
            player_id = request.POST.get(f"slot_{code}")
            slot, _ = LineupSlot.objects.get_or_create(team=team, position=code)
            slot.player = Player.objects.filter(pk=player_id, team=team, position=code).first() if player_id else None
            slot.save()

        Player.objects.bulk_update(pitchers, ["pitcher_role", "role_order"])

        messages.success(request, "라인업과 투수진을 저장했습니다.")
        return redirect("lineup")

    resolved = game.resolve_lineup(team)
    level_total = game.lineup_level_total(resolved)

    slots = []
    for slot_info in resolved:
        code = slot_info["position"]
        if code == "P":
            continue
        candidates = list(team.players.filter(position=code))
        candidates.sort(key=lambda p: p.overall, reverse=True)
        slots.append({
            "position": code,
            "label": slot_info["label"],
            "current": slot_info["player"],
            "candidates": candidates,
        })

    pitchers = list(team.players.filter(position="P"))
    pitchers.sort(key=lambda p: p.overall, reverse=True)
    staff = game.team_pitching_staff(list(team.players.all()))
    rotation_starter = game.choose_starting_pitcher(team, staff)

    return render(request, "club/lineup.html", {
        "team": team,
        "slots": slots,
        "pitchers": pitchers,
        "role_choices": PITCHER_ROLE_CHOICES,
        "staff": game.staff_display(staff),
        "rotation_starter": rotation_starter,
        "level_total": level_total,
        "level_cap": level_cap,
    })


@xframe_options_exempt
def records(request):
    team = get_team()
    tab = request.GET.get("tab", "team_rank")

    opponent_stats = list(
        team.match_logs.values("opponent_name")
        .annotate(
            match_wins=Count("id", filter=Q(win=True)),
            match_losses=Count("id", filter=Q(win=False)),
        )
        .order_by("-match_wins")
    )
    for row in opponent_stats:
        games = row["match_wins"] + row["match_losses"]
        row["win_rate"] = round(row["match_wins"] / games * 100, 1) if games else 0.0
        row["mine"] = False

    total_games = team.wins + team.losses
    win_rate = round(team.wins / total_games * 100, 1) if total_games else 0.0
    recent_logs = list(team.match_logs.order_by("-played_at")[:10])

    team_rank_rows = opponent_stats + [{
        "opponent_name": team.name,
        "match_wins": team.wins,
        "match_losses": team.losses,
        "win_rate": win_rate,
        "mine": True,
    }]
    team_rank_rows.sort(key=lambda r: r["win_rate"], reverse=True)
    my_rank = next((i + 1 for i, r in enumerate(team_rank_rows) if r["mine"]), None)

    # 타자/투수기록은 우리팀에 한정하지 않고 전체 리그(MLB/월드/마스터 등) 실제 선수 기록을 보여줌
    sort = request.GET.get("sort", "")
    direction = request.GET.get("dir", "desc")
    order_prefix = "" if direction == "asc" else "-"

    batter_fields = ["name", "position", "year", "hits", "home_runs", "rbi", "stolen_bases"]
    pitcher_fields = [
        "name", "pitcher_wins", "pitcher_losses", "era", "saves", "holds",
        "strikeouts", "hits_allowed", "home_runs_allowed", "walks", "hit_by_pitch",
    ]

    batter_sort = sort if sort in batter_fields else "home_runs"
    pitcher_sort = sort if sort in pitcher_fields else "pitcher_wins"

    batters = list(
        Player.objects.filter(is_real=True, hits__gt=0)
        .exclude(position="P")
        .order_by(f"{order_prefix}{batter_sort}")[:30]
    )
    pitchers = list(
        Player.objects.filter(is_real=True, position="P")
        .filter(Q(pitcher_wins__gt=0) | Q(pitcher_losses__gt=0))
        .order_by(f"{order_prefix}{pitcher_sort}")[:30]
    )

    def make_sort_links(fields):
        links = {}
        for field in fields:
            new_dir = "asc" if (sort == field and direction == "desc") else "desc"
            links[field] = f"?tab={tab}&sort={field}&dir={new_dir}"
        return links

    return render(request, "club/records.html", {
        "team": team,
        "tab": tab,
        "opponent_stats": opponent_stats,
        "team_rank_rows": team_rank_rows,
        "my_rank": my_rank,
        "win_rate": win_rate,
        "recent_logs": recent_logs,
        "batters": batters,
        "pitchers": pitchers,
        "sort": sort or (batter_sort if tab == "batter" else pitcher_sort),
        "dir": direction,
        "batter_sort_links": make_sort_links(batter_fields),
        "pitcher_sort_links": make_sort_links(pitcher_fields),
    })


@xframe_options_exempt
def scout(request):
    team = get_team()
    if request.method == "POST":
        if team.cash < game.SCOUT_COST:
            messages.error(request, "캐시가 부족합니다.")
            return redirect("scout")
        if not game.real_player_pool_available():
            messages.error(request, "더 이상 영입 가능한 실제 선수가 없습니다.")
            return redirect("scout")
        team.cash -= game.SCOUT_COST
        team.save()
        player = game.scout_new_player(team)
        return render(request, "club/scout.html", {
            "team": team,
            "cost": game.SCOUT_COST,
            "result": player,
        })
    return render(request, "club/scout.html", {"team": team, "cost": game.SCOUT_COST})


@xframe_options_exempt
def match(request):
    team = get_team()
    if request.method == "POST":
        if not team.players.exists():
            messages.error(request, "선수가 없습니다. 먼저 영입하세요.")
            return redirect("match")
        result = game.play_match(team)
        return render(request, "club/match.html", {
            "team": team, "result": result, "cooldown_seconds": 0,
        })
    return render(request, "club/match.html", {
        "team": team,
        "result": None,
        "cooldown_seconds": 0,
    })

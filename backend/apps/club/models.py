from django.db import models

GRADE_CHOICES = [
    ("common", "일반"),
    ("rare", "희귀"),
    ("hero", "영웅"),
    ("legend", "전설"),
]

POSITION_CHOICES = [
    ("P", "투수"),
    ("C", "포수"),
    ("1B", "1루수"),
    ("2B", "2루수"),
    ("3B", "3루수"),
    ("SS", "유격수"),
    ("LF", "좌익수"),
    ("CF", "중견수"),
    ("RF", "우익수"),
    ("DH", "지명타자"),
]

BATTING_STATS = ["contact", "power", "speed", "fielding", "throwing"]
PITCHING_STATS = ["control", "velocity", "stamina", "breaking"]

PITCHER_ROLE_CHOICES = [
    ("SP", "선발"),
    ("MID", "중간계투"),
    ("SETUP", "셋업(홀드)"),
    ("CL", "마무리"),
]

LEAGUE_TIER_CHOICES = [
    ("rookie", "루키"),
    ("amateur", "아마추어"),
    ("semipro", "세미프로"),
    ("pro", "프로"),
    ("master", "마스터"),
    ("world", "월드"),
    ("super", "슈퍼"),
    ("mlb", "MLB"),
]


class Team(models.Model):
    name = models.CharField(max_length=50)
    cash = models.PositiveIntegerField(default=5000)
    last_daily_claim = models.DateField(null=True, blank=True)
    league_tier = models.CharField(max_length=10, choices=LEAGUE_TIER_CHOICES, default="rookie")
    league_points = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    last_match_at = models.DateTimeField(null=True, blank=True)
    season_matches = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    team = models.ForeignKey(
        Team, related_name="players", on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=30)
    nickname = models.CharField(max_length=30, blank=True)
    real_team = models.CharField(max_length=20, blank=True)
    is_real = models.BooleanField(default=False)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    position = models.CharField(max_length=2, choices=POSITION_CHOICES)
    pitcher_role = models.CharField(max_length=5, choices=PITCHER_ROLE_CHOICES, blank=True)
    role_order = models.PositiveSmallIntegerField(default=0)
    grade = models.CharField(max_length=10, choices=GRADE_CHOICES, default="common")
    age = models.PositiveSmallIntegerField(default=20)
    level = models.PositiveIntegerField(default=1)
    exp = models.PositiveIntegerField(default=0)
    potential = models.PositiveSmallIntegerField(default=60)

    contact = models.PositiveSmallIntegerField(default=0)
    power = models.PositiveSmallIntegerField(default=0)
    speed = models.PositiveSmallIntegerField(default=0)
    fielding = models.PositiveSmallIntegerField(default=0)
    throwing = models.PositiveSmallIntegerField(default=0)

    control = models.PositiveSmallIntegerField(default=0)
    velocity = models.PositiveSmallIntegerField(default=0)
    stamina = models.PositiveSmallIntegerField(default=0)
    breaking = models.PositiveSmallIntegerField(default=0)

    # 경기 누적기록 (우리팀 선수 한정으로 집계)
    hits = models.PositiveIntegerField(default=0)
    home_runs = models.PositiveIntegerField(default=0)
    rbi = models.PositiveIntegerField(default=0)
    stolen_bases = models.PositiveIntegerField(default=0)
    pitcher_wins = models.PositiveIntegerField(default=0)
    pitcher_losses = models.PositiveIntegerField(default=0)
    era = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    saves = models.PositiveIntegerField(default=0)
    holds = models.PositiveIntegerField(default=0)
    strikeouts = models.PositiveIntegerField(default=0)
    hits_allowed = models.PositiveIntegerField(default=0)
    home_runs_allowed = models.PositiveIntegerField(default=0)
    walks = models.PositiveIntegerField(default=0)
    hit_by_pitch = models.PositiveIntegerField(default=0)

    awaken_count = models.PositiveIntegerField(default=0, help_text="전설급 재고 소진 시 각성으로 재지급된 횟수")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        label = f"{self.name}'{self.nickname}'" if self.nickname else self.name
        if self.year:
            label = f"[{self.year}] {label}"
        return f"{label}({self.get_position_display()})"

    @property
    def is_pitcher(self):
        return self.position == "P"

    @property
    def real_team_short(self):
        return self.real_team.split(" ")[0] if self.real_team else ""

    @property
    def stat_fields(self):
        return PITCHING_STATS if self.is_pitcher else BATTING_STATS

    @property
    def overall(self):
        fields = self.stat_fields
        return round(sum(getattr(self, f) for f in fields) / len(fields))

    @property
    def card_level(self):
        """실제 성장(경기 출전/훈련)으로 오르는 레벨. 원작처럼 1~10."""
        return self.level

    @property
    def exp_to_next_level(self):
        from .game import MAX_LEVEL, level_exp_threshold

        if self.level >= MAX_LEVEL:
            return None
        return level_exp_threshold(self.level)

    @property
    def card_label(self):
        """원작 표기 스타일: 연도 뒤 2자리 + 이름 (예: 13류현진)."""
        if self.year:
            return f"{str(self.year)[-2:]}{self.name}"
        return self.name


class LineupSlot(models.Model):
    """팀이 직접 지정한 포지션별 선발 선수 (없으면 경기 시 자동으로 OVR 최고 선수가 배치됨)."""

    team = models.ForeignKey(Team, related_name="lineup_slots", on_delete=models.CASCADE)
    position = models.CharField(max_length=2, choices=POSITION_CHOICES)
    player = models.ForeignKey(Player, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("team", "position")

    def __str__(self):
        return f"{self.team} {self.get_position_display()}: {self.player or '자동'}"


class MatchLog(models.Model):
    """경기 결과 기록 (팀순위/팀기록 집계용)."""

    team = models.ForeignKey(Team, related_name="match_logs", on_delete=models.CASCADE)
    opponent_name = models.CharField(max_length=30)
    win = models.BooleanField()
    your_score = models.PositiveSmallIntegerField(default=0)
    opp_score = models.PositiveSmallIntegerField(default=0)
    played_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        result = "승" if self.win else "패"
        return f"{self.played_at:%Y-%m-%d} vs {self.opponent_name} {result} ({self.your_score}:{self.opp_score})"


class ChampionshipLog(models.Model):
    """시즌 종료 포스트시즌(KBO식 승강제 브래킷) 우승 기록 - 팀 트로피 이력."""

    team = models.ForeignKey(Team, related_name="championships", on_delete=models.CASCADE)
    league_tier = models.CharField(max_length=10, choices=LEAGUE_TIER_CHOICES)
    achieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-achieved_at"]

    def __str__(self):
        return f"{self.achieved_at:%Y-%m-%d} {self.get_league_tier_display()} 우승"

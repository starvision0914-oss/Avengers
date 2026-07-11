import random

from django.core.management.base import BaseCommand

from apps.club.models import Player

# 등급별 시즌기록 근사 범위 (KBO 정규시즌 규모 감안)
BATTER_RANGES = {
    "common": {"hits": (20, 60), "hr": (0, 5), "sb": (0, 5)},
    "rare": {"hits": (60, 100), "hr": (5, 15), "sb": (3, 15)},
    "hero": {"hits": (100, 140), "hr": (15, 28), "sb": (10, 30)},
    "legend": {"hits": (140, 180), "hr": (25, 45), "sb": (20, 45)},
}
PITCHER_RANGES = {
    "common": {
        "wins": (0, 4), "losses": (5, 10), "era": (5.0, 7.5), "saves": (0, 2), "holds": (0, 3),
        "so": (30, 70), "hits_allowed": (100, 150), "hr_allowed": (10, 20), "bb": (30, 60), "hbp": (3, 10),
    },
    "rare": {
        "wins": (3, 8), "losses": (6, 12), "era": (4.0, 5.0), "saves": (0, 5), "holds": (0, 8),
        "so": (60, 100), "hits_allowed": (80, 120), "hr_allowed": (7, 15), "bb": (25, 50), "hbp": (3, 8),
    },
    "hero": {
        "wins": (8, 14), "losses": (6, 10), "era": (3.0, 4.0), "saves": (5, 20), "holds": (5, 15),
        "so": (100, 150), "hits_allowed": (60, 100), "hr_allowed": (5, 12), "bb": (20, 40), "hbp": (2, 6),
    },
    "legend": {
        "wins": (12, 18), "losses": (4, 8), "era": (1.5, 3.0), "saves": (20, 40), "holds": (10, 25),
        "so": (150, 220), "hits_allowed": (40, 80), "hr_allowed": (2, 8), "bb": (15, 30), "hbp": (1, 4),
    },
}


class Command(BaseCommand):
    help = "실제 선수 전체(MLB/월드/마스터 등 전체 리그)에 랜덤 시즌기록(안타/홈런/타점, 투수 승패)을 생성합니다."

    def handle(self, *args, **options):
        players = Player.objects.filter(is_real=True)
        batters = 0
        pitchers = 0
        for p in players:
            if p.position == "P":
                r = PITCHER_RANGES[p.grade]
                p.pitcher_wins = random.randint(*r["wins"])
                p.pitcher_losses = random.randint(*r["losses"])
                p.era = round(random.uniform(*r["era"]), 2)
                p.saves = random.randint(*r["saves"])
                p.holds = random.randint(*r["holds"])
                p.strikeouts = random.randint(*r["so"])
                p.hits_allowed = random.randint(*r["hits_allowed"])
                p.home_runs_allowed = random.randint(*r["hr_allowed"])
                p.walks = random.randint(*r["bb"])
                p.hit_by_pitch = random.randint(*r["hbp"])
                pitchers += 1
            else:
                r = BATTER_RANGES[p.grade]
                hits = random.randint(*r["hits"])
                hr = random.randint(*r["hr"])
                sb_base = random.randint(*r["sb"])
                p.hits = hits
                p.home_runs = hr
                p.rbi = hr * random.randint(2, 3) + int(hits * random.uniform(0.3, 0.5))
                p.stolen_bases = round(sb_base * (0.5 + p.speed / 200))
            p.save()

        self.stdout.write(self.style.SUCCESS(
            f"타자 {players.exclude(position='P').count()}명, 투수 {pitchers}명 시즌기록 생성 완료"
        ))

from django.core.management.base import BaseCommand

from apps.club import game
from apps.club.models import Team


class Command(BaseCommand):
    help = "쿨다운이 끝났다면 자동으로 경기 1회를 진행합니다 (cron에서 주기적으로 호출)."

    def handle(self, *args, **options):
        team = Team.objects.first()
        if team is None:
            self.stdout.write("팀이 없습니다.")
            return

        cooldown = game.match_cooldown_remaining(team)
        if cooldown.total_seconds() > 0:
            self.stdout.write(f"쿨다운 중 ({int(cooldown.total_seconds())}초 남음), 건너뜀")
            return

        if not team.players.exists():
            self.stdout.write("선수가 없어 경기를 진행할 수 없습니다.")
            return

        result = game.play_match(team)
        outcome = "승리" if result["win"] else "패배"
        box = result["boxscore"]
        promoted = " [승급!]" if result["promoted"] else ""
        self.stdout.write(
            f"{outcome} vs {result['opponent_name']} "
            f"({box['home_total']}:{box['away_total']}) "
            f"캐시+{result['cash']} 포인트+{result['points']}{promoted}"
        )

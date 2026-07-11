from django.core.management.base import BaseCommand

from apps.club.game import roll_new_player
from apps.club.models import Player, Team

STARTER_POSITIONS = ["P", "C", "CF"]


class Command(BaseCommand):
    help = "최초 1회 실행: 시작 팀과 스타터 선수 3명을 생성합니다."

    def handle(self, *args, **options):
        if Team.objects.exists():
            self.stdout.write(self.style.WARNING("이미 팀이 존재합니다. 아무 작업도 하지 않습니다."))
            return

        team = Team.objects.create(name="나의 구단", cash=5000)

        for position in STARTER_POSITIONS:
            data = roll_new_player(position=position, grade="common")
            player = Player.objects.create(
                team=team,
                name=data["name"],
                position=data["position"],
                grade=data["grade"],
                age=data["age"],
                potential=data["potential"],
                **data["stats"],
            )
            self.stdout.write(f"  - 스타터 영입: {player}")

        self.stdout.write(self.style.SUCCESS(f"'{team.name}' 생성 완료 (시작 캐시 {team.cash})"))

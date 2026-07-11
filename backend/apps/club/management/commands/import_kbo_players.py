import random

from django.core.management.base import BaseCommand

from apps.club.game import GRADE_POTENTIAL_RANGE, GRADE_STAT_RANGE
from apps.club.models import BATTING_STATS, PITCHING_STATS, Player

# (실명, 소속팀, 포지션코드, 등급(2026년 기준), 별명, 별명 보너스 스탯)
REAL_PLAYERS = [
    ("류현진", "한화 이글스", "P", "legend", "괴물", ["control", "velocity"]),
    ("문동주", "한화 이글스", "P", "hero", "파이어볼러", ["velocity"]),
    ("강백호", "한화 이글스", "1B", "hero", "천재타자", ["contact", "power"]),
    ("노시환", "한화 이글스", "3B", "legend", "홈런왕", ["power"]),
    ("김도영", "KIA 타이거즈", "3B", "legend", "더 영 킹", ["speed", "power"]),
    ("나성범", "KIA 타이거즈", "RF", "hero", "나스타", ["contact", "power"]),
    ("양현종", "KIA 타이거즈", "P", "legend", "대투수", ["control", "stamina"]),
    ("최형우", "KIA 타이거즈", "DH", "hero", "아버지", ["power", "contact"]),
    ("구자욱", "삼성 라이온즈", "LF", "hero", "구스타", ["contact", "power"]),
    ("원태인", "삼성 라이온즈", "P", "hero", "푸른피의 에이스", ["control"]),
    ("이재현", "삼성 라이온즈", "SS", "rare", "빼뱀", ["fielding", "speed"]),
    ("강민호", "삼성 라이온즈", "C", "hero", "삼민호", ["fielding", "throwing"]),
    ("오지환", "LG 트윈스", "SS", "hero", "오지배", ["contact", "fielding"]),
    ("김현수", "LG 트윈스", "DH", "legend", "타격기계", ["contact"]),
    ("박해민", "LG 트윈스", "CF", "hero", "도루왕", ["speed"]),
    ("양의지", "두산 베어스", "C", "legend", "양사장", ["contact", "fielding"]),
    ("곽빈", "두산 베어스", "P", "hero", "배명고 오타니", ["velocity", "breaking"]),
    ("정수빈", "두산 베어스", "CF", "rare", "잠실아이돌", ["speed", "fielding"]),
    ("박병호", "KT 위즈", "1B", "hero", "박뱅", ["power"]),
    ("고영표", "KT 위즈", "P", "rare", "잠수함", ["control", "stamina"]),
    ("배정대", "KT 위즈", "RF", "rare", "안심정대", ["fielding", "throwing"]),
    ("최정", "SSG 랜더스", "3B", "legend", "홈런공장장", ["power"]),
    ("한유섬", "SSG 랜더스", "LF", "rare", "동미니칸", ["power"]),
    ("문승원", "SSG 랜더스", "P", "rare", "문쇼", ["control"]),
    ("구창모", "NC 다이노스", "P", "hero", "엔구행", ["velocity", "control"]),
    ("박건우", "NC 다이노스", "RF", "rare", "사푼이", ["contact"]),
    ("손아섭", "NC 다이노스", "DH", "hero", "오빠", ["contact"]),
    ("안우진", "키움 히어로즈", "P", "legend", "장군님", ["velocity", "breaking"]),
    ("송성문", "키움 히어로즈", "3B", "rare", "송글벙글", ["contact", "power"]),
    ("임병욱", "키움 히어로즈", "RF", "rare", "거금이", ["speed", "power"]),
    ("전준우", "롯데 자이언츠", "LF", "hero", "안타제조기", ["contact"]),
    ("박세웅", "롯데 자이언츠", "P", "hero", "레인맨", ["control", "stamina"]),
    ("나승엽", "롯데 자이언츠", "1B", "rare", "치즈스틱", ["power"]),
    # 2차 보강 (2021~2026 활동 기준, 은퇴/MLB 이적 포함)
    ("채은성", "한화 이글스", "1B", "rare", "홈런레이스 왕", ["power"]),
    ("정우람", "한화 이글스", "P", "rare", "우람신", ["stamina"]),
    ("심우준", "한화 이글스", "SS", "rare", "거유준", ["power"]),
    ("이대호", "롯데 자이언츠", "DH", "legend", "조선의 4번타자", ["power"]),
    ("전민재", "롯데 자이언츠", "SS", "rare", "담넘천", ["power"]),
    ("윤동희", "롯데 자이언츠", "RF", "rare", "찐동희", ["contact"]),
    ("노진혁", "롯데 자이언츠", "3B", "rare", "노검사", ["fielding"]),
    ("김선빈", "KIA 타이거즈", "2B", "hero", "최단신", ["contact"]),
    ("박찬호", "KIA 타이거즈", "SS", "rare", "눕찬호", ["fielding"]),
    ("윤도현", "KIA 타이거즈", "2B", "rare", "YB", ["contact"]),
    ("오승환", "삼성 라이온즈", "P", "legend", "돌부처", ["control"]),
    ("김지찬", "삼성 라이온즈", "2B", "hero", "맥지찬", ["speed"]),
    ("백정현", "삼성 라이온즈", "P", "rare", "백쇼", ["breaking"]),
    ("홍창기", "LG 트윈스", "LF", "hero", "출루머신", ["contact"]),
    ("박동원", "LG 트윈스", "C", "rare", "참치", ["throwing"]),
    ("문보경", "LG 트윈스", "3B", "hero", "국보경", ["power"]),
    ("양석환", "두산 베어스", "1B", "rare", "석환신", ["power"]),
    ("김택연", "두산 베어스", "P", "hero", "아기곰", ["control"]),
    ("허경민", "두산 베어스", "3B", "rare", "안경민", ["contact"]),
    ("소형준", "KT 위즈", "P", "rare", "대형준", ["stamina"]),
    ("엄상백", "KT 위즈", "P", "rare", "엄식빵", ["control"]),
    ("오재일", "KT 위즈", "1B", "rare", "오마산", ["power"]),
    ("김광현", "SSG 랜더스", "P", "legend", "KK", ["breaking"]),
    ("김재환", "SSG 랜더스", "LF", "hero", "킹재환", ["power"]),
    ("조상우", "SSG 랜더스", "P", "hero", "조질라", ["velocity"]),
    ("박민우", "NC 다이노스", "2B", "hero", "득점권의 악마", ["contact"]),
    ("김주원", "NC 다이노스", "SS", "rare", "우주", ["power"]),
    ("최원준", "NC 다이노스", "CF", "rare", "에어조던", ["fielding"]),
    ("이정후", "키움 히어로즈", "CF", "legend", "바람의 손자", ["contact"]),
    ("김혜성", "키움 히어로즈", "2B", "legend", "혜성특급", ["speed"]),
    ("원종현", "키움 히어로즈", "P", "rare", "고무팔", ["stamina"]),
    ("서건창", "키움 히어로즈", "2B", "rare", "서센세", ["contact"]),
]

GRADE_ORDER = ["common", "rare", "hero", "legend"]

# 등급별 커리어 구간(연도) 근사치: [초기, 전성기, 현재]
# 정확한 개인별 데뷔/전성기 연도 조사 없이, 인지도(등급)에 비례한 근사 연표로 단순화
YEAR_SETS = {
    "legend": [2013, 2020, 2026],
    "hero": [2019, 2023, 2026],
    "rare": [2021, 2024, 2026],
}

# 2026년 기준 이미 은퇴했거나 KBO를 떠난(MLB 진출 등) 선수는 '현재' 슬롯을
# 실제 마지막 활동 연도로 대체 (실제 은퇴/이적 시점과 매칭)
FINAL_YEAR_OVERRIDES = {
    "오승환": 2025,   # 2025시즌 후 은퇴(은퇴식 2025-09-30)
    "이대호": 2022,   # 2022시즌 후 은퇴
    "오재일": 2025,   # 2025시즌 후 은퇴
    "이정후": 2023,   # 2024 MLB 자이언츠 진출, 마지막 KBO 시즌은 2023
    "김혜성": 2024,   # 2025 MLB 다저스 진출, 마지막 KBO 시즌은 2024
}


def shift_grade(grade, delta):
    idx = GRADE_ORDER.index(grade)
    idx = max(0, min(len(GRADE_ORDER) - 1, idx + delta))
    return GRADE_ORDER[idx]


def build_stats(position, grade, boost_stats):
    lo, hi = GRADE_STAT_RANGE[grade]
    plo, phi = GRADE_POTENTIAL_RANGE[grade]
    potential = random.randint(plo, phi)

    stat_names = PITCHING_STATS if position == "P" else BATTING_STATS
    stats = {name_: random.randint(lo, hi) for name_ in stat_names}
    for stat_name in boost_stats:
        if stat_name in stats:
            stats[stat_name] = min(stats[stat_name] + 2, 99)

    potential = max(potential, *stats.values())
    potential = min(potential, 99)
    return stats, potential


class Command(BaseCommand):
    help = (
        "실제 KBO 유명 선수를 연도별(초기/전성기/현재) 3개 버전으로 영입풀에 등록합니다. "
        "전성기·현재 버전에는 별명과 관련 스탯 +2 보너스가 붙고, 초기 버전은 무명 시절이라 별명이 없습니다."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="기존에 등록된 실제 선수를 모두 삭제 후 재등록 (주의: 이미 팀에 영입된 선수도 삭제됨)"
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Player.objects.filter(is_real=True).delete()
            self.stdout.write(f"기존 실제 선수 {deleted}명 삭제")
        else:
            # 연도 필드 도입 이전에 생성된 기존 선수는 '현재(2026)' 버전으로 간주
            backfilled = Player.objects.filter(is_real=True, year__isnull=True).update(year=2026)
            if backfilled:
                self.stdout.write(f"기존 선수 {backfilled}명을 2026년 버전으로 표시")

            # 은퇴/MLB 이적 등으로 2026년에 KBO 활동이 없는 선수는 실제 마지막 연도로 보정
            for name, final_year in FINAL_YEAR_OVERRIDES.items():
                fixed = Player.objects.filter(is_real=True, name=name, year=2026).exclude(
                    year=final_year
                ).update(year=final_year)
                if fixed:
                    self.stdout.write(f"{name}: 2026 → {final_year}년으로 보정")

        created = 0
        for name, real_team, position, grade, nickname, boost_stats in REAL_PLAYERS:
            early_year, prime_year, current_year = YEAR_SETS[grade]
            current_year = FINAL_YEAR_OVERRIDES.get(name, current_year)
            variants = [
                (early_year, shift_grade(grade, -1), "", []),
                (prime_year, shift_grade(grade, +1), nickname, boost_stats),
                (current_year, grade, nickname, boost_stats),
            ]
            for year, year_grade, year_nickname, year_boost in variants:
                if Player.objects.filter(is_real=True, name=name, year=year).exists():
                    continue

                stats, potential = build_stats(position, year_grade, year_boost)
                Player.objects.create(
                    team=None,
                    name=name,
                    nickname=year_nickname,
                    real_team=real_team,
                    is_real=True,
                    year=year,
                    position=position,
                    grade=year_grade,
                    age=random.randint(20, 38),
                    potential=potential,
                    **stats,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"실제 KBO 선수 (연도별 버전 포함) {created}명을 영입풀에 등록했습니다."))

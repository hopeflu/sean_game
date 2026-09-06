"""
선수 명단 생성기.

실존 선수의 이름·성적을 임의로 지어내지 않기 위해 **모든 선수는 가상 인물**이다.
또한 팀 간 밸런스를 완전히 맞추기 위해, 라인업 9명의 **능력치 세트는 모든 구단이
동일**하고 이름만 팀별로 다르게 배정된다(teams.py의 설계 주석 참조).
"""

import random

# ── 가상 선수 이름 재료 ───────────────────────────────────
_SURNAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
             "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍"]
_GIVEN = ["도현", "지훈", "서준", "민재", "예준", "우진", "시우", "준서",
          "하준", "지호", "건우", "현우", "성민", "태양", "재원", "동하",
          "찬영", "승우", "진우", "영호"]

# ── 타순별 고정 능력치 (모든 구단 공통) ───────────────────
# contact : 스윙 판정 관대함 (배트 히트박스 크기)  1~10
# power   : 타구 초속 → 비거리                     1~10
# eye     : 볼/스트라이크 구분 보정(연출용 표시)   1~10
# pos     : 수비 포지션 표기
_LINEUP_TEMPLATE = [
    {"order": 1, "pos": "중견수", "contact": 8, "power": 4, "eye": 8},
    {"order": 2, "pos": "2루수", "contact": 8, "power": 4, "eye": 7},
    {"order": 3, "pos": "우익수", "contact": 7, "power": 8, "eye": 7},
    {"order": 4, "pos": "1루수", "contact": 6, "power": 10, "eye": 6},
    {"order": 5, "pos": "지명타자", "contact": 6, "power": 9, "eye": 6},
    {"order": 6, "pos": "3루수", "contact": 6, "power": 7, "eye": 5},
    {"order": 7, "pos": "좌익수", "contact": 7, "power": 6, "eye": 6},
    {"order": 8, "pos": "포수", "contact": 5, "power": 5, "eye": 5},
    {"order": 9, "pos": "유격수", "contact": 6, "power": 3, "eye": 5},
]

# ── 선발 투수 능력치 (모든 구단 공통) ─────────────────────
# velocity : 직구 체감 속도 (공이 존까지 오는 프레임 수를 줄인다)
# control  : 제구 — 노린 코스에 얼마나 붙는가
# stamina  : 투구 수에 따른 구위 저하 속도 (1경기 모드에서 사용)
_ACE_TEMPLATE = {"pos": "투수", "velocity": 7, "control": 7, "stamina": 7}


def _make_names(team_code: str, count: int):
    """팀 코드를 시드로 사용해 매번 동일한 가상 이름 목록을 만든다."""
    rng = random.Random(f"kbo8bit::{team_code}")
    names, used = [], set()
    while len(names) < count:
        n = rng.choice(_SURNAMES) + rng.choice(_GIVEN)
        if n not in used:            # 한 팀 안에서 동명이인 방지
            used.add(n)
            names.append(n)
    return names


def build_lineup(team: dict):
    """해당 팀의 타순 9명을 반환한다. 능력치는 전 구단 공통."""
    names = _make_names(team["code"], len(_LINEUP_TEMPLATE) + 1)
    lineup = []
    for tpl, name in zip(_LINEUP_TEMPLATE, names):
        player = dict(tpl)           # 템플릿 복사 (원본 훼손 방지)
        player["name"] = name
        player["team"] = team["code"]
        lineup.append(player)
    return lineup


def build_pitcher(team: dict):
    """해당 팀의 선발 투수를 반환한다. 능력치는 전 구단 공통."""
    name = _make_names(team["code"], len(_LINEUP_TEMPLATE) + 1)[-1]
    pitcher = dict(_ACE_TEMPLATE)
    pitcher["name"] = name
    pitcher["team"] = team["code"]
    return pitcher

"""
수비 시프트.

수비 측 플레이어가 투구 전에 고르는 유일한 '수비 결정'이다. 야수를 직접
움직이는 대신, 시프트가 **타구 방향·발사각별 안타 확률에 계수로** 붙는다.
`batted_ball._classify` 가 이미 구간별 안타 확률로 수비를 근사하고 있으므로
같은 층에 얹는 것이 자연스럽다.

부호 규약은 batted_ball 과 같다 — **spray 음수 = 좌측(3루쪽), 양수 = 우측(1루쪽)**.

트레이드오프 설계
-----------------
어떤 시프트든 **막는 쪽이 있으면 비는 쪽이 있다.** 상대 타자의 타구 성향을
읽지 못하면 시프트는 오히려 손해가 되도록 계수를 대칭으로 잡았다.
"""

SHIFTS = [
    {"key": "STD",  "name": "표준 수비",
     "desc": "치우침 없는 기본 위치"},
    {"key": "PULL", "name": "당겨치기 시프트",
     "desc": "좌측(3루쪽)을 두껍게 — 우측이 빈다"},
    {"key": "OPPO", "name": "밀어치기 시프트",
     "desc": "우측(1루쪽)을 두껍게 — 좌측이 빈다"},
    {"key": "IN",   "name": "전진 수비",
     "desc": "내야 전진 — 땅볼은 막고 뜬공에 약하다"},
]
BY_KEY = {s["key"]: s for s in SHIFTS}

# 한쪽으로 치우쳤다고 볼 각도 경계
SIDE_DEG = 12.0


def hit_prob_modifier(shift_key: str, launch: float, spray: float) -> float:
    """
    안타 확률에 곱할 계수. 1.0이면 영향 없음.

    launch : 발사각(도)   — 땅볼/뜬공 구분에 쓴다
    spray  : 타구 방향(도) — 음수 좌측, 양수 우측
    """
    if shift_key == "PULL":
        if spray < -SIDE_DEG:
            return 0.62                     # 시프트 건 쪽으로 굴러왔다
        if spray > SIDE_DEG:
            return 1.38                     # 반대쪽이 텅 비었다
        return 1.0

    if shift_key == "OPPO":
        if spray > SIDE_DEG:
            return 0.62
        if spray < -SIDE_DEG:
            return 1.38
        return 1.0

    if shift_key == "IN":
        if launch < 5.0:
            return 0.55                     # 내야 전진 — 땅볼 봉쇄
        if launch >= 18.0:
            return 1.45                     # 외야 앞이 비어 텍사스성 타구가 산다
        return 1.05                         # 라인드라이브는 조금 유리해진다

    return 1.0


def blocks_homerun(shift_key: str) -> bool:
    """시프트로 홈런을 막을 수는 없다 — 계수 적용 대상에서 제외하기 위한 표시."""
    return False

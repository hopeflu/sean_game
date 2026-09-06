"""
투구 모델.

좌표계
------
포수 뒤 시점이므로 공은 화면 위쪽(마운드)에서 아래쪽(홈플레이트)으로 다가온다.
진행도 t 를 0(릴리스) → 1(홈플레이트 도달)로 두고,

    화면좌표 = 릴리스점 → 목표점 선형보간 + 무브먼트(늦게 휘는 가중치)
    반지름   = 원근감 표현 (t 에 따라 커짐)

무브먼트에 t**3 가중치를 쓰는 이유: 실제 변화구처럼 **홈플레이트 근처에서
급격히 휘어 보이게** 하기 위함이다(선형이면 처음부터 휘어 보여 밋밋하다).
"""

import math
import random

from .. import config as C


# ── 구종 정의 ─────────────────────────────────────────────
# frames  : 릴리스 → 홈플레이트 도달까지의 프레임 수 (작을수록 빠름)
# bx, by  : 최종 무브먼트(픽셀). +x=오른쪽, +y=아래(가라앉음)
# spin    : 공 실밥 회전 연출 속도
# color   : 궤적 잔상 색 (구종 식별용 — 고전 게임의 색 힌트 연출)
PITCH_TYPES = [
    {"key": "FB", "name": "직구",     "frames": 46, "bx": 0,   "by": -3,
     "spin": 0.55, "color": C.WHITE},
    {"key": "SL", "name": "슬라이더", "frames": 52, "bx": -13, "by": 4,
     "spin": 0.40, "color": C.CYAN},
    {"key": "CB", "name": "커브",     "frames": 62, "bx": 6,   "by": 15,
     "spin": 0.28, "color": C.MAGENTA},
    {"key": "CH", "name": "체인지업", "frames": 60, "bx": 7,   "by": 8,
     "spin": 0.22, "color": C.GREEN},
    {"key": "FK", "name": "포크",     "frames": 54, "bx": 1,   "by": 17,
     "spin": 0.18, "color": C.YELLOW},
]
BY_KEY = {p["key"]: p for p in PITCH_TYPES}


def cell_center(col: int, row: int):
    """스트라이크존 3x3 격자의 (열, 행) 중심 화면좌표를 돌려준다."""
    cx = C.ZONE_X + col * C.CELL_W + C.CELL_W // 2
    cy = C.ZONE_Y + row * C.CELL_H + C.CELL_H // 2
    return cx, cy


class Pitch:
    """날아오는 공 하나의 상태."""

    def __init__(self, ptype: dict, target_xy, velocity: int = 7):
        self.type = ptype
        self.tx, self.ty = target_xy          # 무브먼트 적용 전 조준점

        # 투수 구속이 좋을수록 도달 프레임이 짧아진다 (velocity 7 을 기준값으로)
        speed_mod = 1.0 - (velocity - 7) * 0.035
        self.flight = max(24, int(ptype["frames"] * speed_mod))

        self.elapsed = 0.0
        self.done = False                     # 포수 미트 통과 여부
        self.trail = []                       # 잔상용 최근 좌표 목록

        # 실제 홈플레이트 통과 지점(무브먼트 포함) — 판정에 쓰인다
        self.plate_x = self.tx + ptype["bx"]
        self.plate_y = self.ty + ptype["by"]

    # ── 진행 ──────────────────────────────────────────────
    @property
    def t(self) -> float:
        """0=릴리스, 1=홈플레이트. 1을 넘으면 포수 쪽으로 지나가는 중."""
        return self.elapsed / self.flight

    def update(self, dt_frames: float = 1.0):
        self.elapsed += dt_frames
        self.trail.append(self.position())
        if len(self.trail) > 6:
            self.trail.pop(0)
        if self.t > 1.25:
            self.done = True

    # ── 렌더용 정보 ───────────────────────────────────────
    def position(self, t: float = None):
        """현재(또는 지정 t)의 화면 좌표."""
        if t is None:
            t = self.t
        t = min(t, 1.3)
        # 직선 성분: 릴리스점 → 조준점
        x = C.RELEASE_X + (self.tx - C.RELEASE_X) * t
        y = C.RELEASE_Y + (self.ty - C.RELEASE_Y) * t
        # 무브먼트: 늦게 휘도록 t^3 가중
        w = t ** 3
        x += self.type["bx"] * w
        y += self.type["by"] * w
        return x, y

    def radius(self, t: float = None) -> float:
        """원근감 — 멀리 있을 때 1px, 홈플레이트에서 5px 남짓."""
        if t is None:
            t = self.t
        return 1.2 + 4.2 * min(t, 1.2) ** 1.6

    def in_strike_zone(self) -> bool:
        """홈플레이트 통과 지점이 스트라이크존 안인가."""
        return (C.ZONE_X <= self.plate_x <= C.ZONE_X + C.ZONE_W and
                C.ZONE_Y <= self.plate_y <= C.ZONE_Y + C.ZONE_H)


class PitcherAI:
    """
    CPU 투수. 볼카운트에 따라 구종·코스를 고른다.

    고전 게임답게 복잡한 확률 모델 대신 **읽히는 패턴**을 쓴다.
      - 유리한 카운트(2S)  → 존 바깥 유인구 비중↑
      - 불리한 카운트(3B)  → 한복판 직구 비중↑
    """

    def __init__(self, pitcher: dict, seed=None):
        self.p = pitcher
        self.rng = random.Random(seed)

    def choose(self, balls: int, strikes: int) -> Pitch:
        rng = self.rng

        # ── 1) 구종 선택 ──────────────────────────────────
        if balls >= 3 and strikes <= 1:
            # 볼넷 위기 → 스트라이크를 잡으러 직구 위주
            weights = {"FB": 6, "SL": 2, "CB": 1, "CH": 1, "FK": 0}
        elif strikes >= 2:
            # 삼진 노림 → 떨어지는 공 위주
            weights = {"FB": 2, "SL": 3, "CB": 2, "CH": 2, "FK": 3}
        else:
            weights = {"FB": 4, "SL": 3, "CB": 2, "CH": 2, "FK": 2}

        keys = [k for k, w in weights.items() for _ in range(w)]
        ptype = BY_KEY[rng.choice(keys)]

        # ── 2) 코스 선택 ──────────────────────────────────
        # 유인구를 던질지 결정 (2스트라이크에서 확률↑, 볼넷 위기엔 자제)
        if balls >= 3:
            chase_p = 0.10
        elif strikes >= 2:
            chase_p = 0.62
        else:
            chase_p = 0.35
        chase = rng.random() < chase_p

        col = rng.randrange(C.ZONE_COLS)
        row = rng.randrange(C.ZONE_ROWS)
        tx, ty = cell_center(col, row)

        if chase:
            # 존 "가장자리 바깥"을 직접 겨냥한다.
            # 셀 중심에서 오프셋만 더하면 가운데 셀에서 시작할 때 여전히
            # 존 안에 남아 볼이 거의 나오지 않는다.
            side = rng.choice(("L", "R", "U", "D", "D"))   # 낮은 공을 더 자주
            out = rng.randint(5, 16)
            if side == "L":
                tx = C.ZONE_X - out
            elif side == "R":
                tx = C.ZONE_X + C.ZONE_W + out
            elif side == "U":
                ty = C.ZONE_Y - out
            else:
                ty = C.ZONE_Y + C.ZONE_H + out

        # ── 3) 제구 오차 ──────────────────────────────────
        # control 이 높을수록 조준점에서 덜 벗어난다
        spread = max(1.0, (11 - self.p["control"]) * 1.4)
        tx += rng.gauss(0, spread)
        ty += rng.gauss(0, spread * 0.8)

        # 무브먼트를 감안해 조준점을 되돌려 놓는다
        # (투수는 "휜 뒤에 존에 들어오도록" 던지므로)
        tx -= ptype["bx"] * 0.6
        ty -= ptype["by"] * 0.6

        return Pitch(ptype, (tx, ty), velocity=self.p["velocity"])

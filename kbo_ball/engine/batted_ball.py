"""
타구 물리 및 결과 판정.

컨택 정보(품질/타이밍/배트-공 상하 오차)를 세 가지 물리량으로 바꾼 뒤
그 조합으로 결과를 분류한다.

  타구속도(exit)   ← 컨택 품질 x 타자 파워
  발사각(launch)   ← 배트가 공 위를 때렸나 아래를 때렸나 (dy)
  타구방향(spray)  ← 타이밍이 빨랐나 늦었나 (당겨치기 / 밀어치기)

이 세 값만으로 땅볼·뜬공·안타·홈런이 자연스럽게 갈리므로, 결과를 난수로
직접 뽑지 않는다(고전 야구게임의 "친 대로 나간다"는 감각을 위해).
"""

import math
import random

# ── 구장 규격 (미터) ──────────────────────────────────────
# 국내 구장에서 흔한 치수를 기준으로 삼은 게임용 상수.
FENCE_LINE   = 99.0     # 좌우 폴대 쪽
FENCE_CENTER = 122.0    # 중앙 펜스

# ── 타구 물리 계수 ────────────────────────────────────────
LAUNCH_BASE   = 10.0    # dy=0(정타)일 때의 발사각 — 라인드라이브
LAUNCH_PER_PX = 2.5     # 상하 조준 오차 1px당 발사각 변화량
DIST_K        = 152.0   # 최적 조건(타구속도 1.0, 28도)에서의 비거리(m)
OPT_LAUNCH    = 28.0    # 비거리가 최대가 되는 발사각
LAUNCH_SPREAD = 22.0    # 최적각에서 벗어날 때 비거리가 줄어드는 폭


def _carry(launch_deg: float) -> float:
    """
    발사각 → 비거리 계수(0~1).

    진공 포물선의 sin(2θ)를 쓰면 45도에서 최대가 되어 야구와 맞지 않는다.
    공기저항·백스핀이 있는 실제 타구는 28도 부근에서 가장 멀리 나가므로,
    그 지점을 정점으로 하는 종 모양 곡선을 쓴다.
    """
    if launch_deg <= 0:
        return 0.0
    return math.exp(-((launch_deg - OPT_LAUNCH) / LAUNCH_SPREAD) ** 2)


class BattedBall:
    def __init__(self, exit_v, launch, spray, distance, result, bases, desc):
        self.exit_v = exit_v        # 0~1 정규화 타구 속도
        self.launch = launch        # 발사각(도)
        self.spray = spray          # 타구 방향(도). -45=좌측 폴, +45=우측 폴
        self.distance = distance    # 비거리(m)
        self.result = result        # 결과 코드
        self.bases = bases          # 진루 수 (0=아웃/파울, 1~4)
        self.desc = desc            # 화면에 띄울 한글 문구

    @property
    def is_hit(self) -> bool:
        return self.bases > 0

    @property
    def is_foul(self) -> bool:
        return self.result == "FOUL"


def fence_at(spray_deg: float) -> float:
    """타구 방향에 따른 펜스까지의 거리(중앙이 가장 멀다)."""
    ratio = abs(spray_deg) / 45.0                  # 0=중앙, 1=폴대
    return FENCE_CENTER + (FENCE_LINE - FENCE_CENTER) * ratio


def resolve(contact, batter: dict, rng: random.Random = None) -> BattedBall:
    """컨택 결과를 타구로 변환한다. contact.made 가 True일 때만 호출."""
    rng = rng or random

    # ── 1) 타구 속도 ──────────────────────────────────────
    # 파워 1~10 을 0.73~1.0 계수로 환산한다.
    # power_q 를 그대로 곱하면 비거리(속도의 제곱에 비례)가 급격히 죽으므로
    # 0.35 의 바닥값을 두어 완만하게 만든다.
    power_k = 0.70 + batter["power"] * 0.030
    raw = 0.35 + 0.65 * contact.power_q
    exit_v = max(0.05, min(1.0, raw * power_k * rng.uniform(0.95, 1.05)))

    # ── 2) 발사각 ─────────────────────────────────────────
    # dy > 0 : 커서가 공보다 아래 → 공 밑을 퍼올림 → 뜬공
    # dy < 0 : 커서가 공보다 위   → 공 윗면을 때림 → 땅볼
    # 정타(dy=0)의 기본값을 라인드라이브 각으로 두어, 살짝 퍼올린 정타가
    # 최적 발사각(28도)에 닿게 한다.
    launch = LAUNCH_BASE + contact.dy * LAUNCH_PER_PX + rng.uniform(-3, 3)
    launch = max(-25.0, min(70.0, launch))

    # ── 3) 타구 방향 ──────────────────────────────────────
    # 타이밍이 빠르면(음수) 당겨치고, 늦으면 밀어친다.
    # 좌우 커서 오차도 방향에 일부 반영된다.
    spray = -contact.timing * 4.0 + contact.dx * 0.5 + rng.uniform(-4, 4)
    spray = max(-70.0, min(70.0, spray))

    # ── 4) 비거리 ─────────────────────────────────────────
    distance = DIST_K * (exit_v ** 2) * _carry(launch)
    # 낮은 라이너·땅볼도 어느 정도는 굴러가도록 바닥값을 준다
    distance = max(distance, 40.0 * exit_v * max(0.0, 1 - abs(launch) / 45.0))

    return _classify(exit_v, launch, spray, distance, rng)


def _classify(exit_v, launch, spray, distance, rng) -> BattedBall:
    """
    물리량 → 결과 코드/진루 수/문구.

    수비를 사람 단위로 시뮬레이션하는 대신 **구간별 안타 확률**로 근사한다.
    확률은 타구 속도와 낙구 지점(내야/외야 앞/갭/펜스)에서 나오므로,
    "잘 맞은 타구가 안타가 되기 쉽다"는 인과가 유지된다.
    """

    # ── 파울 ──────────────────────────────────────────────
    if abs(spray) > 45.0:
        return BattedBall(exit_v, launch, spray, distance, "FOUL", 0, "파울")

    wall = fence_at(spray)
    gap = 22 <= abs(spray) <= 38          # 좌중간·우중간

    # ── 팝플라이 (너무 높이 떴다) ─────────────────────────
    if launch > 50:
        return BattedBall(exit_v, launch, spray, distance, "POP", 0, "내야 뜬공 아웃")

    # ── 뜬공 구간 ─────────────────────────────────────────
    if launch >= 18:
        if distance >= wall:
            desc = "홈런!" if distance < wall + 14 else "장외 홈런!!"
            return BattedBall(exit_v, launch, spray, distance, "HR", 4, desc)
        if distance >= wall - 8:                       # 펜스 직격
            return BattedBall(exit_v, launch, spray, distance, "2B", 2, "펜스 직격 2루타!")
        if distance >= wall - 25:                      # 외야수 뒤 깊은 타구
            if rng.random() < (0.55 if gap else 0.32):
                code, base, txt = ("3B", 3, "우중간을 가르는 3루타!") \
                    if gap and rng.random() < 0.25 else ("2B", 2, "외야 깊숙한 2루타!")
                return BattedBall(exit_v, launch, spray, distance, code, base, txt)
            return BattedBall(exit_v, launch, spray, distance, "FLY", 0, "외야 뜬공 아웃")
        if 46 <= distance:                             # 내야 뒤 텍사스성 타구
            if rng.random() < 0.22:
                return BattedBall(exit_v, launch, spray, distance, "1B", 1, "빗맞은 안타")
            return BattedBall(exit_v, launch, spray, distance, "FLY", 0, "외야 뜬공 아웃")
        return BattedBall(exit_v, launch, spray, distance, "POP", 0, "내야 뜬공 아웃")

    # ── 라인드라이브 구간 ─────────────────────────────────
    if launch >= 5:
        # 강한 라이너일수록 수비 사이를 뚫는다. 정면 직선타로 잡히기도 한다.
        p = max(0.10, min(0.62, 0.06 + (exit_v - 0.35) * 1.25))
        if rng.random() < p:
            if exit_v >= 0.80 and gap and rng.random() < 0.45:
                return BattedBall(exit_v, launch, spray, distance, "2B", 2,
                                  "갭을 가르는 2루타!")
            return BattedBall(exit_v, launch, spray, distance, "1B", 1, "깨끗한 안타!")
        return BattedBall(exit_v, launch, spray, distance, "LINE", 0, "직선타 아웃")

    # ── 땅볼 구간 ─────────────────────────────────────────
    # 3루·유격 쪽으로 강하게 굴러가면 내야 안타 확률이 오른다.
    p = max(0.03, min(0.38, (exit_v - 0.48) * 0.85))
    if abs(spray) >= 25:
        p += 0.06
    if rng.random() < p:
        side = "3루쪽" if spray < -15 else ("1루쪽" if spray > 15 else "중전")
        return BattedBall(exit_v, launch, spray, distance, "1B", 1, f"{side} 안타")
    return BattedBall(exit_v, launch, spray, distance, "GO", 0, "내야 땅볼 아웃")

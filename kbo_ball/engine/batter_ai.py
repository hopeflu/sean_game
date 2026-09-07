"""
CPU 타자.

유저가 투수를 맡을 때 상대 타자를 굴린다. 투구가 시작되는 시점에 한 번
**계획**을 세우고(스윙할지, 한다면 어느 시점에 어디를 노릴지), 엔진은 공이
그 시점에 도달했을 때 스윙을 실행한다. 매 프레임 판단하지 않으므로
결과가 재현 가능하고, 사람 타자와 같은 `swing.judge` 를 그대로 통과한다.

판단 오차 모델
--------------
CPU는 공의 최종 궤적을 알지 못한다. 그래서 `plate_x/plate_y`(무브먼트가 다
적용된 홈플레이트 통과 지점)에 **선구안에 반비례하는 오차**를 섞어 "예상 코스"를
만들고, 그 예상으로만 스트라이크/볼을 판단한다. 변화가 큰 공일수록 예상이
빗나가므로 유인구에 방망이가 따라 나간다.
"""

import random

from .. import config as C


class BatterAI:
    """
    difficulty : 1(쉬움) ~ 5(어려움). 클수록 타이밍·조준이 정확해진다.
                 모든 구단 능력치가 동일하므로 CPU 강도는 이 값으로만 조절한다.
    """

    def __init__(self, difficulty: int = 3, rng=None):
        self.difficulty = max(1, min(5, difficulty))
        self.rng = rng or random.Random()

    # ── 내부: 정확도 계수 ─────────────────────────────────
    def _timing_sd(self, batter, pitch) -> float:
        """
        스윙 타이밍 표준편차(프레임). 작을수록 정확.

        배트 히트박스의 타이밍 창(`swing.judge`의 miss_window)이 컨택 6 기준
        7프레임뿐이라, 여기 값이 5를 넘으면 CPU가 거의 못 친다.
        난이도 3에서 타율 .26 내외가 나오도록 맞춘 계수다.
        """
        base = 3.9 - self.difficulty * 0.40        # 난이도 3 → 2.70
        base -= (batter["contact"] - 5) * 0.18     # 컨택 좋은 타자가 더 정확
        # 변화가 큰 공일수록 타이밍을 뺏긴다
        break_amt = (abs(pitch.type["bx"]) + abs(pitch.type["by"])) / 30.0
        return max(1.0, base + break_amt)

    def _aim_sd(self, batter) -> float:
        """조준 표준편차(px). 배트 반폭(컨택 6 기준 약 12px)과 견줘 잡는다."""
        base = 5.4 - self.difficulty * 0.50        # 난이도 3 → 3.90
        base -= (batter["contact"] - 5) * 0.25
        return max(1.2, base)

    def _read_error(self, batter) -> float:
        """구질 판단 오차(px). 선구안이 좋을수록 작다."""
        return max(2.0, 13.0 - batter["eye"] * 0.9 - self.difficulty * 0.6)

    def _edge_factor(self, pitch) -> float:
        """
        존 중앙에서 멀수록 정확히 맞히기 어렵다 (1.0 ~ 약 1.9).

        이게 없으면 CPU는 실제 통과 지점을 기준으로 조준하므로 **유저가 어디에
        던지든 컨택 품질이 같아진다** — 투구 코스가 게임에 아무 영향을 못 준다.
        코너를 찌르면 약한 타구, 한복판이면 정타가 되도록 만드는 계수.
        """
        cx = C.ZONE_X + C.ZONE_W / 2
        cy = C.ZONE_Y + C.ZONE_H / 2
        dx = abs(pitch.plate_x - cx) / (C.ZONE_W / 2)
        dy = abs(pitch.plate_y - cy) / (C.ZONE_H / 2)
        d = min(1.6, (dx * dx + dy * dy) ** 0.5)
        return 1.0 + 0.55 * d

    def _lock_in(self, batter, balls: int, strikes: int) -> bool:
        """
        '노리고 들어간' 스윙인지. 이때는 타이밍·조준이 크게 좋아지고
        발사각도 홈런 각으로 맞춘다.

        이 장치가 없으면 CPU는 홈런을 거의 못 친다. 타구 속도가 좌우 조준 오차에
        가파르게 반응하는데(power_q), CPU는 항상 일정한 산포로 조준하기 때문에
        담장을 넘길 만한 타구 속도에 도달하는 일이 사실상 없다. 실제 타자도
        유리한 카운트에서 구종을 노리고 들어가 크게 치므로 그 상황을 모델링한다.
        """
        p = 0.05
        if batter["power"] >= 8:
            p += 0.03
        if (balls, strikes) in ((2, 0), (3, 0), (3, 1)):
            p += 0.07                      # 타자에게 유리한 카운트
        return self.rng.random() < p

    # ── 계획 수립 ─────────────────────────────────────────
    def plan(self, pitch, batter, balls: int, strikes: int):
        """
        반환: None(스윙 안 함) 또는 (swing_t, (aim_x, aim_y))
        swing_t 는 pitch.t 기준 시점이다.
        """
        rng = self.rng

        # 1) 예상 통과 지점 — 실제 지점에 판단 오차를 섞는다
        err = self._read_error(batter)
        px = pitch.plate_x + rng.gauss(0, err)
        py = pitch.plate_y + rng.gauss(0, err)
        looks_strike = (C.ZONE_X <= px <= C.ZONE_X + C.ZONE_W and
                        C.ZONE_Y <= py <= C.ZONE_Y + C.ZONE_H)

        # 2) 스윙 여부 — 카운트에 따라 적극성이 달라진다
        if looks_strike:
            p = 0.92 if strikes >= 2 else (0.60 if balls >= 3 else 0.78)
        else:
            p = 0.45 if strikes >= 2 else (0.08 if balls >= 3 else 0.22)
        if rng.random() >= p:
            return None

        # 3) 정확도 계수 — 코스(가장자리일수록 어렵다)와 노림 여부로 정해진다
        edge = self._edge_factor(pitch)
        locked = self._lock_in(batter, balls, strikes)
        sharpen = 0.22 if locked else 1.0

        # 4) 스윙 타이밍 — 홈플레이트 도달(t=1.0) 기준 오차
        err_frames = rng.gauss(0, self._timing_sd(batter, pitch) * edge * sharpen)
        swing_t = 1.0 + err_frames / pitch.flight
        swing_t = max(0.45, min(1.22, swing_t))    # 너무 이르거나 늦지 않게

        # 5) 노리는 좌표 — **실제** 통과 지점 기준으로 조준한다.
        #    판단 오차(px, py)는 위의 스윙 여부 결정에만 쓴다. 조준까지 그 값을
        #    쓰면 판단 오차와 조준 오차가 이중으로 쌓여(합성 SD 6px+) CPU가
        #    아무리 정확해도 타율 .24를 못 넘긴다. 실제 타자도 공을 끝까지
        #    보며 배트 궤도를 조정하므로, 조준은 실제 위치를 기준으로 두는 게 맞다.
        #
        #    공 아래를 노리는 정도(어퍼컷)가 발사각을 만든다. 파워 타자일수록
        #    깊게 퍼올려 홈런을 노리고, 컨택 위주 타자는 거의 수평으로 친다.
        aim_sd = self._aim_sd(batter) * edge * sharpen
        # 노리고 들어간 스윙은 홈런 발사각(약 24도 → dy 5.6px)에 맞춘다
        uppercut = 5.6 if locked else 0.6 + batter["power"] * 0.30
        aim = (pitch.plate_x + rng.gauss(0, aim_sd),
               pitch.plate_y + uppercut + rng.gauss(0, aim_sd))
        return swing_t, aim

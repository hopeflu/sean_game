"""
스윙 판정.

세 축을 따로 재고, **역할을 분리**해서 합친다.
  1) 타이밍(q_time) — SPACE를 누른 시점이 홈플레이트 도달(t=1.0)과 얼마나 가까운가
  2) 좌우 코스(q_dx) — 커서가 공의 좌우 위치와 얼마나 겹치는가
  3) 상하 코스(q_dy) — 커서가 공의 상하 위치와 얼마나 겹치는가

**상하 오차(dy)를 품질에서 크게 떼어놓은 이유**
dy는 batted_ball.py에서 *발사각*을 정하는 값이다. dy가 품질을 좌우까지 지배하면
"뜬공을 만들려면 반드시 빗맞혀야 하는" 구조가 되어 홈런이 나올 수 없다.
그래서 타구 속도(power_q)는 타이밍과 좌우 코스가 주로 결정하고, dy는 완만한
감쇠만 준다. 공 밑을 살짝 퍼올린 정타가 담장을 넘어가도록 만드는 핵심 설계.
"""

import math


class Contact:
    """판정 결과 컨테이너."""

    def __init__(self, made, quality=0.0, power_q=0.0, timing=0.0, dx=0.0, dy=0.0):
        self.made = made              # 배트에 맞았는가
        self.quality = quality        # 종합 정타도 0.0~1.0 (문구 표시용)
        self.power_q = power_q        # 타구 속도로 환산되는 품질 0.0~1.0
        self.timing = timing          # 프레임 단위 오차. 음수=빠름, 양수=늦음
        self.dx = dx                  # 커서 - 공 (가로). 양수=커서가 오른쪽
        self.dy = dy                  # 커서 - 공 (세로). 양수=커서가 아래

    @property
    def label(self) -> str:
        """HUD에 띄울 타이밍 평가 문구."""
        if not self.made:
            return "헛스윙"
        if self.quality >= 0.85:
            return "완벽!"
        if self.quality >= 0.6:
            return "좋음"
        if self.quality >= 0.35:
            return "빗맞음"
        return "간신히"


def judge(pitch, swing_t: float, cursor_xy, contact_rating: int) -> Contact:
    """
    pitch          : Pitch 인스턴스
    swing_t        : SPACE를 누른 순간의 pitch.t 값
    cursor_xy      : 조준 커서 중심 화면좌표
    contact_rating : 타자 컨택 능력 1~10 (히트박스와 타이밍 창을 넓힌다)
    """
    # ── 1) 타이밍 축 ──────────────────────────────────────
    err_frames = (swing_t - 1.0) * pitch.flight
    miss_window = 4.0 + contact_rating * 0.5      # 이 밖이면 배트에 안 맞음
    q_time = 1.0 - min(1.0, abs(err_frames) / miss_window)

    # ── 2) 좌우/상하 코스 축 ──────────────────────────────
    cx, cy = cursor_xy
    dx = cx - pitch.plate_x
    dy = cy - pitch.plate_y
    half_w = 7.0 + contact_rating * 0.8           # 배트 히트박스 반폭
    half_h = 5.5 + contact_rating * 0.75          # 반높이
    q_dx = 1.0 - min(1.0, abs(dx) / half_w)
    q_dy = 1.0 - min(1.0, abs(dy) / half_h)

    # 배트에 아예 닿지 않는 조건
    if q_time <= 0.0 or q_dx <= 0.0 or q_dy <= 0.0:
        return Contact(False, 0.0, 0.0, err_frames, dx, dy)

    # 타구 속도 품질 — 타이밍과 좌우 코스가 주도.
    # 상하(q_dy) 감쇠를 약하게 둬야 "공 밑을 퍼올린 정타 = 홈런"이 성립한다.
    power_q = q_time * (0.45 + 0.55 * q_dx) * (0.82 + 0.18 * q_dy)

    # 표시용 종합 정타도 (상하도 정직하게 반영)
    quality = q_time * q_dx * q_dy

    if power_q <= 0.04:
        return Contact(False, 0.0, 0.0, err_frames, dx, dy)

    return Contact(True, quality, power_q, err_frames, dx, dy)

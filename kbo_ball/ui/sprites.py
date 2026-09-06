"""
픽셀 아트 스프라이트 — 외부 이미지 없이 전부 코드로 그린다.

모든 좌표는 **플레이필드(320x240) 기준**이며, 확대는 상위에서 처리한다.
스프라이트를 코드로 그리면 팀 색을 그대로 유니폼에 입힐 수 있어
KBO 10구단 색 반영이 자산 교체 없이 끝난다.
"""

import pygame

from .. import config as C


def _px(surf, color, x, y, w=1, h=1):
    """플레이필드 픽셀 단위 사각형."""
    pygame.draw.rect(surf, color, (int(x), int(y), int(w), int(h)))


# ── 투수 (마운드, 정면에서 멀리 보임) ─────────────────────
def draw_pitcher(surf, cx, cy, team, wind_up: float = 0.0):
    """
    wind_up : 0=세트포지션, 1=릴리스 직전. 팔 위치가 바뀐다.
    멀리 있으므로 전체 높이 약 22px의 작은 실루엣으로 그린다.
    """
    uni, cap = team["primary"], team["second"]
    skin = (232, 188, 148)

    _px(surf, uni,  cx - 4, cy - 12, 9, 12)      # 몸통
    _px(surf, skin, cx - 3, cy - 18, 7, 6)       # 얼굴
    _px(surf, cap,  cx - 4, cy - 20, 9, 3)       # 모자
    _px(surf, C.WHITE, cx - 4, cy,   4, 9)       # 다리 (왼)
    _px(surf, C.WHITE, cx + 1, cy,   4, 9)       # 다리 (오)
    _px(surf, (32, 32, 40), cx - 5, cy + 9, 11, 2)   # 신발/그림자

    # 팔 — 와인드업 정도에 따라 위로 올라간다
    arm_y = cy - 10 - int(wind_up * 8)
    _px(surf, skin, cx + 5, arm_y, 3, 7)
    if wind_up > 0.75:                            # 릴리스 순간 글러브 반짝
        _px(surf, C.YELLOW, cx + 5, arm_y - 3, 3, 3)


# ── 타자 (화면 좌우 한쪽, 옆모습) ─────────────────────────
def draw_batter(surf, cx, cy, team, swing_phase: float = 0.0, lefty: bool = False):
    """
    swing_phase : 0=대기, 0~1 스윙 진행. 배트 각도가 회전한다.
    """
    uni, cap = team["primary"], team["second"]
    skin = (232, 188, 148)
    face = -1 if lefty else 1                     # 바라보는 방향

    _px(surf, uni,  cx - 5, cy - 20, 11, 14)      # 몸통
    _px(surf, skin, cx - 4, cy - 27, 9, 7)        # 얼굴
    _px(surf, cap,  cx - 5, cy - 29, 11, 3)       # 헬멧
    _px(surf, C.WHITE, cx - 5, cy - 6, 5, 12)     # 다리 (뒤)
    _px(surf, C.WHITE, cx + 1, cy - 6, 5, 12)     # 다리 (앞)
    _px(surf, (32, 32, 40), cx - 6, cy + 6, 13, 2)

    # 배트 — 대기 시 세워 들고, 스윙하면 앞으로 돈다
    import math
    angle = math.radians(-70 + 150 * swing_phase) * face
    bx, by = cx + face * 5, cy - 18
    ex = bx + math.cos(angle) * 16 * face
    ey = by + math.sin(angle) * 16
    pygame.draw.line(surf, (196, 156, 92), (bx, by), (ex, ey), 2)
    _px(surf, skin, bx - 1, by - 1, 3, 3)         # 손


# ── 포수 / 주심 (화면 하단, 뒷모습) ───────────────────────
def draw_catcher(surf, cx, cy, team):
    uni = team["primary"]
    _px(surf, (48, 48, 60), cx - 11, cy - 6, 23, 16)   # 프로텍터
    _px(surf, uni,          cx - 9,  cy - 2, 19, 12)
    _px(surf, (72, 72, 88), cx - 6,  cy - 14, 13, 9)   # 마스크
    _px(surf, (24, 24, 32), cx - 5,  cy - 12, 11, 5)
    _px(surf, (196, 120, 40), cx + 9, cy - 4, 7, 7)    # 미트


def draw_umpire(surf, cx, cy):
    _px(surf, (28, 28, 36), cx - 13, cy - 10, 27, 18)
    _px(surf, (48, 48, 60), cx - 7,  cy - 18, 15, 9)


# ── 공 ────────────────────────────────────────────────────
def draw_ball(surf, x, y, r, spin_phase: float = 0.0, trail=None):
    """공과 잔상. r 이 커질수록 가까이 온 것."""
    if trail:
        for i, (tx, ty) in enumerate(trail):
            a = (i + 1) / (len(trail) + 1)
            shade = tuple(int(c * (0.25 + 0.45 * a)) for c in C.BALL_WHITE)
            pygame.draw.circle(surf, shade, (int(tx), int(ty)),
                               max(1, int(r * (0.45 + 0.4 * a))))

    r = max(1, int(round(r)))
    # 잔디·흙 배경에서도 공이 묻히지 않도록 어두운 외곽선을 먼저 깐다
    pygame.draw.circle(surf, (20, 20, 28), (int(x), int(y)), r + 1)
    pygame.draw.circle(surf, C.BALL_WHITE, (int(x), int(y)), r)
    if r >= 3:
        # 실밥 — 회전에 따라 위치가 도는 두 점
        import math
        for k in (0, 1):
            a = spin_phase * 6.283 + k * 3.141
            sx = x + math.cos(a) * r * 0.5
            sy = y + math.sin(a) * r * 0.5
            _px(surf, C.BALL_SEAM, sx, sy, 1, 1)


# ── 조준 커서 ─────────────────────────────────────────────
def draw_cursor(surf, cx, cy, color=C.YELLOW, size=9, blink=True, frame=0):
    """배트 조준 위치. 코너 4개만 그리는 고전 조준 마커."""
    if blink and (frame // 6) % 2 == 0:
        color = tuple(min(255, int(c * 1.35)) for c in color)
    h = size // 2
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x = cx + sx * h
        y = cy + sy * h
        pygame.draw.line(surf, color, (x, y), (x - sx * 3, y), 1)
        pygame.draw.line(surf, color, (x, y), (x, y - sy * 3), 1)

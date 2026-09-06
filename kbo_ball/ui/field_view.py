"""
타구 중계용 탑다운 구장 화면.

R.B.I. Baseball 계열 고전 야구게임처럼, 배트에 맞는 순간
**투타 클로즈업 → 위에서 내려다본 구장**으로 화면이 전환되는 연출을 담당한다.

좌표 변환
---------
홈플레이트를 화면 아래쪽에 두고, 타구 방향(spray, 도)과 비거리(m)를
플레이필드 픽셀로 옮긴다.  ppm = 픽셀/미터.
"""

import math
import pygame

from .. import config as C
from ..engine.batted_ball import fence_at, FENCE_CENTER

# 하단 HUD 바(플레이필드 기준 22px)에 홈플레이트가 가리지 않도록 위로 올린다.
HOME_X, HOME_Y = 160, 210
PPM = 160.0 / FENCE_CENTER          # 중앙 펜스가 화면 위쪽에 딱 맞도록


def to_screen(spray_deg: float, dist_m: float):
    """(타구방향, 비거리) → 플레이필드 좌표."""
    a = math.radians(spray_deg)
    x = HOME_X + math.sin(a) * dist_m * PPM
    y = HOME_Y - math.cos(a) * dist_m * PPM
    return x, y


def draw_field(pf, defense_team):
    """잔디·내야·파울라인·펜스·수비수를 그린다."""
    pf.fill(C.NIGHT)

    # ── 외야 잔디 (부채꼴을 폴리곤으로) ───────────────────
    fence_pts = [to_screen(a, fence_at(a)) for a in range(-45, 46, 3)]
    pygame.draw.polygon(pf, C.TURF, [(HOME_X, HOME_Y)] + fence_pts)

    # 잔디 줄무늬 — 부채꼴 방향으로 번갈아 어둡게
    for i, a in enumerate(range(-45, 45, 6)):
        if i % 2:
            continue
        wedge = [(HOME_X, HOME_Y),
                 to_screen(a, fence_at(a)),
                 to_screen(a + 6, fence_at(a + 6))]
        pygame.draw.polygon(pf, C.TURF_DARK, wedge)

    # ── 워닝트랙 & 펜스 ───────────────────────────────────
    track = [to_screen(a, fence_at(a) - 5) for a in range(-45, 46, 3)]
    pygame.draw.lines(pf, C.DIRT, False, track, 3)
    pygame.draw.lines(pf, C.LINE_WHITE, False, fence_pts, 2)

    # ── 내야 흙 ───────────────────────────────────────────
    infield = [to_screen(a, 42) for a in range(-45, 46, 5)]
    pygame.draw.polygon(pf, C.DIRT, [(HOME_X, HOME_Y)] + infield)

    # ── 베이스 & 파울라인 ─────────────────────────────────
    b1 = to_screen(45, 27.4)     # 27.4m = 90피트
    b2 = to_screen(0, 38.8)
    b3 = to_screen(-45, 27.4)
    pygame.draw.polygon(pf, C.TURF_DARK,
                        [(HOME_X, HOME_Y), b1, b2, b3])
    pygame.draw.polygon(pf, C.LINE_WHITE,
                        [(HOME_X, HOME_Y), b1, b2, b3], 1)
    for bx, by in (b1, b2, b3):
        pygame.draw.rect(pf, C.LINE_WHITE, (int(bx) - 2, int(by) - 2, 5, 5))
    pygame.draw.rect(pf, C.BONE, (HOME_X - 3, HOME_Y - 3, 7, 6))

    # 파울라인
    for s in (-45, 45):
        pygame.draw.line(pf, C.LINE_WHITE, (HOME_X, HOME_Y),
                         to_screen(s, fence_at(s)), 1)

    # ── 수비수 9명 (대략적인 정위치) ──────────────────────
    spots = [(0, 18.4), (0, 0),                       # 투수, 포수
             (38, 33), (18, 43), (-18, 43), (-38, 33),  # 1·2·유·3루
             (-30, 88), (0, 100), (30, 88)]             # 좌·중·우익수
    for s, d in spots:
        x, y = to_screen(s, d)
        pygame.draw.circle(pf, defense_team["primary"], (int(x), int(y)), 3)
        pygame.draw.circle(pf, (16, 16, 24), (int(x), int(y)), 3, 1)


def draw_ball_flight(pf, bb, progress: float):
    """
    타구 궤적을 그린다.
    progress : 0=타격 순간, 1=낙하 지점 도달
    포물선 높이는 그림자와의 거리로 표현한다(탑다운이므로 y를 살짝 띄운다).
    """
    p = max(0.0, min(1.0, progress))
    d = bb.distance * p
    x, y = to_screen(bb.spray, d)

    # 궤적 잔상
    for k in range(1, 7):
        pp = max(0.0, p - k * 0.045)
        tx, ty = to_screen(bb.spray, bb.distance * pp)
        shade = 90 + k * 12
        pygame.draw.rect(pf, (shade, shade, shade - 20), (int(tx), int(ty), 1, 1))

    # 그림자(지면)와 공(공중) — 뜬공일수록 크게 벌어진다
    hop = math.sin(math.pi * p) * (bb.launch / 60.0) * 26
    pygame.draw.circle(pf, (16, 48, 20), (int(x), int(y)), 3)
    pygame.draw.circle(pf, (20, 20, 28), (int(x), int(y - hop)), 4)
    pygame.draw.circle(pf, C.BALL_WHITE, (int(x), int(y - hop)), 3)


def draw_runner(pf, team, progress: float, bases: int):
    """
    타자 주자가 베이스를 도는 모습(점 하나)을 그린다.
    progress : 0~1. bases 만큼의 루를 이 시간 동안 돈다.
    """
    # 홈 → 1루 → 2루 → 3루 → 홈 순서의 꼭짓점
    path = [(HOME_X, HOME_Y),
            to_screen(45, 27.4), to_screen(0, 38.8), to_screen(-45, 27.4),
            (HOME_X, HOME_Y)]

    travelled = max(0.0, min(float(max(bases, 1)), progress * max(bases, 1)))
    seg = int(travelled)
    frac = travelled - seg
    if seg >= len(path) - 1:
        seg, frac = len(path) - 2, 1.0

    x0, y0 = path[seg]
    x1, y1 = path[seg + 1]
    x = x0 + (x1 - x0) * frac
    y = y0 + (y1 - y0) * frac

    pygame.draw.circle(pf, (16, 16, 24), (int(x), int(y)), 4)
    pygame.draw.circle(pf, team["primary"], (int(x), int(y)), 3)
    pygame.draw.circle(pf, team["accent"], (int(x), int(y) - 3), 1)


def draw_landing_mark(pf, bb, frame):
    """낙구 지점 표시 — 깜빡이는 X."""
    x, y = to_screen(bb.spray, bb.distance)
    if (frame // 6) % 2 == 0:
        return
    for dx, dy in ((-3, -3), (3, 3), (-3, 3), (3, -3)):
        pygame.draw.line(pf, C.YELLOW, (x, y), (x + dx, y + dy), 1)

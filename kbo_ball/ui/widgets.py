"""
HUD 위젯.

sprites.py 와 달리 이 모듈은 **창 해상도(960x720)에 직접** 그린다.
한글 텍스트를 320x240에 그리면 자모가 뭉개져 읽을 수 없기 때문이다.
픽셀 아트(플레이필드)와 선명한 텍스트(HUD)를 레이어로 분리한 구조.
"""

import pygame

from .. import config as C
from ..fonts import draw_text
from ..retro import bevel_box


def panel(surf, rect, alpha=225):
    """반투명 검은 패널 + 밝은 테두리."""
    x, y, w, h = rect
    box = pygame.Surface((w, h), pygame.SRCALPHA)
    box.fill((*C.PANEL_BG, alpha))
    surf.blit(box, (x, y))
    pygame.draw.rect(surf, C.PANEL_EDGE, rect, 2)


def lamp_row(surf, x, y, label, lit, total, color, radius=8, gap=22):
    """B / S / O 램프 줄. 전광판의 그 표시."""
    draw_text(surf, label, (x, y), size=20, color=C.WHITE, bold=True, anchor="midleft")
    for i in range(total):
        cx = x + 34 + i * gap
        on = i < lit
        pygame.draw.circle(surf, color if on else (48, 48, 58), (cx, y), radius)
        pygame.draw.circle(surf, (16, 16, 24), (cx, y), radius, 2)


def count_board(surf, x, y, half_inning, pitcher_name, batter):
    """
    좌상단 카운트 보드.
    half_inning : engine.rules.HalfInning
    """
    w, h = 230, 168
    panel(surf, (x, y, w, h))

    draw_text(surf, "COUNT", (x + 14, y + 14), size=18, color=C.YELLOW, bold=True)

    c = half_inning.count
    lamp_row(surf, x + 20, y + 52, "B", c.balls,   3, C.GREEN)
    lamp_row(surf, x + 20, y + 80, "S", c.strikes, 2, C.YELLOW)
    lamp_row(surf, x + 20, y + 108, "O", half_inning.outs, 2, C.RED)

    draw_text(surf, f"투수 {pitcher_name}", (x + 14, y + 130), size=15, color=C.CYAN)
    draw_text(surf, f"타자 {batter['name']} ({batter['pos']})",
              (x + 14, y + 148), size=15, color=C.WHITE)


def base_diamond(surf, cx, cy, bases, size=34):
    """주자 상황을 보여주는 작은 다이아몬드."""
    pts = {
        0: (cx + size, cy),          # 1루
        1: (cx, cy - size),          # 2루
        2: (cx - size, cy),          # 3루
    }
    home = (cx, cy + size)
    # 연결선
    order = [home, pts[0], pts[1], pts[2], home]
    pygame.draw.lines(surf, (90, 90, 110), False, order, 2)
    # 베이스
    for i, p in pts.items():
        col = C.YELLOW if bases[i] else (60, 60, 76)
        pygame.draw.polygon(surf, col, _diamond_pts(p, 9))
        pygame.draw.polygon(surf, (16, 16, 24), _diamond_pts(p, 9), 2)
    pygame.draw.polygon(surf, C.BONE, _diamond_pts(home, 8))


def _diamond_pts(center, r):
    x, y = center
    return [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]


def runner_board(surf, x, y, half_inning):
    """우상단 주자/득점 보드."""
    w, h = 200, 168
    panel(surf, (x, y, w, h))
    draw_text(surf, "주자", (x + 14, y + 14), size=18, color=C.YELLOW, bold=True)
    base_diamond(surf, x + w // 2, y + 82, half_inning.bases)
    draw_text(surf, f"득점 {half_inning.runs}", (x + w // 2, y + 138),
              size=20, color=C.WHITE, bold=True, anchor="midtop")


def stat_line(surf, x, y, stats):
    """하단 성적 한 줄."""
    txt = (f"{stats.ab}타수 {stats.hits}안타  홈런 {stats.hr}  "
           f"타점 {stats.rbi}  삼진 {stats.strikeouts}  볼넷 {stats.walks}  "
           f"타율 {stats.avg_text()}")
    draw_text(surf, txt, (x, y), size=17, color=(200, 210, 230))


def result_banner(surf, text, sub=None, color=C.YELLOW, y=None):
    """
    타석 결과를 크게 띄우는 배너.
    좌우의 로그/주자 패널을 덮지 않도록 폭을 480px로 제한한다.
    """
    y = y if y is not None else C.WIN_H // 2 - 60
    w, h = 480, 120 if sub else 84
    x = (C.WIN_W - w) // 2
    bevel_box(surf, (x, y, w, h), (12, 12, 28), (220, 220, 236), (60, 60, 76), border=3)
    draw_text(surf, text, (C.WIN_W // 2, y + (34 if sub else 42)),
              size=40, color=color, bold=True, anchor="center")
    if sub:
        draw_text(surf, sub, (C.WIN_W // 2, y + 84),
                  size=19, color=(200, 210, 230), anchor="center")


def linescore(surf, x, y, board, away_team, home_team, away_stats, home_stats,
              w=436):
    """
    상단 중앙 전광판 — 이닝별 득점 + R(득점) H(안타).

    연장 이닝이 붙어도 폭이 늘어나지 않도록 칸 너비를 이닝 수로 나눠 정한다.
    현재 진행 중인 반 이닝은 노란 테두리로 표시한다.
    """
    n = board.innings_played
    head_w, tail_w = 62, 40                      # 팀명 칸 / R·H 칸
    cell = max(16, (w - head_w - tail_w * 2) // n)
    h = 78
    panel(surf, (x, y, w, h))

    def col_x(i):
        return x + head_w + i * cell

    # ── 헤더 ──────────────────────────────────────────────
    for i in range(n):
        draw_text(surf, str(i + 1), (col_x(i) + cell // 2, y + 8), size=13,
                  color=(150, 160, 195), anchor="midtop")
    draw_text(surf, "R", (x + w - tail_w * 2 + tail_w // 2, y + 8), size=13,
              color=C.YELLOW, bold=True, anchor="midtop")
    draw_text(surf, "H", (x + w - tail_w + tail_w // 2, y + 8), size=13,
              color=(150, 160, 195), anchor="midtop")

    # ── 두 팀 행 ──────────────────────────────────────────
    rows = (("away", away_team, away_stats), ("home", home_team, home_stats))
    for r, (side, team, stats) in enumerate(rows):
        ry = y + 28 + r * 24
        draw_text(surf, team["code"], (x + 10, ry), size=16,
                  color=team["accent"], bold=True)

        for i, runs in enumerate(board.row(side, n)):
            txt = "-" if runs is None else str(runs)
            col = C.WHITE if runs is not None else (78, 84, 110)
            # 지금 진행 중인 반 이닝 강조
            live = (not board.final and i == board.inning - 1
                    and ((side == "away") == board.top))
            if live:
                pygame.draw.rect(surf, C.YELLOW,
                                 (col_x(i) + 1, ry - 2, cell - 2, 22), 1)
            draw_text(surf, txt, (col_x(i) + cell // 2, ry), size=15,
                      color=col, anchor="midtop")

        draw_text(surf, str(board.total(side)),
                  (x + w - tail_w * 2 + tail_w // 2, ry), size=17,
                  color=C.YELLOW, bold=True, anchor="midtop")
        draw_text(surf, str(stats.hits),
                  (x + w - tail_w + tail_w // 2, ry), size=15,
                  color=(200, 210, 230), anchor="midtop")


def pitch_selector(surf, x, y, types, idx, w=560):
    """유저 투구 시 구종 선택 줄. 선택된 구종을 그 구종의 식별색으로 강조한다."""
    chip = w // len(types)
    for i, t in enumerate(types):
        cx = x + i * chip
        on = (i == idx)
        bg = (t["color"] if on else (26, 28, 46))
        fg = ((10, 10, 20) if on else (150, 160, 190))
        bevel_box(surf, (cx + 3, y, chip - 6, 34), bg,
                  (240, 240, 250) if on else (70, 74, 100), (16, 16, 26),
                  border=2 if on else 1)
        draw_text(surf, f"{i + 1}", (cx + 12, y + 8), size=13, color=fg)
        draw_text(surf, t["name"], (cx + chip // 2 + 6, y + 8), size=16,
                  color=fg, bold=on, anchor="midtop")


def shift_indicator(surf, x, y, shift, w=196, h=34):
    """현재 수비 시프트 표시. 표준이 아니면 강조한다."""
    active = shift["key"] != "STD"
    bevel_box(surf, (x, y, w, h), (34, 26, 16) if active else (26, 28, 46),
              (230, 200, 120) if active else (70, 74, 100), (16, 16, 26),
              border=2 if active else 1)
    draw_text(surf, "수비", (x + 10, y + 9), size=13, color=(150, 160, 190))
    draw_text(surf, shift["name"], (x + w - 10, y + 7), size=15,
              color=C.YELLOW if active else (190, 198, 220),
              bold=active, anchor="topright")


def pitch_log(surf, x, y, entries):
    """최근 타석 결과 목록."""
    for i, line in enumerate(entries[-6:]):
        draw_text(surf, line, (x, y + i * 20), size=15, color=(150, 160, 190))

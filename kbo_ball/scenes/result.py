"""반 이닝 종료 화면 — 기록 요약과 등급 판정."""

import pygame

from .. import config as C
from .. import sfx
from ..fonts import draw_text
from ..retro import vgradient, bevel_box
from ..ui import sprites
from .base import Scene


def _grade(stats, runs: int) -> tuple:
    """3아웃 동안의 성적을 고전 게임식 등급으로 환산한다."""
    score = runs * 3 + stats.hits * 2 + stats.hr * 3 - stats.strikeouts
    if score >= 12:
        return "S", C.YELLOW, "전설의 이닝!"
    if score >= 8:
        return "A", C.GREEN, "빅이닝을 만들었다"
    if score >= 4:
        return "B", C.CYAN, "무난한 공격"
    if score >= 1:
        return "C", C.WHITE, "아쉬운 마무리"
    return "D", C.RED, "삼자범퇴"


class ResultScene(Scene):
    def __init__(self, app, half):
        super().__init__(app)
        self.half = half
        self.grade, self.color, self.comment = _grade(half.stats, half.runs)
        sfx.play("select")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_SPACE, pygame.K_RETURN):
            sfx.play("select")
            from .duel import DuelScene
            self.next_scene = DuelScene(self.app)     # 같은 매치업으로 재도전
        elif event.key == pygame.K_ESCAPE:
            from .title import TitleScene
            self.next_scene = TitleScene(self.app)

    # ── 픽셀 아트 레이어 ──────────────────────────────────
    def draw_playfield(self, pf):
        vgradient(pf, (0, 0, C.PF_W, C.PF_H), (12, 14, 30), (34, 44, 84), bands=10)
        # 홈런 세리머니 느낌으로 타자 스프라이트를 크게 배치
        sprites.draw_batter(pf, 60, 214, self.app.my_team,
                            swing_phase=0.75)
        sprites.draw_pitcher(pf, 262, 206, self.app.opp_team, wind_up=0.0)

    # ── HUD 레이어 ────────────────────────────────────────
    def draw_hud(self, win):
        cx = C.WIN_W // 2
        s = self.half.stats

        draw_text(win, "이닝 종료", (cx, 44), size=34, color=C.YELLOW,
                  bold=True, anchor="center")

        # 등급 박스
        bevel_box(win, (cx - 70, 86, 140, 108), (12, 12, 28),
                  (220, 220, 236), (60, 60, 76), border=3)
        draw_text(win, self.grade, (cx, 132), size=72, color=self.color,
                  bold=True, anchor="center")
        draw_text(win, self.comment, (cx, 208), size=20,
                  color=(210, 220, 240), anchor="center")

        # 기록 표
        rows = [
            ("득점",   f"{self.half.runs}"),
            ("타수",   f"{s.ab}"),
            ("안타",   f"{s.hits}"),
            ("2루타",  f"{s.doubles}"),
            ("3루타",  f"{s.triples}"),
            ("홈런",   f"{s.hr}"),
            ("타점",   f"{s.rbi}"),
            ("볼넷",   f"{s.walks}"),
            ("삼진",   f"{s.strikeouts}"),
            ("타율",   s.avg_text()),
        ]
        x0, y0 = cx - 300, 252
        for i, (k, v) in enumerate(rows):
            col, row = divmod(i, 5)
            x = x0 + col * 320
            y = y0 + row * 40
            bevel_box(win, (x, y, 280, 32), (18, 20, 40),
                      (90, 96, 130), (8, 8, 16), border=1)
            draw_text(win, k, (x + 14, y + 6), size=18, color=(180, 190, 220))
            draw_text(win, v, (x + 264, y + 4), size=20, color=C.WHITE,
                      bold=True, anchor="topright")

        # 타석 로그
        draw_text(win, "타석 기록", (cx - 300, 470), size=18, color=C.CYAN, bold=True)
        for i, line in enumerate(self.half.log[-6:]):
            draw_text(win, line, (cx - 300, 498 + i * 22), size=16,
                      color=(160, 170, 200))

        if (self.frame // 26) % 2 == 0:
            draw_text(win, "SPACE 다시 도전    ESC 타이틀로",
                      (cx, C.WIN_H - 56), size=22, color=(200, 220, 255),
                      bold=True, anchor="center")

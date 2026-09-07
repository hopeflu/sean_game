"""경기 종료 화면 — 최종 전광판과 양 팀 기록."""

import pygame

from .. import config as C
from .. import sfx
from ..fonts import draw_text
from ..retro import vgradient, bevel_box
from ..ui import sprites, widgets
from .base import Scene


class GameResultScene(Scene):
    def __init__(self, app, board, teams, game_stats, user_side,
                 two_player: bool = False):
        super().__init__(app)
        self.board = board
        self.teams = teams
        self.stats = game_stats
        self.user_side = user_side
        self.two_player = two_player
        sfx.play("hr" if (two_player or self.user_won) else "out")

    # ── 결과 판정 ─────────────────────────────────────────
    @property
    def winner(self) -> str:
        return self.board.winner

    @property
    def user_won(self) -> bool:
        return self.winner == self.user_side

    def headline(self):
        if self.winner == "draw":
            return "무승부", C.GRAY
        if self.two_player:
            # 1P=홈, 2P=원정 (game.py 의 _player_of 와 같은 규약)
            who = "1P" if self.winner == "home" else "2P"
            suffix = " 끝내기 승!" if self.board.walkoff else " 승리!"
            return who + suffix, C.YELLOW
        if self.user_won:
            return "끝내기 승!" if self.board.walkoff else "승리!", C.YELLOW
        return "패배", C.RED

    # ── 입력 ──────────────────────────────────────────────
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_SPACE, pygame.K_RETURN):
            sfx.play("select")
            from .game import GameScene
            self.next_scene = GameScene(self.app)       # 같은 매치업으로 재경기
        elif event.key == pygame.K_ESCAPE:
            from .title import TitleScene
            self.next_scene = TitleScene(self.app)

    # ── 렌더 ──────────────────────────────────────────────
    def draw_playfield(self, pf):
        vgradient(pf, (0, 0, C.PF_W, C.PF_H), (12, 14, 30), (34, 44, 84), bands=10)
        win_team = (self.teams[self.winner] if self.winner != "draw"
                    else self.teams[self.user_side])
        # 기록 표(창 기준 x 180~780 = 플레이필드 60~260)를 침범하지 않도록
        # 스프라이트를 화면 양 끝에 붙인다.
        sprites.draw_batter(pf, 26, 216, win_team, swing_phase=0.75)
        sprites.draw_pitcher(pf, 296, 208, win_team, wind_up=0.4)

    def draw_hud(self, win):
        cx = C.WIN_W // 2
        text, color = self.headline()

        draw_text(win, "경기 종료", (cx, 34), size=26, color=(180, 190, 220),
                  anchor="center")
        draw_text(win, text, (cx, 84), size=54, color=color, bold=True,
                  anchor="center")

        # 최종 스코어
        a, h = self.board.total("away"), self.board.total("home")
        draw_text(win,
                  f"{self.teams['away']['name']}  {a}   -   "
                  f"{h}  {self.teams['home']['name']}",
                  (cx, 148), size=26, color=C.WHITE, bold=True, anchor="center")

        # 이닝별 전광판
        widgets.linescore(win, cx - 300, 192, self.board,
                          self.teams["away"], self.teams["home"],
                          self.stats["away"], self.stats["home"], w=600)

        # 양 팀 기록 표
        rows = [
            ("타수",  "ab"), ("안타", "hits"), ("2루타", "doubles"),
            ("홈런",  "hr"), ("타점", "rbi"), ("볼넷",  "walks"),
            ("삼진",  "strikeouts"),
        ]
        x0, y0 = cx - 300, 300
        col_w = 600

        bevel_box(win, (x0, y0, col_w, 30), (18, 20, 40), (90, 96, 130),
                  (8, 8, 16), border=1)
        draw_text(win, "항목", (x0 + 14, y0 + 5), size=16, color=(170, 180, 210))
        for i, side in enumerate(("away", "home")):
            label = self.teams[side]["code"]
            if self.two_player:
                label += "  (2P)" if side == "away" else "  (1P)"
            draw_text(win, label, (x0 + 300 + i * 200, y0 + 4), size=17,
                      color=self.teams[side]["accent"], bold=True, anchor="midtop")

        for r, (label, attr) in enumerate(rows):
            ry = y0 + 34 + r * 32
            bevel_box(win, (x0, ry, col_w, 28), (14, 16, 32), (70, 74, 100),
                      (8, 8, 16), border=1)
            draw_text(win, label, (x0 + 14, ry + 4), size=16, color=(180, 190, 220))
            for i, side in enumerate(("away", "home")):
                draw_text(win, str(getattr(self.stats[side], attr)),
                          (x0 + 300 + i * 200, ry + 3), size=17,
                          color=C.WHITE, anchor="midtop")

        # 타율 행
        ry = y0 + 34 + len(rows) * 32
        bevel_box(win, (x0, ry, col_w, 28), (14, 16, 32), (70, 74, 100),
                  (8, 8, 16), border=1)
        draw_text(win, "타율", (x0 + 14, ry + 4), size=16, color=(180, 190, 220))
        for i, side in enumerate(("away", "home")):
            draw_text(win, self.stats[side].avg_text(),
                      (x0 + 300 + i * 200, ry + 3), size=17,
                      color=C.WHITE, anchor="midtop")

        if (self.frame // 26) % 2 == 0:
            draw_text(win, "SPACE 재경기    ESC 타이틀로",
                      (cx, C.WIN_H - 42), size=22, color=(200, 220, 255),
                      bold=True, anchor="center")

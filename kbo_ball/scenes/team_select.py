"""
구단 선택 화면.

2단계로 진행한다.
  1단계 : 내 팀(공격 = 타자) 선택
  2단계 : 상대 팀(수비 = 투수) 선택
방향키로 5x2 격자를 이동하고 SPACE로 확정, ESC로 한 단계 뒤로 간다.
"""

import pygame

from .. import config as C
from .. import sfx
from ..data.teams import TEAMS
from ..data.roster import build_lineup, build_pitcher
from ..fonts import draw_text
from ..retro import bevel_box, vgradient
from ..ui import sprites
from .base import Scene

COLS, ROWS = 5, 2


class TeamSelectScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.step = 0            # 0=내 팀, 1=상대 팀
        self.index = 0           # 격자 커서 위치
        self.picked = [None, None]

    # ── 입력 ──────────────────────────────────────────────
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            if self.step == 1:
                self.step = 0                      # 한 단계 뒤로
                self.index = TEAMS.index(self.picked[0])
                self.picked[1] = None
            else:
                from .title import TitleScene
                self.next_scene = TitleScene(self.app)
            return

        moved = True
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.index = (self.index - 1) % len(TEAMS)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.index = (self.index + 1) % len(TEAMS)
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.index = (self.index - COLS) % len(TEAMS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.index = (self.index + COLS) % len(TEAMS)
        else:
            moved = False

        if moved:
            sfx.play("move")
            return

        if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            sfx.play("select")
            self.picked[self.step] = TEAMS[self.index]
            if self.step == 0:
                self.step = 1
                # 상대는 기본적으로 다른 팀을 가리키게 한다
                self.index = (self.index + 1) % len(TEAMS)
            else:
                self._start_game()

    def _start_game(self):
        """선택 결과로 앱 상태를 채우고 선택한 모드의 씬으로 넘어간다."""
        app = self.app
        app.my_team, app.opp_team = self.picked

        # 1경기 모드는 양 팀의 타순과 선발이 모두 필요하다
        app.lineup = build_lineup(app.my_team)
        app.opp_lineup = build_lineup(app.opp_team)
        app.pitcher = build_pitcher(app.opp_team)      # 상대 선발
        app.my_pitcher = build_pitcher(app.my_team)    # 우리 선발

        if getattr(app, "mode", "duel") == "game":
            from .game import GameScene
            self.next_scene = GameScene(app)
        else:
            from .duel import DuelScene
            self.next_scene = DuelScene(app)

    # ── 픽셀 아트 레이어 ──────────────────────────────────
    def draw_playfield(self, pf):
        vgradient(pf, (0, 0, C.PF_W, C.PF_H), (14, 16, 34), (30, 40, 76), bands=10)

        # 화면 중단(격자와 안내문 사이의 빈 띠)에 유니폼 미리보기를 놓는다.
        # 아래쪽에 두면 안내 텍스트와 겹친다.
        team = TEAMS[self.index]
        sprites.draw_batter(pf, 108, 158, team, swing_phase=0.0)
        sprites.draw_pitcher(pf, 212, 152, team, wind_up=0.35)

        # 이미 고른 내 팀은 왼쪽에 작게 표시
        if self.picked[0]:
            sprites.draw_batter(pf, 32, 158, self.picked[0])

    # ── HUD 레이어 ────────────────────────────────────────
    def draw_hud(self, win):
        cx = C.WIN_W // 2
        if getattr(self.app, "two_player", False):
            # 2인용은 1P=홈(후공), 2P=원정(선공) — game.py 의 규약과 같다
            head = "1P 팀 선택 (홈·후공)" if self.step == 0 else "2P 팀 선택 (원정·선공)"
        else:
            head = "내 팀 선택 (공격)" if self.step == 0 else "상대 팀 선택 (수비)"
        draw_text(win, head, (cx, 42), size=32, color=C.YELLOW,
                  bold=True, anchor="center")

        # ── 팀 격자 ───────────────────────────────────────
        cell_w, cell_h = 168, 74
        gap = 10
        grid_w = COLS * cell_w + (COLS - 1) * gap
        ox = (C.WIN_W - grid_w) // 2
        oy = 100

        for i, team in enumerate(TEAMS):
            r, c = divmod(i, COLS)
            x = ox + c * (cell_w + gap)
            y = oy + r * (cell_h + gap)
            selected = (i == self.index)

            # 이미 1단계에서 고른 팀은 흐리게
            taken = (self.step == 1 and team is self.picked[0])

            fill = team["primary"] if not taken else (48, 48, 56)
            light = (255, 255, 255) if selected else (120, 120, 140)
            bevel_box(win, (x, y, cell_w, cell_h), fill, light, (20, 20, 28),
                      border=3 if selected else 1)

            draw_text(win, team["code"], (x + 12, y + 10), size=26,
                      color=team["accent"], bold=True)
            draw_text(win, team["name"], (x + 12, y + 42), size=17,
                      color=(240, 240, 245) if not taken else (130, 130, 140))

            if selected:
                draw_text(win, "▶", (x - 22, y + cell_h // 2), size=26,
                          color=C.YELLOW, anchor="center")

        # ── 하단 정보 ─────────────────────────────────────
        team = TEAMS[self.index]
        draw_text(win, f"{team['name']}  ·  연고지 {team['city']}",
                  (cx, oy + ROWS * (cell_h + gap) + 26), size=24,
                  color=C.WHITE, bold=True, anchor="center")

        # 미리보기 스프라이트 아래 라벨 (플레이필드 y=158 → 창 y≈474)
        draw_text(win, "타자", (324, 500), size=16, color=(170, 180, 210), anchor="center")
        draw_text(win, "투수", (636, 500), size=16, color=(170, 180, 210), anchor="center")
        if self.picked[0]:
            owner = "1P" if getattr(self.app, "two_player", False) else "공격"
            draw_text(win, f"{owner}  {self.picked[0]['name']}",
                      (96, 500), size=17, color=C.CYAN, anchor="center")

        draw_text(win,
                  "모든 구단의 능력치는 동일합니다 (색·엠블럼만 다름)",
                  (cx, C.WIN_H - 108), size=16, color=(140, 150, 185), anchor="center")
        draw_text(win, "방향키 이동    SPACE 결정    ESC 뒤로",
                  (cx, C.WIN_H - 74), size=18, color=(180, 190, 220), anchor="center")

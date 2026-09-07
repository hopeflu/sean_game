"""
투타 대결 씬 (Phase 1) — 반 이닝 하나를 유저 타격으로 플레이한다.

타석 진행과 렌더는 `atbat.AtBatEngine` 이 담당하므로, 이 씬은 호스트 규약을
채우고 HUD만 그린다. 1경기 씬(`game.py`)도 같은 엔진을 쓴다.
"""

import random
import pygame

from .. import config as C
from ..engine.pitch import PitcherAI
from ..engine.rules import HalfInning
from ..fonts import draw_text
from ..retro import shake_offset
from ..ui import widgets
from . import atbat
from .base import Scene


class DuelScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.rng = random.Random()
        self.half = HalfInning(rng=self.rng)
        self.pitcher_ai = PitcherAI(app.pitcher)
        self.batter_ai = None            # 유저가 항상 타격하므로 쓰이지 않는다

        self.batter_idx = 0
        self.engine = atbat.AtBatEngine(self, self.rng)

    # ── 호스트 규약 ───────────────────────────────────────
    @property
    def batter(self):
        return self.app.lineup[self.batter_idx % len(self.app.lineup)]

    @property
    def pitcher(self):
        return self.app.pitcher

    @property
    def bat_team(self):
        return self.app.my_team

    @property
    def field_team(self):
        return self.app.opp_team

    # 유저가 타자, CPU가 투수 (2인용은 game.py 쪽에서만 지원)
    batter_player = 1
    pitcher_player = None

    def next_batter(self):
        self.batter_idx += 1

    # ── 입력 ──────────────────────────────────────────────
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from .title import TitleScene
            self.next_scene = TitleScene(self.app)
            return
        self.engine.handle_event(event)

    # ── 갱신 ──────────────────────────────────────────────
    def update(self):
        self.engine.update()
        if self.engine.state == atbat.DONE:
            from .result import ResultScene
            self.next_scene = ResultScene(self.app, self.half)

    # ── 렌더 ──────────────────────────────────────────────
    def draw_playfield(self, pf):
        self.engine.draw_playfield(pf)

    def draw_hud(self, win):
        half = self.half
        widgets.count_board(win, 24, 24, half, self.pitcher["name"], self.batter)
        widgets.runner_board(win, C.WIN_W - 224, 24, half)

        draw_text(win, f"{self.bat_team['code']} 공격", (C.WIN_W // 2, 30),
                  size=22, color=self.bat_team["accent"], bold=True, anchor="midtop")
        draw_text(win, f"vs {self.field_team['name']}", (C.WIN_W // 2, 58),
                  size=16, color=(170, 180, 210), anchor="midtop")

        # 좌측 — 타석 기록 로그 (결과 배너 폭 480과 겹치지 않도록 200)
        widgets.panel(win, (24, 204, 200, 152))
        draw_text(win, "타석 기록", (38, 216), size=16, color=C.CYAN, bold=True)
        widgets.pitch_log(win, 38, 242, half.log)

        # 하단 — 성적 한 줄 + 조작 안내
        widgets.panel(win, (0, C.WIN_H - 58, C.WIN_W, 58), alpha=235)
        widgets.stat_line(win, 24, C.WIN_H - 40, half.stats)
        draw_text(win, C.CONTROL_HINT_BAT, (C.WIN_W - 24, C.WIN_H - 40),
                  size=15, color=(130, 140, 175), anchor="topright")

        if self.engine.state == atbat.RESULT and self.engine.banner:
            title, sub, color = self.engine.banner
            widgets.result_banner(win, title, sub, color)

        if self.engine.state == atbat.READY:
            b = self.batter
            widgets.result_banner(
                win, f"{b['order']}번 {b['pos']}  {b['name']}",
                f"컨택 {b['contact']}  파워 {b['power']}  선구안 {b['eye']}",
                self.bat_team["accent"])

    def playfield_offset(self):
        return shake_offset(self.engine.shake, magnitude=3)

"""모드 선택 — 투타 대결(Phase 1) / 1경기(Phase 2)."""

import pygame

from .. import config as C
from .. import sfx
from ..fonts import draw_text
from ..retro import vgradient, bevel_box
from ..ui import sprites
from .base import Scene

MODES = [
    {"key": "duel", "title": "투타 대결",
     "sub": "반 이닝 3아웃 · 유저는 타자만",
     "desc": "타격 감각을 익히는 짧은 모드. 3아웃까지의 성적으로 등급이 나온다."},
    {"key": "game", "title": "1경기 (9이닝)",
     "sub": "공수 교대 · 유저가 타격과 투구를 모두",
     "desc": "유저는 홈(후공). 1회초 투구로 시작하고 9회말 끝내기가 가능하다."},
    {"key": "vs", "title": "2인용 대전 (9이닝)",
     "sub": "한 사람은 타격, 다른 사람은 투구+수비",
     "desc": "타자는 마우스, 투수는 키보드+넘패드. 반 이닝마다 장치를 바꿔 쥔다."},
]


class ModeSelectScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.index = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            from .title import TitleScene
            self.next_scene = TitleScene(self.app)
        elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
            self.index = (self.index - 1) % len(MODES)
            sfx.play("move")
        elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
            self.index = (self.index + 1) % len(MODES)
            sfx.play("move")
        elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            sfx.play("select")
            key = MODES[self.index]["key"]
            self.app.mode = "game" if key == "vs" else key
            self.app.two_player = (key == "vs")
            from .team_select import TeamSelectScene
            self.next_scene = TeamSelectScene(self.app)

    # ── 렌더 ──────────────────────────────────────────────
    def draw_playfield(self, pf):
        vgradient(pf, (0, 0, C.PF_W, C.PF_H), (14, 16, 34), (30, 40, 76), bands=10)
        # 좌우에 타자/투수 실루엣 — 두 모드의 성격을 그림으로 보여준다
        team = {"primary": (170, 60, 70), "second": (30, 30, 40),
                "accent": (240, 220, 120)}
        sprites.draw_batter(pf, 44, 214, team, swing_phase=0.55)
        sprites.draw_pitcher(pf, 278, 206, team, wind_up=0.7)

    def draw_hud(self, win):
        cx = C.WIN_W // 2
        draw_text(win, "모드 선택", (cx, 54), size=34, color=C.YELLOW,
                  bold=True, anchor="center")

        bw, bh = 620, 108
        for i, m in enumerate(MODES):
            x, y = cx - bw // 2, 128 + i * (bh + 20)
            on = (i == self.index)
            bevel_box(win, (x, y, bw, bh), (18, 20, 42) if not on else (30, 36, 72),
                      (255, 255, 255) if on else (100, 106, 140), (10, 10, 20),
                      border=3 if on else 1)
            draw_text(win, m["title"], (x + 24, y + 16), size=28,
                      color=C.YELLOW if on else (200, 205, 225), bold=True)
            draw_text(win, m["sub"], (x + 24, y + 56), size=17,
                      color=(190, 200, 225) if on else (130, 138, 168))
            draw_text(win, m["desc"], (x + 24, y + 82), size=15,
                      color=(150, 160, 190) if on else (100, 108, 138))
            if on:
                draw_text(win, "▶", (x - 24, y + bh // 2), size=26,
                          color=C.YELLOW, anchor="center")

        draw_text(win, "방향키 이동    SPACE 결정    ESC 뒤로",
                  (cx, C.WIN_H - 74), size=18, color=(180, 190, 220),
                  anchor="center")

"""타이틀 화면 — 야간 경기장 실루엣 위에 로고와 안내를 띄운다."""

import math
import pygame

from .. import config as C
from .. import sfx
from ..fonts import draw_text
from ..retro import vgradient
from .base import Scene


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        # 조명탑에서 흩날리는 반딧불 느낌의 점들 (연출용)
        self.motes = [[(i * 37) % C.PF_W, (i * 53) % 90, 0.2 + (i % 5) * 0.12]
                      for i in range(28)]

    # ── 입력 ──────────────────────────────────────────────
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                sfx.play("select")
                from .mode_select import ModeSelectScene
                self.next_scene = ModeSelectScene(self.app)
            elif event.key == pygame.K_ESCAPE:
                self.quit = True

    def update(self):
        for m in self.motes:
            m[1] += m[2]
            if m[1] > 120:
                m[1] = 0

    # ── 픽셀 아트 레이어 ──────────────────────────────────
    def draw_playfield(self, pf):
        # 밤하늘
        vgradient(pf, (0, 0, C.PF_W, 130), C.NIGHT, C.SKY_BOT, bands=10)

        # 조명탑 4기
        for tx in (34, 108, 212, 286):
            pygame.draw.rect(pf, (40, 40, 52), (tx - 2, 34, 5, 62))
            pygame.draw.rect(pf, (80, 80, 96), (tx - 12, 22, 25, 14))
            for r in range(3):
                for c in range(5):
                    lit = (self.frame // 10 + r + c) % 7 != 0   # 살짝 깜빡임
                    col = (250, 246, 200) if lit else (170, 166, 130)
                    pygame.draw.rect(pf, col, (tx - 11 + c * 5, 23 + r * 4, 3, 3))

        # 반딧불
        for x, y, _ in self.motes:
            pygame.draw.rect(pf, (230, 230, 180), (int(x), int(y), 1, 1))

        # 관중석 실루엣
        pygame.draw.rect(pf, (26, 26, 44), (0, 96, C.PF_W, 26))
        for x in range(0, C.PF_W, 4):
            h = 3 + int(2 * math.sin(x * 0.4))
            pygame.draw.rect(pf, (44, 44, 68), (x, 96 - h, 3, h))

        # 외야 잔디 (줄무늬)
        for i, y in enumerate(range(122, C.PF_H, 8)):
            col = C.TURF if i % 2 == 0 else C.TURF_DARK
            pygame.draw.rect(pf, col, (0, y, C.PF_W, 8))

        # 내야 흙 + 다이아몬드
        pygame.draw.polygon(pf, C.DIRT, [(160, 150), (238, 196), (160, 238), (82, 196)])
        pygame.draw.polygon(pf, C.LINE_WHITE,
                            [(160, 150), (238, 196), (160, 238), (82, 196)], 1)
        pygame.draw.circle(pf, C.DIRT_DARK, (160, 176), 11)
        for bx, by in ((238, 196), (160, 150), (82, 196)):
            pygame.draw.rect(pf, C.LINE_WHITE, (bx - 2, by - 2, 5, 5))
        pygame.draw.rect(pf, C.BONE, (157, 233, 7, 5))

    # ── HUD 레이어 ────────────────────────────────────────
    def draw_hud(self, win):
        cx = C.WIN_W // 2

        # 로고 — 위아래로 살짝 떠다니게
        bob = int(math.sin(self.frame * 0.05) * 4)
        draw_text(win, "KBO", (cx, 120 + bob), size=78, color=C.YELLOW,
                  bold=True, anchor="center")
        draw_text(win, "8-BIT BASEBALL", (cx, 186 + bob), size=42,
                  color=C.WHITE, bold=True, anchor="center")
        draw_text(win, "투 타 대 결", (cx, 232 + bob), size=24,
                  color=C.CYAN, anchor="center")

        # 잔디 위 텍스트가 묻히지 않도록 테두리 있는 패널 위에 올린다.
        # (반투명 띠만 깔면 잔디 위에 잘린 사각형처럼 보인다)
        pw, ph = 640, 148
        px, py = (C.WIN_W - pw) // 2, C.WIN_H - 186
        box = pygame.Surface((pw, ph), pygame.SRCALPHA)
        box.fill((*C.PANEL_BG, 232))
        win.blit(box, (px, py))
        pygame.draw.rect(win, C.PANEL_EDGE, (px, py, pw, ph), 2)

        # 시작 안내 (깜빡임)
        if (self.frame // 26) % 2 == 0:
            draw_text(win, "SPACE 를 눌러 시작", (cx, py + 34),
                      size=28, color=(200, 220, 255), bold=True, anchor="center")

        draw_text(win, C.CONTROL_HINT, (cx, py + 84),
                  size=17, color=(150, 160, 195), anchor="center")
        draw_text(win, "v0.1  Phase 1 — 투타 대결",
                  (cx, py + 116), size=15, color=(110, 118, 155), anchor="center")

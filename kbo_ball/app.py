"""
게임 루프와 앱 전역 상태.

렌더 파이프라인
---------------
  1) 씬이 320x240 플레이필드에 픽셀 아트를 그린다
  2) 플레이필드를 창 크기로 정수배 확대해 올린다 (nearest-neighbor)
  3) 씬이 창 해상도에 한글 HUD를 직접 그린다
  4) 스캔라인 오버레이를 덮는다 (F1로 토글)
"""

import sys
import pygame

from . import config as C
from . import retro, sfx
from .scenes.title import TitleScene


class App:
    def __init__(self):
        pygame.init()
        sfx.init()

        self.screen = pygame.display.set_mode((C.WIN_W, C.WIN_H))
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()

        self.playfield = retro.new_playfield()
        self.scanlines_on = True
        self.running = True

        # ── 씬 간 공유 상태 ───────────────────────────────
        self.my_team = None
        self.opp_team = None
        self.lineup = []
        self.pitcher = None

        self.scene = TitleScene(self)

    # ── 메인 루프 ─────────────────────────────────────────
    def run(self):
        while self.running:
            self._handle_events()
            self.scene.update()
            self.scene.tick()
            self._draw()
            self._switch_scene()
            self.clock.tick(C.FPS)

        pygame.quit()
        sys.exit(0)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                self.scanlines_on = not self.scanlines_on
                continue
            self.scene.handle_event(event)

    def _draw(self):
        # 1) 픽셀 아트 레이어
        self.playfield.fill(C.BLACK)
        self.scene.draw_playfield(self.playfield)

        # 2) 확대 (씬이 화면 흔들림을 요구하면 오프셋 적용)
        self.screen.fill(C.BLACK)
        ox, oy = (self.scene.playfield_offset()
                  if hasattr(self.scene, "playfield_offset") else (0, 0))
        scaled = pygame.transform.scale(self.playfield, (C.WIN_W, C.WIN_H))
        self.screen.blit(scaled, (ox * C.SCALE, oy * C.SCALE))

        # 3) HUD 레이어
        self.scene.draw_hud(self.screen)

        # 4) 스캔라인
        if self.scanlines_on:
            self.screen.blit(retro.scanline_overlay(), (0, 0))

        pygame.display.flip()

    def _switch_scene(self):
        if self.scene.quit:
            self.running = False
        elif self.scene.next_scene is not None:
            self.scene = self.scene.next_scene


def main():
    App().run()

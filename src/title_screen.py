import pygame
import math
from src.utils import get_font

# 게임 시작 전에 보이는 타이틀 화면
class TitleScreen:
    def __init__(self, screen_width, screen_height):
        self.screen_width  = screen_width
        self.screen_height = screen_height
        self.frame = 0
        self.done  = False  # True가 되면 메뉴로 넘어감

        self.font_title    = get_font(40, bold=True)  # "Full Acceleration"
        self.font_subtitle = get_font(22)              # "with Sean Kim" — 작게
        self.font_sub      = get_font(22, bold=True)
        self.font_press    = get_font(26)
        self.font_hint     = get_font(18)

        # 배경에서 달리는 장식용 자동차들
        self.cars = [
            {"x": -60,  "y": 200, "speed": 3.8, "color": (220, 30,  30),  "w": 58, "h": 28},
            {"x": -160, "y": 340, "speed": 2.6, "color": (30,  100, 220), "w": 52, "h": 24},
            {"x": -260, "y": 460, "speed": 4.4, "color": (220, 200, 0),   "w": 62, "h": 26},
            {"x": -380, "y": 150, "speed": 3.2, "color": (30,  180, 60),  "w": 55, "h": 24},
            {"x": -500, "y": 520, "speed": 2.9, "color": (200, 200, 200), "w": 50, "h": 22},
        ]

        # 별 파티클 (배경 장식)
        import random
        self.stars = [
            {"x": random.randint(0, screen_width),
             "y": random.randint(0, screen_height),
             "r": random.randint(1, 3),
             "phase": random.randint(0, 60)}
            for _ in range(40)
        ]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.done = True

    def update(self):
        self.frame += 1
        # 자동차 이동
        for car in self.cars:
            car["x"] += car["speed"]
            if car["x"] > self.screen_width + 100:
                car["x"] = -car["w"] - 10

    def draw(self, screen):
        # ── 배경 ────────────────────────────────────────────
        screen.fill((5, 8, 25))

        # 도로 줄무늬 효과 (배경)
        stripe_h = 30
        y = (self.frame * 3) % (stripe_h * 2) - stripe_h * 2
        while y < self.screen_height:
            pygame.draw.rect(screen, (12, 16, 38), (0, y, self.screen_width, stripe_h))
            y += stripe_h * 2

        # 별 (깜빡임)
        for s in self.stars:
            alpha = int(128 + 127 * math.sin(math.radians((self.frame + s["phase"]) * 4)))
            bright = max(80, alpha)
            pygame.draw.circle(screen, (bright, bright, bright), (s["x"], s["y"]), s["r"])

        # 달리는 자동차들
        for car in self.cars:
            self._draw_small_car(screen, int(car["x"]), int(car["y"]),
                                 car["color"], car["w"], car["h"])

        # ── 제목 박스 ────────────────────────────────────────
        bw, bh = 440, 140
        bx = self.screen_width // 2 - bw // 2
        by = 80
        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box.fill((0, 0, 0, 190))
        screen.blit(box, (bx, by))
        # 황금색 테두리 (두께 3)
        pygame.draw.rect(screen, (255, 200, 0), (bx, by, bw, bh), 3, border_radius=12)

        # 게임 제목 두 줄
        t1 = self.font_title.render("Full Acceleration", True, (255, 220, 0))
        t2 = self.font_subtitle.render("with Sean Kim", True, (220, 220, 220))
        screen.blit(t1, (self.screen_width // 2 - t1.get_width() // 2, by + 18))
        screen.blit(t2, (self.screen_width // 2 - t2.get_width() // 2, by + 78))

        # ── "시작" 안내 (깜빡임) ────────────────────────────
        if (self.frame // 22) % 2 == 0:
            press = self.font_press.render("SPACE 또는 ENTER를 눌러 시작", True, (180, 200, 255))
            screen.blit(press, (self.screen_width // 2 - press.get_width() // 2, 260))

        # ── 부제 ────────────────────────────────────────────
        sub = self.font_sub.render("2026 F1 드라이버와 함께하는 레이싱!", True, (140, 190, 255))
        screen.blit(sub, (self.screen_width // 2 - sub.get_width() // 2, 320))

        # ── 조작법 안내 ─────────────────────────────────────
        hint = self.font_hint.render("← → / A D 이동   F11 전체화면   ESC 종료", True, (100, 100, 160))
        screen.blit(hint, (self.screen_width // 2 - hint.get_width() // 2, 370))

        # ── 하단 버전 표시 ───────────────────────────────────
        ver = self.font_hint.render("v1.0  |  Pygame Edition", True, (60, 60, 90))
        screen.blit(ver, (self.screen_width // 2 - ver.get_width() // 2, self.screen_height - 26))

    def _draw_small_car(self, screen, x, y, color, w, h):
        # 가로로 달리는 작은 자동차 (배경 장식)
        dark_c = tuple(max(0, v - 60) for v in color)
        pygame.draw.rect(screen, color, (x, y, w, h), border_radius=5)
        # 지붕
        pygame.draw.rect(screen, dark_c, (x + 8, y + 3, w - 16, h - 8), border_radius=4)
        # 앞 유리
        pygame.draw.rect(screen, (150, 200, 255), (x + w - 14, y + 4, 10, h - 10), border_radius=2)
        # 뒷 유리
        pygame.draw.rect(screen, (150, 200, 255), (x + 4, y + 4, 10, h - 10), border_radius=2)
        # 바퀴 4개
        for wx, wy in [(x + 6, y - 4), (x + w - 12, y - 4),
                       (x + 6, y + h - 2), (x + w - 12, y + h - 2)]:
            pygame.draw.circle(screen, (20, 20, 20), (wx, wy), 5)

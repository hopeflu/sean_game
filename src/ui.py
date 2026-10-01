import pygame
from src.data import TIRE_COLORS

# 게임 화면 위에 표시되는 정보창(HUD) 클래스
class HUD:
    HEART_ON  = (255, 50, 80)   # 남은 목숨 색깔
    HEART_OFF = (70, 70, 70)    # 잃은 목숨 색깔

    def __init__(self, screen_width, screen_height):
        self.screen_width  = screen_width
        self.screen_height = screen_height

        self.font_big   = pygame.font.SysFont("malgungothic", 30, bold=True)
        self.font_small = pygame.font.SysFont("malgungothic", 20)
        self.font_tiny  = pygame.font.SysFont("malgungothic", 17)

    def draw(self, screen, lives, score, consecutive, racer_name, tire,
             booster_active, speed):
        # ── 상단 HUD 바 ──────────────────────────────────────
        hud = pygame.Surface((self.screen_width, 54), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 150))
        screen.blit(hud, (0, 0))

        # 하트 (목숨) — 최대 5개
        for i in range(5):
            col = self.HEART_ON if i < lives else self.HEART_OFF
            self._draw_heart(screen, 12 + i * 30, 10, 20, col)

        # 점수 (오른쪽)
        sc_text = self.font_big.render(f"{score // 10:,}", True, (255, 255, 100))
        screen.blit(sc_text, (self.screen_width - sc_text.get_width() - 10, 8))

        # 속도 표시 (점수 왼쪽)
        spd_text = self.font_tiny.render(f"SPD {speed:.0f}", True, (180, 220, 180))
        screen.blit(spd_text, (self.screen_width - spd_text.get_width() - 16, 38))

        # ── 부스터 게이지 ─────────────────────────────────────
        self._draw_boost_gauge(screen, consecutive, booster_active)

        # ── 하단 정보 바 ─────────────────────────────────────
        bot = pygame.Surface((self.screen_width, 28), pygame.SRCALPHA)
        bot.fill((0, 0, 0, 130))
        screen.blit(bot, (0, self.screen_height - 28))

        racer_t = self.font_tiny.render(f"Driver: {racer_name}", True, (200, 230, 255))
        screen.blit(racer_t, (8, self.screen_height - 22))

        tc      = TIRE_COLORS.get(tire, (255, 255, 255))
        tire_t  = self.font_tiny.render(f"Tire: {tire}", True, tc)
        screen.blit(tire_t, (self.screen_width - tire_t.get_width() - 8,
                              self.screen_height - 22))

    def _draw_heart(self, screen, x, y, size, color):
        # 하트: 원 두 개 + 삼각형
        r = size // 4
        pygame.draw.circle(screen, color, (x + r,              y + r), r)
        pygame.draw.circle(screen, color, (x + size // 2 + r,  y + r), r)
        pts = [
            (x,              y + r + 2),
            (x + size,       y + r + 2),
            (x + size // 2,  y + size),
        ]
        pygame.draw.polygon(screen, color, pts)

    def _draw_boost_gauge(self, screen, consecutive, booster_active):
        bx, by   = 10, 58
        bw, bh   = 170, 11
        max_cons = 10  # 부스터 발동까지 필요한 연속 피하기 횟수

        # 배경
        pygame.draw.rect(screen, (40, 40, 40), (bx, by, bw, bh), border_radius=5)

        # 채움 (0~1 비율)
        fill = min(consecutive / max_cons, 1.0)
        if fill > 0:
            fill_c = (100, 255, 120) if booster_active else (255, 200, 0)
            pygame.draw.rect(screen, fill_c, (bx, by, int(bw * fill), bh), border_radius=5)

        # 테두리
        pygame.draw.rect(screen, (180, 180, 180), (bx, by, bw, bh), 2, border_radius=5)

        # 라벨
        label_c = (120, 255, 140) if booster_active else (255, 230, 100)
        label   = self.font_tiny.render("BOOST", True, label_c)
        screen.blit(label, (bx + bw + 5, by - 1))

        # 현재 연속 횟수
        cnt = self.font_tiny.render(f"{consecutive}/10", True, (200, 200, 200))
        screen.blit(cnt, (bx + bw + 45, by - 1))

import math
import pygame
from src.data  import TIRE_COLORS
from src.utils import get_font

# 게임 화면 위에 표시되는 정보창(HUD) 클래스
class HUD:
    HEART_ON  = (255, 50, 80)   # 남은 목숨 색깔
    HEART_OFF = (70, 70, 70)    # 잃은 목숨 색깔

    def __init__(self, screen_width, screen_height):
        self.screen_width  = screen_width
        self.screen_height = screen_height

        self.font_big   = get_font(30, bold=True)
        self.font_small = get_font(20)
        self.font_tiny  = get_font(17)

    def draw(self, screen, lives, score, consecutive, racer_name, tire,
             booster_active, speed, circuit_img=None, circuit_name="",
             circuit_pos=0.0, circuit_lap=1):
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

        # ── 서킷 미니맵 (우측 하단) ──────────────────────────
        if circuit_img:
            self._draw_minimap(screen, circuit_img, circuit_name,
                               circuit_pos, circuit_lap)

    def _draw_minimap(self, screen, circuit_img, circuit_name,
                      circuit_pos=0.0, circuit_lap=1):
        """서킷 이미지를 우측 하단에 미니맵으로 표시 + 현재 위치 점"""
        iw = circuit_img.get_width()
        ih = circuit_img.get_height()
        mx = self.screen_width  - iw - 6
        my = self.screen_height - ih - 32

        # 반투명 검정 배경
        bg = pygame.Surface((iw + 4, ih + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        screen.blit(bg, (mx - 2, my - 2))

        # 이미지
        screen.blit(circuit_img, (mx, my))

        # ── 현재 위치 표시 점 ────────────────────────────────
        # circuit_pos (0~1)을 타원 궤도로 변환 → 서킷 둘레를 따라가는 근사값
        angle = circuit_pos * 2 * math.pi - math.pi / 2   # 위쪽(12시)에서 시작
        rx = iw * 0.36   # 타원 x 반지름
        ry = ih * 0.36   # 타원 y 반지름
        cx = mx + iw // 2
        cy = my + ih // 2
        dot_x = int(cx + rx * math.cos(angle))
        dot_y = int(cy + ry * math.sin(angle))

        # 점 그리기 (빨간 점 + 흰 테두리)
        pygame.draw.circle(screen, (255, 255, 255), (dot_x, dot_y), 6)
        pygame.draw.circle(screen, (255, 50, 50),   (dot_x, dot_y), 5)

        # 테두리
        pygame.draw.rect(screen, (255, 200, 0),
                         (mx - 2, my - 2, iw + 4, ih + 4), 2, border_radius=3)

        # 랩 카운터 + 진행도 (이미지 위)
        lap_s = self.font_tiny.render(f"LAP {circuit_lap}  {int(circuit_pos*100)}%",
                                      True, (255, 220, 100))
        screen.blit(lap_s, (mx, my - 16))

        # 서킷 이름 (이미지 아래)
        short = circuit_name.replace("Circuit", "").replace("Grand Prix", "").strip()
        if len(short) > 22:
            short = short[:21] + "…"
        name_s = self.font_tiny.render(short, True, (220, 220, 180))
        screen.blit(name_s, (mx + iw // 2 - name_s.get_width() // 2,
                              my + ih + 2))

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

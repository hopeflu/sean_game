import pygame
import math

# 10개 연속 피하기 성공 시 등장하는 부스터 아이템
class Booster:
    SIZE = 38  # 전체 크기

    def __init__(self, x, y):
        self.x         = float(x)
        self.y         = float(y)
        self.speed     = 2.5    # 천천히 내려옴
        self.frame     = 0
        self.collected = False   # 수집 여부

        self.rect = pygame.Rect(int(self.x), int(self.y), self.SIZE, self.SIZE)

    def update(self):
        self.y += self.speed
        self.frame += 1
        self.rect.y = int(self.y)
        self.rect.x = int(self.x)

    def is_off_screen(self, screen_height):
        return self.y > screen_height

    def draw(self, screen):
        if self.collected:
            return

        cx = int(self.x) + self.SIZE // 2
        cy = int(self.y) + self.SIZE // 2

        # 바깥 빛나는 원 (크기가 살짝 맥박처럼 변함)
        glow_r = int(20 + 4 * math.sin(math.radians(self.frame * 8)))
        pygame.draw.circle(screen, (255, 230, 0), (cx, cy), glow_r + 4)
        pygame.draw.circle(screen, (255, 170, 0), (cx, cy), glow_r)

        # 별 모양 (5각 별)
        angle_off = self.frame * 4  # 별이 천천히 회전
        self._draw_star(screen, cx, cy, glow_r - 2, glow_r // 2 + 2,
                        angle_off, (255, 255, 120))

        # 중심 번쩍이는 점
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 5)

    def _draw_star(self, screen, cx, cy, r_out, r_in, angle_off, color):
        # 5각 별: 꼭짓점 10개 (바깥 5 + 안쪽 5 교대)
        points = []
        for i in range(10):
            angle = math.radians(angle_off + i * 36 - 90)
            r = r_out if i % 2 == 0 else r_in
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        if len(points) >= 3:
            pygame.draw.polygon(screen, color, points)

import pygame
import random

# 도로를 달리는 일반 차량 (장애물) 클래스
class Obstacle:
    WIDTH  = 46
    HEIGHT = 76

    # 일반 차량 색깔 목록 (레이싱카와 구분되는 평범한 색)
    COLORS = [
        (160, 160, 160),  # 회색
        (100, 80,  60),   # 갈색
        (60,  80,  140),  # 남색
        (140, 130, 60),   # 카키
        (100, 60,  100),  # 자주색
        (180, 100, 40),   # 주황 갈색
    ]

    def __init__(self, speed, lane_x):
        # lane_x: 해당 차선의 x 좌표 (트랙에서 계산해서 넘겨줌)
        self.x     = float(lane_x)
        self.y     = float(-self.HEIGHT - random.randint(0, 40))  # 화면 위에서 등장
        self.speed = speed
        self.color = random.choice(self.COLORS)

        # 충돌 판정 rect (차 몸통 기준)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.WIDTH, self.HEIGHT)

        # True가 되면 플레이어를 피한 것으로 처리 (재충돌 방지)
        self.passed = False

    def update(self):
        # 아래로 내려오기
        self.y += self.speed
        self.rect.y = int(self.y)

    def is_off_screen(self, screen_height):
        return self.y > screen_height

    def draw(self, screen):
        x, y = int(self.x), int(self.y)
        c     = self.color
        dark  = (20, 20, 20)

        # 차 앞범퍼 (아래쪽)
        pygame.draw.rect(screen, dark, (x + 4, y + self.HEIGHT - 10, self.WIDTH - 8, 8), border_radius=3)

        # 차 몸통
        pygame.draw.rect(screen, c, (x + 2, y + 8, self.WIDTH - 4, self.HEIGHT - 16), border_radius=6)

        # 지붕 (약간 어두운 색)
        roof_c = tuple(max(0, v - 50) for v in c)
        pygame.draw.rect(screen, roof_c, (x + 8, y + 18, self.WIDTH - 16, self.HEIGHT - 40), border_radius=4)

        # 뒷 유리창 (위쪽 — 이 차는 위에서 내려오므로 "뒤"는 위)
        pygame.draw.rect(screen, (170, 210, 255), (x + 9, y + 10, self.WIDTH - 18, 14), border_radius=3)

        # 앞 유리창 (아래쪽 — 플레이어 방향)
        pygame.draw.rect(screen, (170, 210, 255), (x + 9, y + self.HEIGHT - 28, self.WIDTH - 18, 16), border_radius=3)

        # 헤드라이트 두 개 (차 앞쪽)
        pygame.draw.rect(screen, (255, 255, 180), (x + 6,  y + self.HEIGHT - 14, 10, 6), border_radius=2)
        pygame.draw.rect(screen, (255, 255, 180), (x + self.WIDTH - 16, y + self.HEIGHT - 14, 10, 6), border_radius=2)

        # 바퀴 4개 (검정 사각형)
        for wx, wy in [
            (x - 7,              y + 10),
            (x + self.WIDTH - 3, y + 10),
            (x - 7,              y + self.HEIGHT - 28),
            (x + self.WIDTH - 3, y + self.HEIGHT - 28),
        ]:
            pygame.draw.rect(screen, dark, (wx, wy, 10, 20), border_radius=3)

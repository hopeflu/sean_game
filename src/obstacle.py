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

    def __init__(self, speed, lane_x, lane_index, can_change_lane=False):
        # lane_index: 차선 번호(0·1·2) — 도로가 이동해도 같은 차선에 머무름
        self.lane_index = lane_index
        self.x     = float(lane_x)
        self.y     = float(-self.HEIGHT - random.randint(0, 40))
        self.speed = speed
        self.color = random.choice(self.COLORS)

        # 충돌 판정 rect
        self.rect = pygame.Rect(int(self.x), int(self.y), self.WIDTH, self.HEIGHT)

        # True가 되면 플레이어를 피한 것으로 처리 (재충돌 방지)
        self.passed = False

        # ── 차선 변경 시스템 (어려움·익스트림 난이도) ─────────
        self.can_change_lane  = can_change_lane
        self.changing_lane    = False            # 현재 차선 변경 중인지
        self.change_progress  = 0.0             # 0.0(시작) → 1.0(완료)
        self.target_lane_idx  = lane_index      # 목표 차선 번호
        # 첫 번째 차선 변경까지 대기 시간 (프레임)
        self.change_timer = random.randint(60, 160) if can_change_lane else 9999

        # 방향지시등 깜빡임 프레임
        self.blinker_frame = 0

    def update(self, lane_x, lane_xs=None):
        """lane_x: 현재 차선 x,  lane_xs: 전체 차선 x 목록 (차선 변경 시 필요)"""
        if self.can_change_lane and lane_xs is not None:
            self.change_timer -= 1
            self.blinker_frame += 1

            # 차선 변경 시작 조건: 타이머 만료 + 현재 변경 중 아님
            if self.change_timer <= 0 and not self.changing_lane:
                candidates = [i for i in [self.lane_index - 1, self.lane_index + 1]
                              if 0 <= i < len(lane_xs)]
                if candidates:
                    self.target_lane_idx = random.choice(candidates)
                    self.changing_lane   = True
                    self.change_progress = 0.0
                self.change_timer = random.randint(100, 240)

            if self.changing_lane:
                self.change_progress += 0.035   # 약 28프레임에 걸쳐 이동
                if self.change_progress >= 1.0:
                    self.lane_index      = self.target_lane_idx
                    self.changing_lane   = False
                    self.change_progress = 0.0

                # 현재 차선과 목표 차선 사이를 부드럽게 보간
                src_x = lane_xs[self.lane_index]
                tgt_x = lane_xs[self.target_lane_idx]
                self.x = src_x + (tgt_x - src_x) * min(self.change_progress, 1.0)
            else:
                self.x = float(lane_x)
        else:
            self.x = float(lane_x)

        self.y += self.speed
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def is_off_screen(self, screen_height):
        return self.y > screen_height

    _MARGIN = 10  # 바퀴 돌출분을 담는 여백

    def draw(self, screen, scale: float = 1.0):
        """scale < 1.0: 멀리 있어서 작게 보임 (원근 효과)"""
        if abs(scale - 1.0) < 0.02:
            # 1.0 배율이면 바로 화면에 그림 (빠름)
            self._render(screen, int(self.x), int(self.y))
        else:
            # 임시 투명 surface에 그리고 스케일 적용
            M  = self._MARGIN
            W, H = self.WIDTH, self.HEIGHT
            temp = pygame.Surface((W + M * 2, H), pygame.SRCALPHA)
            self._render(temp, M, 0)

            sw = max(1, int((W + M * 2) * scale))
            sh = max(1, int(H * scale))
            scaled = pygame.transform.smoothscale(temp, (sw, sh))

            # 원래 rect 중심에 맞춰 배치
            cx = int(self.x) + W // 2
            cy = int(self.y) + H // 2
            screen.blit(scaled, (cx - sw // 2 + int(M * scale), cy - sh // 2))

    def _render(self, surface, x, y):
        """surface의 (x, y)를 기준으로 차를 그린다"""
        c    = self.color
        dark = (20, 20, 20)
        W, H = self.WIDTH, self.HEIGHT

        # 차 앞범퍼
        pygame.draw.rect(surface, dark, (x + 4, y + H - 10, W - 8, 8), border_radius=3)
        # 차 몸통
        pygame.draw.rect(surface, c, (x + 2, y + 8, W - 4, H - 16), border_radius=6)
        # 지붕
        roof_c = tuple(max(0, v - 50) for v in c)
        pygame.draw.rect(surface, roof_c, (x + 8, y + 18, W - 16, H - 40), border_radius=4)
        # 뒷 유리
        pygame.draw.rect(surface, (170, 210, 255), (x + 9, y + 10, W - 18, 14), border_radius=3)
        # 앞 유리
        pygame.draw.rect(surface, (170, 210, 255), (x + 9, y + H - 28, W - 18, 16), border_radius=3)
        # 헤드라이트
        pygame.draw.rect(surface, (255, 255, 180), (x + 6,     y + H - 14, 10, 6), border_radius=2)
        pygame.draw.rect(surface, (255, 255, 180), (x + W - 16, y + H - 14, 10, 6), border_radius=2)
        # 바퀴 4개
        for wx, wy in [
            (x - 7,      y + 10),
            (x + W - 3,  y + 10),
            (x - 7,      y + H - 28),
            (x + W - 3,  y + H - 28),
        ]:
            pygame.draw.rect(surface, dark, (wx, wy, 10, 20), border_radius=3)
        # 방향지시등 (차선 변경 중 노란 깜빡이)
        if self.changing_lane and (self.blinker_frame // 8) % 2 == 0:
            bx = (x + W - 6) if self.target_lane_idx > self.lane_index else (x + 2)
            pygame.draw.rect(surface, (255, 200, 0), (bx, y + 14, 4, 8), border_radius=1)

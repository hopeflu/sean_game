import pygame

# 플레이어가 조종하는 F1 레이싱카 클래스
class Player:
    WIDTH  = 40   # 차 너비 (픽셀)
    HEIGHT = 90   # 차 높이 (픽셀)

    def __init__(self, screen_width, screen_height, color, road_center_x, road_width):
        self.screen_width  = screen_width
        self.screen_height = screen_height
        self.color         = color  # 선택한 차 색깔

        # 화면 아래쪽 도로 중앙에 배치
        self.x = float(road_center_x - self.WIDTH // 2)
        self.y = float(screen_height - self.HEIGHT - 35)

        self.speed = 6  # 좌우 이동 속도 (픽셀/프레임)

        # 충돌 판정용 사각형 (실제 차 몸통보다 살짝 작게)
        self.rect = pygame.Rect(int(self.x) + 4, int(self.y) + 10,
                                self.WIDTH - 8, self.HEIGHT - 20)

        # 무적 상태 관련 (충돌 후 잠시 무적)
        self.invincible_timer = 0
        self.flash_timer      = 0

    def move(self, direction, road_left, road_right):
        # direction: -1 왼쪽, +1 오른쪽
        self.x += direction * self.speed
        # 도로 경계 안에서만 이동 가능
        self.x = max(float(road_left), min(self.x, float(road_right - self.WIDTH)))
        self._sync_rect()

    def clamp_to_road(self, road_left, road_right):
        # 트랙이 커브를 그릴 때 도로 밖으로 밀려나지 않도록 클램핑
        self.x = max(float(road_left), min(self.x, float(road_right - self.WIDTH)))
        self._sync_rect()

    def get_hit(self):
        # 장애물과 충돌했을 때 호출
        # 무적 상태가 아니면 True(데미지) 반환 후 무적 시작
        if self.invincible_timer <= 0:
            self.invincible_timer = 90  # 약 1.5초(90프레임) 무적
            return True
        return False  # 이미 무적 → 데미지 없음

    def update(self):
        # 무적 타이머 감소
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            self.flash_timer += 1
        else:
            self.flash_timer = 0

    def _sync_rect(self):
        # 충돌 rect를 실제 위치에 맞게 업데이트 (몸통 안쪽 기준)
        self.rect.x = int(self.x) + 4
        self.rect.y = int(self.y) + 10

    def is_visible(self):
        # 무적 중에는 5프레임마다 깜빡임
        if self.invincible_timer > 0:
            return (self.flash_timer // 5) % 2 == 0
        return True

    def draw(self, screen):
        if not self.is_visible():
            return

        x, y = int(self.x), int(self.y)
        c      = self.color
        dark_c = tuple(max(0, v - 70) for v in c)   # 어두운 버전
        silver = (190, 190, 200)
        dark   = (25, 25, 25)
        white  = (255, 255, 255)

        # ── 리어 윙 (차 뒤, y+HEIGHT 근처) ──────────────────
        pygame.draw.rect(screen, silver,
                         (x - 12, y + self.HEIGHT - 18, self.WIDTH + 24, 9),
                         border_radius=3)

        # ── 사이드포드 (몸통 좌우 돌출부) ──────────────────
        pygame.draw.rect(screen, dark_c, (x - 7, y + 22, 9, 44), border_radius=3)
        pygame.draw.rect(screen, dark_c, (x + self.WIDTH - 2, y + 22, 9, 44), border_radius=3)

        # ── 메인 바디 ───────────────────────────────────────
        pygame.draw.rect(screen, c,
                         (x + 4, y + 8, self.WIDTH - 8, self.HEIGHT - 16),
                         border_radius=7)

        # 바디 하이라이트 (위쪽 밝은 선)
        highlight = tuple(min(255, v + 60) for v in c)
        pygame.draw.rect(screen, highlight, (x + 8, y + 10, self.WIDTH - 16, 4), border_radius=2)

        # ── 코크핏 (운전석) ─────────────────────────────────
        pygame.draw.ellipse(screen, dark,
                            (x + 9, y + 33, self.WIDTH - 18, 26))
        # 헬멧
        pygame.draw.ellipse(screen, white,
                            (x + 12, y + 36, self.WIDTH - 24, 18))
        # 헬멧 바이저 (어두운 색)
        pygame.draw.ellipse(screen, (80, 80, 200),
                            (x + 15, y + 40, self.WIDTH - 30, 10))

        # ── 노즈 콘 (앞부분 삼각형) ─────────────────────────
        nose_pts = [
            (x + self.WIDTH // 2, y),         # 꼭대기
            (x + 9,               y + 12),    # 왼쪽
            (x + self.WIDTH - 9,  y + 12),    # 오른쪽
        ]
        pygame.draw.polygon(screen, c, nose_pts)

        # ── 프론트 윙 (앞 날개) ─────────────────────────────
        pygame.draw.rect(screen, silver,
                         (x - 10, y + 4, self.WIDTH + 20, 7),
                         border_radius=2)

        # ── 장식선 (차 번호 위치) ────────────────────────────
        pygame.draw.rect(screen, white, (x + 13, y + 14, self.WIDTH - 26, 3))

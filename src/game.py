import pygame
import random
from src.player   import Player
from src.obstacle import Obstacle
from src.track    import Track
from src.booster  import Booster
from src.ui       import HUD
from src.data     import DIFFICULTIES, CAR_COLORS, TRACKS

# 게임 플레이 전체를 관리하는 클래스
class Game:
    STATE_PLAYING  = "playing"
    STATE_GAMEOVER = "gameover"

    MAX_LIVES         = 5   # 시작 목숨 수
    BOOSTER_THRESHOLD = 10  # 연속 피하기 몇 번에 부스터 등장

    def __init__(self, screen_width, screen_height, selections):
        self.screen_width  = screen_width
        self.screen_height = screen_height

        # ── 선택된 설정 불러오기 ─────────────────────────────
        diff_name = selections.get("difficulty", "보통")
        diff      = DIFFICULTIES[diff_name]
        self.obstacle_speed  = float(diff["obstacle_speed"])
        self.spawn_interval  = float(diff["spawn_interval"])
        self.speed_inc       = float(diff["speed_inc"])

        car_color_name = selections.get("car", "빨강")
        car_color      = CAR_COLORS[car_color_name]

        self.racer_name = selections.get("racer", "Max Verstappen")
        self.tire       = selections.get("tire",  "미디엄")

        track_name = selections.get("track", "완전 직선 트랙")
        track_data = next(t for t in TRACKS if t["name"] == track_name)

        # ── 트랙 생성 ────────────────────────────────────────
        self.track = Track(track_data, screen_width, screen_height)

        # ── 플레이어 생성 ────────────────────────────────────
        road_left, road_right = self.track.get_road_bounds()
        road_center = (road_left + road_right) // 2
        road_width  = road_right - road_left
        self.player = Player(screen_width, screen_height, car_color,
                             road_center, road_width)

        # ── HUD 생성 ─────────────────────────────────────────
        self.hud = HUD(screen_width, screen_height)

        # ── 게임 상태 변수 ───────────────────────────────────
        self.state      = self.STATE_PLAYING
        self.lives      = self.MAX_LIVES
        self.score      = 0
        self.frame      = 0
        self.obstacles  = []
        self.boosters   = []
        self.consecutive_dodge = 0   # 연속 피한 장애물 수
        self.booster_active    = False

        # 폰트 (게임 오버 화면용)
        self.font_big   = pygame.font.SysFont("malgungothic", 54, bold=True)
        self.font_mid   = pygame.font.SysFont("malgungothic", 30)
        self.font_small = pygame.font.SysFont("malgungothic", 22)

    # ── 키보드 입력 처리 ─────────────────────────────────────
    def handle_input(self, keys):
        if self.state != self.STATE_PLAYING:
            return
        road_left, road_right = self.track.get_road_bounds()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.move(-1, road_left, road_right)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.move(1, road_left, road_right)

    # ── 이벤트 처리 ──────────────────────────────────────────
    def handle_event(self, event):
        if self.state == self.STATE_GAMEOVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return "restart"  # 메인 루프에 재시작 신호
        return None

    # ── 매 프레임 게임 상태 업데이트 ──────────────────────────
    def update(self):
        if self.state != self.STATE_PLAYING:
            return

        self.frame += 1
        self.score += 1  # 1프레임 = 1점

        # 트랙 업데이트 (도로 커브 이동)
        self.track.update(self.obstacle_speed)

        # 플레이어 업데이트 (무적 타이머)
        self.player.update()

        # 커브로 인해 도로 밖으로 밀려났을 때 클램핑
        road_left, road_right = self.track.get_road_bounds()
        self.player.clamp_to_road(road_left, road_right)

        # 150프레임마다 속도 & 스폰 간격 조정 (점점 어려워짐)
        if self.frame % 150 == 0:
            self.obstacle_speed = min(self.obstacle_speed + self.speed_inc, 22.0)
            self.spawn_interval = max(self.spawn_interval - 4.0, 28.0)

        # 장애물 생성
        if self.frame % int(self.spawn_interval) == 0:
            lane_xs = self.track.get_lane_xs()
            lx      = random.choice(lane_xs)
            self.obstacles.append(Obstacle(self.obstacle_speed, lx))

        # 장애물 업데이트 + 충돌 + 피하기 카운팅
        self._update_obstacles()

        # 부스터 업데이트
        self._update_boosters()

    def _update_obstacles(self):
        new_obstacles = []
        for obs in self.obstacles:
            obs.update()

            # 충돌 확인 (아직 패스 처리 안 된 장애물만)
            if not obs.passed and self.player.rect.colliderect(obs.rect):
                obs.passed = True  # 이 장애물로 더 이상 충돌 없음
                hit = self.player.get_hit()
                if hit:
                    self.lives -= 1
                    self.consecutive_dodge = 0  # 연속 피하기 리셋
                    if self.lives <= 0:
                        self.state = self.STATE_GAMEOVER

            # 플레이어보다 아래로 내려갔으면 성공적으로 피한 것
            if (not obs.passed
                    and obs.y > self.player.y + self.player.HEIGHT):
                obs.passed = True
                self.consecutive_dodge += 1
                # 10개 연속 피하면 부스터 등장
                if (self.consecutive_dodge >= self.BOOSTER_THRESHOLD
                        and not self.boosters):
                    self._spawn_booster()
                    self.consecutive_dodge = 0

            # 화면 밖으로 나간 장애물은 제거
            if not obs.is_off_screen(self.screen_height):
                new_obstacles.append(obs)

        self.obstacles = new_obstacles

    def _update_boosters(self):
        new_boosters = []
        for b in self.boosters:
            b.update()

            # 플레이어가 부스터를 수집했는지 확인
            if self.player.rect.colliderect(b.rect):
                b.collected = True
                self.score += 5000        # +500점 표시 (score//10)
                self.booster_active = True

            # 화면 밖으로 나가거나 수집됐으면 제거
            if not b.is_off_screen(self.screen_height) and not b.collected:
                new_boosters.append(b)

        self.boosters = new_boosters
        if not self.boosters:
            self.booster_active = False

    def _spawn_booster(self):
        road_left, road_right = self.track.get_road_bounds()
        bx = random.randint(road_left + 20, road_right - Booster.SIZE - 20)
        self.boosters.append(Booster(float(bx), -50.0))

    # ── 화면 그리기 ──────────────────────────────────────────
    def draw(self, screen):
        # 트랙
        self.track.draw(screen)

        # 장애물
        for obs in self.obstacles:
            obs.draw(screen)

        # 부스터
        for b in self.boosters:
            b.draw(screen)

        # 플레이어
        self.player.draw(screen)

        # HUD (정보창)
        self.hud.draw(
            screen,
            lives          = self.lives,
            score          = self.score,
            consecutive    = self.consecutive_dodge,
            racer_name     = self.racer_name,
            tire           = self.tire,
            booster_active = self.booster_active,
            speed          = self.obstacle_speed,
        )

        # 게임 오버 오버레이
        if self.state == self.STATE_GAMEOVER:
            self._draw_gameover(screen)

    def _draw_gameover(self, screen):
        # 반투명 검정 오버레이
        ov = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        screen.blit(ov, (0, 0))

        # 게임 오버 텍스트
        go = self.font_big.render("GAME OVER", True, (255, 60, 60))
        screen.blit(go, (self.screen_width // 2 - go.get_width() // 2, 150))

        # 드라이버 이름
        racer = self.font_mid.render(f"Driver: {self.racer_name}", True, (200, 220, 255))
        screen.blit(racer, (self.screen_width // 2 - racer.get_width() // 2, 235))

        # 최종 점수
        sc = self.font_mid.render(f"최종 점수: {self.score // 10:,}", True, (255, 255, 100))
        screen.blit(sc, (self.screen_width // 2 - sc.get_width() // 2, 280))

        # 재시작 안내
        restart = self.font_small.render("SPACE — 메뉴로 돌아가기", True, (180, 180, 220))
        screen.blit(restart, (self.screen_width // 2 - restart.get_width() // 2, 360))

        hint = self.font_small.render("ESC — 타이틀 화면으로", True, (140, 140, 180))
        screen.blit(hint, (self.screen_width // 2 - hint.get_width() // 2, 395))

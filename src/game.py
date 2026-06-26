import os
import random
import pygame

from src.road_3d import Road3D  # SEG_LEN 상수도 사용
from src.booster import Booster
from src.ui      import HUD
from src.data    import DIFFICULTIES, CAR_COLORS, CIRCUITS
from src.utils   import get_font

_CIRCUIT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "circuit")

# ─────────────────────────────────────────────────────────────
#  Obstacle3D — Pseudo-3D 공간의 장애물 차량
# ─────────────────────────────────────────────────────────────
class Obstacle3D:
    WIDTH_WORLD  = 120   # 세계 단위 폭 (충돌 판정용)
    COLORS = [
        (160,160,160),(100,80,60),(60,80,140),
        (140,130,60),(100,60,100),(180,100,40),
    ]

    def __init__(self, z_spawn, lane, speed, can_change=False):
        self.z      = float(z_spawn)    # 플레이어로부터의 거리 (양수=앞)
        self.lane   = lane              # 0·1·2 (좌·중·우)
        self.speed  = speed
        self.passed = False
        self.color  = random.choice(self.COLORS)

        # 차선 변경
        self.can_change   = can_change
        self.change_timer = random.randint(80, 200) if can_change else 99999
        self.target_lane  = lane
        self.changing     = False
        self.change_prog  = 0.0
        self.blinker_f    = 0

        # lane_norm: -0.58=왼쪽, 0=중앙, +0.58=오른쪽
        self._lane_norms  = [-0.58, 0.0, 0.58]
        self.lane_norm    = self._lane_norms[lane]

    def update(self):
        self.z -= self.speed

        if self.can_change:
            self.change_timer -= 1
            self.blinker_f    += 1
            if self.change_timer <= 0 and not self.changing:
                cands = [l for l in [self.lane - 1, self.lane + 1] if 0 <= l <= 2]
                if cands:
                    self.target_lane = random.choice(cands)
                    self.changing    = True
                    self.change_prog = 0.0
                self.change_timer = random.randint(100, 250)

            if self.changing:
                self.change_prog += 0.035
                if self.change_prog >= 1.0:
                    self.lane    = self.target_lane
                    self.changing = False
                src = self._lane_norms[self.lane]
                tgt = self._lane_norms[self.target_lane]
                self.lane_norm = src + (tgt - src) * min(self.change_prog, 1.0)
            else:
                self.lane_norm = self._lane_norms[self.lane]

    def draw(self, screen, road: Road3D):
        pos = road.project_obstacle(self.lane_norm, self.z)
        if pos is None:
            return
        sx, sy, scale = pos

        W = max(1, int(46 * scale))
        H = max(1, int(76 * scale))
        x = sx - W // 2
        y = sy - H       # 차 하단이 sy에 오도록

        c     = self.color
        dark  = (20, 20, 20)
        roof  = tuple(max(0, v - 50) for v in c)
        glass = (170, 210, 255)

        def r(ax, ay, aw, ah, rad=0):
            pygame.draw.rect(screen, c,
                             (x + int(ax*scale), y + int(ay*scale),
                              max(1,int(aw*scale)), max(1,int(ah*scale))),
                             border_radius=max(0, int(rad*scale)))

        # 몸통
        pygame.draw.rect(screen, c,
                         (x + int(2*scale), y + int(8*scale),
                          max(1, W - int(4*scale)), max(1, H - int(16*scale))),
                         border_radius=max(2, int(5*scale)))
        # 지붕
        pygame.draw.rect(screen, roof,
                         (x + int(8*scale), y + int(18*scale),
                          max(1, W - int(16*scale)), max(1, H - int(40*scale))),
                         border_radius=max(1, int(4*scale)))
        # 앞유리 (아래)
        pygame.draw.rect(screen, glass,
                         (x + int(9*scale), y + int((76-28)*scale),
                          max(1, W - int(18*scale)), max(1, int(16*scale))),
                         border_radius=max(1, int(3*scale)))
        # 뒷유리 (위)
        pygame.draw.rect(screen, glass,
                         (x + int(9*scale), y + int(10*scale),
                          max(1, W - int(18*scale)), max(1, int(14*scale))),
                         border_radius=max(1, int(3*scale)))
        # 헤드라이트
        hl_y = y + int((76-14)*scale)
        pygame.draw.rect(screen, (255,255,180),
                         (x + int(6*scale), hl_y, max(1,int(10*scale)), max(1,int(6*scale))))
        pygame.draw.rect(screen, (255,255,180),
                         (x + W - int(16*scale), hl_y, max(1,int(10*scale)), max(1,int(6*scale))))
        # 바퀴
        for wx, wy in [(-7,10),( W-3+46,10),(-7,76-28),(W-3+46,76-28)]:
            pygame.draw.rect(screen, dark,
                             (x + int((wx-46)*scale), y + int(wy*scale),
                              max(1,int(10*scale)), max(1,int(20*scale))),
                             border_radius=max(1,int(3*scale)))
        # 방향지시등
        if self.changing and (self.blinker_f // 8) % 2 == 0:
            bx = (x + W - int(6*scale)) if self.target_lane > self.lane else (x + int(2*scale))
            pygame.draw.rect(screen, (255,200,0),
                             (bx, y + int(14*scale), max(1,int(4*scale)), max(1,int(8*scale))))


# ─────────────────────────────────────────────────────────────
#  Booster3D — Pseudo-3D 공간의 부스터 아이템
# ─────────────────────────────────────────────────────────────
class Booster3D:
    SIZE_WORLD = 80

    def __init__(self, z_spawn, lane_norm):
        self.z         = float(z_spawn)
        self.lane_norm = lane_norm
        self.speed     = 0.0         # 카메라가 움직이므로 별도 이동 없음
        self.collected = False
        self.frame     = 0

    def update(self, obstacle_speed):
        self.z     -= obstacle_speed
        self.frame += 1

    def draw(self, screen, road: Road3D):
        import math
        pos = road.project_obstacle(self.lane_norm, self.z)
        if pos is None:
            return
        sx, sy, scale = pos
        r = max(4, int(20 * scale))
        glow_r = r + int(4 * abs(math.sin(math.radians(self.frame * 7))))
        pygame.draw.circle(screen, (255, 230, 0), (sx, sy - r), glow_r + 3)
        pygame.draw.circle(screen, (255, 160, 0), (sx, sy - r), glow_r)
        # 별 (5각)
        pts = []
        for i in range(10):
            a    = math.radians(self.frame * 4 + i * 36 - 90)
            ri   = glow_r if i % 2 == 0 else glow_r // 2 + 2
            pts.append((sx + ri * math.cos(a), sy - r + ri * math.sin(a)))
        if len(pts) >= 3:
            pygame.draw.polygon(screen, (255, 255, 120), pts)
        pygame.draw.circle(screen, (255, 255, 255), (sx, sy - r), max(2, r // 3))


# ─────────────────────────────────────────────────────────────
#  Game — Pseudo-3D 메인 게임 클래스
# ─────────────────────────────────────────────────────────────
class Game:
    STATE_PLAYING  = "playing"
    STATE_GAMEOVER = "gameover"

    MAX_LIVES         = 5
    BOOSTER_THRESHOLD = 10

    # 장애물 생성 거리 (플레이어 앞)
    # DEPTH=380 기준: z=2500 → screen_y ≈ 366px (수평선 바로 아래, 작게 보임)
    SPAWN_Z   = 2500.0
    DESPAWN_Z = -600.0
    # 충돌 판정 범위: z=550 → screen_y≈642px (화면 하단 2/3 위치)
    # z=0: 장애물이 플레이어를 통과 → dodge 처리
    HIT_Z_FAR = 550.0

    def __init__(self, sw, sh, selections):
        self.sw = sw
        self.sh = sh

        # ── 난이도 ──────────────────────────────────────────
        diff_name = selections.get("difficulty", "보통")
        diff = DIFFICULTIES[diff_name]
        # 속도: 기본값 × 2  (보통=5×2=10 units/frame)
        # 10/frame × 60fps = 600 world/sec
        # SPAWN_Z=2500 → 장애물 접근 시간 = 2500/10/60 ≈ 4.2초
        self.obstacle_speed  = float(diff["obstacle_speed"]) * 2
        self.spawn_interval  = float(diff["spawn_interval"])
        self.speed_inc       = float(diff["speed_inc"]) * 2
        self.can_lane_change = diff_name in ("어려움", "익스트림")

        # ── 차 색깔 ─────────────────────────────────────────
        self.car_color  = CAR_COLORS[selections.get("car", "빨강")]
        self.racer_name = selections.get("racer", "Max Verstappen")
        self.tire       = selections.get("tire",  "미디엄")

        # ── 서킷 데이터 ─────────────────────────────────────
        circuit_name = selections.get("circuit", "Circuit de Monaco")
        circuit_data = next(
            (c for c in CIRCUITS if c["name"] == circuit_name),
            CIRCUITS[0])
        self.circuit_name = circuit_name

        # ── Road3D 생성 ─────────────────────────────────────
        self.road = Road3D(
            sw, sh,
            seg_curves   = circuit_data["curve"],
            road_half    = circuit_data["road_half"],
            grass_color  = circuit_data["grass"],
        )

        # ── HUD + 미니맵 ────────────────────────────────────
        self.hud = HUD(sw, sh)
        self.circuit_minimap = self._load_minimap(circuit_name)

        # ── 플레이어 상태 ────────────────────────────────────
        # x_norm: -1.0(왼쪽 끝) ~ 0.0(중앙) ~ +1.0(오른쪽 끝)
        self.player_x      = 0.0
        self.player_speed  = 0.022   # 좌우 이동 속도 (프레임당)
        self._cam_x        = 0.0    # 조향 시 카메라 시점 이동 (lerp)
        self.invincible    = 0
        self.flash_timer   = 0

        # ── 게임 상태 ────────────────────────────────────────
        self.state      = self.STATE_PLAYING
        self.lives      = self.MAX_LIVES
        self.score      = 0
        self.frame      = 0
        self.obstacles  = []
        self.boosters   = []
        self.consecutive_dodge = 0
        self.booster_active    = False

        self.font_big   = get_font(54, bold=True)
        self.font_mid   = get_font(30)
        self.font_small = get_font(22)

        # 플레이어 차 스프라이트 (사전 렌더링)
        self._player_surf = self._make_player_sprite()

    # ── 플레이어 F1카 스프라이트 생성 ───────────────────────
    def _make_player_sprite(self, w=56, h=110):
        surf = pygame.Surface((w + 28, h), pygame.SRCALPHA)
        c    = self.car_color
        dk   = tuple(max(0, v - 70) for v in c)
        M    = 14   # 바퀴 마진

        silver = (190, 190, 200)
        dark   = (25, 25, 25)
        white  = (255, 255, 255)

        x, y = M, 0

        # 리어 윙
        pygame.draw.rect(surf, silver, (x - 12, y + h - 18, w + 24, 9), border_radius=3)
        # 사이드포드
        pygame.draw.rect(surf, dk, (x - 7, y + 22, 9, 44), border_radius=3)
        pygame.draw.rect(surf, dk, (x + w - 2, y + 22, 9, 44), border_radius=3)
        # 메인 바디
        pygame.draw.rect(surf, c, (x + 4, y + 8, w - 8, h - 16), border_radius=7)
        # 하이라이트
        hl = tuple(min(255, v + 60) for v in c)
        pygame.draw.rect(surf, hl, (x + 8, y + 10, w - 16, 4), border_radius=2)
        # 코크핏
        pygame.draw.ellipse(surf, dark, (x + 9, y + 33, w - 18, 26))
        pygame.draw.ellipse(surf, white, (x + 12, y + 36, w - 24, 18))
        pygame.draw.ellipse(surf, (80, 80, 200), (x + 15, y + 40, w - 30, 10))
        # 노즈
        pygame.draw.polygon(surf, c, [(x + w//2, y), (x+9, y+12), (x+w-9, y+12)])
        # 프론트 윙
        pygame.draw.rect(surf, silver, (x - 10, y + 4, w + 20, 7), border_radius=2)
        # 장식선
        pygame.draw.rect(surf, white, (x + 13, y + 14, w - 26, 3))
        # 바퀴
        for wx, wy in [(-7, 8), (w - 2, 8), (-7, h - 28), (w - 2, h - 28)]:
            pygame.draw.rect(surf, dark, (x + wx, y + wy, 10, 20), border_radius=3)

        return surf

    # ── 서킷 미니맵 로드 ─────────────────────────────────────
    def _load_minimap(self, name, size=(168, 112)):
        path = os.path.join(_CIRCUIT_DIR, f"{name}.webp")
        try:
            raw = pygame.image.load(path).convert()
            return pygame.transform.smoothscale(raw, size)
        except Exception:
            return None

    # ── 키 입력 ─────────────────────────────────────────────
    def handle_input(self, keys):
        if self.state != self.STATE_PLAYING:
            return
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player_x = max(-1.0, self.player_x - self.player_speed)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player_x = min(1.0,  self.player_x + self.player_speed)

    # ── 이벤트 ──────────────────────────────────────────────
    def handle_event(self, event):
        if self.state == self.STATE_GAMEOVER:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    return "to_menu"
        return None

    # ── 업데이트 ────────────────────────────────────────────
    def update(self):
        if self.state != self.STATE_PLAYING:
            return

        self.frame += 1
        self.score += 1

        # 카메라 전진
        self.road.advance(self.obstacle_speed)

        # 조향 카메라: player_x를 부드럽게 따라가 시점 이동
        self._cam_x += (self.player_x - self._cam_x) * 0.12

        # 플레이어 무적 타이머
        if self.invincible > 0:
            self.invincible  -= 1
            self.flash_timer += 1
        else:
            self.flash_timer = 0

        # 속도 증가 (150프레임마다)
        if self.frame % 150 == 0:
            self.obstacle_speed = min(self.obstacle_speed + self.speed_inc, 60.0)
            self.spawn_interval = max(self.spawn_interval - 3.0, 35.0)

        # 장애물 생성
        if self.frame % int(self.spawn_interval) == 0:
            lane = random.randint(0, 2)
            # 같은 차선에 너무 가까운 장애물이 이미 있으면 스킵
            too_close = any(
                o.lane == lane and o.z < self.SPAWN_Z * 0.6
                for o in self.obstacles)
            if not too_close:
                self.obstacles.append(
                    Obstacle3D(self.SPAWN_Z + random.uniform(-400, 400),
                               lane, self.obstacle_speed,
                               can_change=self.can_lane_change))

        self._update_obstacles()
        self._update_boosters()

    def _update_obstacles(self):
        new_obs = []
        for obs in self.obstacles:
            obs.update()

            # ── 충돌 판정 ─────────────────────────────────
            # 장애물이 플레이어 앞 HIT_Z_FAR 이내에 들어오면 x 겹침 확인
            if not obs.passed and 0 < obs.z <= self.HIT_Z_FAR:
                dx = abs(self.player_x - obs.lane_norm)
                if dx < 0.44:   # 차선 겹침 기준
                    obs.passed = True
                    if self.invincible <= 0:
                        self.invincible  = 90
                        self.flash_timer = 0
                        self.lives      -= 1
                        self.consecutive_dodge = 0
                        if self.lives <= 0:
                            self.state = self.STATE_GAMEOVER

            # ── 피하기 성공 ───────────────────────────────
            # z ≤ 0: 장애물이 플레이어를 통과함 → 피하기 카운트
            if not obs.passed and obs.z <= 0:
                obs.passed = True
                self.consecutive_dodge += 1
                if (self.consecutive_dodge >= self.BOOSTER_THRESHOLD
                        and not self.boosters):
                    self._spawn_booster()
                    self.consecutive_dodge = 0

            if obs.z > self.DESPAWN_Z:
                new_obs.append(obs)

        self.obstacles = new_obs

    def _update_boosters(self):
        new_b = []
        for b in self.boosters:
            b.update(self.obstacle_speed)

            # 부스터 수집: 플레이어 z 범위 + x 겹침
            if (self.HIT_Z_NEAR <= b.z <= self.HIT_Z_FAR
                    and abs(self.player_x - b.lane_norm) < 0.5):
                b.collected = True
                self.score += 5000
                self.booster_active = True

            if b.z > self.DESPAWN_Z and not b.collected:
                new_b.append(b)

        self.boosters = new_b
        if not self.boosters:
            self.booster_active = False

    def _spawn_booster(self):
        ln = random.choice([-0.58, 0.0, 0.58])
        self.boosters.append(Booster3D(self.SPAWN_Z * 0.5, ln))

    # ── 그리기 ──────────────────────────────────────────────
    def draw(self, screen):
        # 도로 렌더링 (조향 카메라 피드백 포함)
        road_cx, road_w = self.road.draw(screen, self._cam_x)

        # 장애물 (z 멀리→가까이 순으로 그려야 앞이 위에)
        for obs in sorted(self.obstacles, key=lambda o: -o.z):
            obs.draw(screen, self.road)

        # 부스터
        for b in self.boosters:
            b.draw(screen, self.road)

        # 플레이어 차 (화면 하단 중앙)
        if self.invincible <= 0 or (self.flash_timer // 5) % 2 == 0:
            ps  = self._player_surf
            pw  = ps.get_width()
            ph  = ps.get_height()
            # 플레이어 x를 도로 경계 안에서 변환
            px  = road_cx + int(self.player_x * road_w * 0.55) - pw // 2
            py  = self.sh - ph - 20
            screen.blit(ps, (px, py))

        # 서킷 한 바퀴 총 길이 + 현재 진행 위치
        total_len    = len(self.road.segs) * Road3D.SEG_LEN
        circuit_pos  = (self.road.camera_z % total_len) / max(1, total_len)
        circuit_lap  = int(self.road.camera_z / total_len) + 1

        # HUD
        self.hud.draw(
            screen,
            lives          = self.lives,
            score          = self.score,
            consecutive    = self.consecutive_dodge,
            racer_name     = self.racer_name,
            tire           = self.tire,
            booster_active = self.booster_active,
            speed          = self.obstacle_speed / 2,   # 원래 단위로 환산
            circuit_img    = self.circuit_minimap,
            circuit_name   = self.circuit_name,
            circuit_pos    = circuit_pos,
            circuit_lap    = circuit_lap,
        )

        if self.state == self.STATE_GAMEOVER:
            self._draw_gameover(screen)

    def _draw_gameover(self, screen):
        ov = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        screen.blit(ov, (0, 0))

        go = self.font_big.render("GAME OVER", True, (255, 60, 60))
        screen.blit(go, (self.sw // 2 - go.get_width() // 2, 160))

        racer = self.font_mid.render(f"Driver: {self.racer_name}", True, (200, 220, 255))
        screen.blit(racer, (self.sw // 2 - racer.get_width() // 2, 250))

        sc = self.font_mid.render(f"최종 점수: {self.score // 10:,}", True, (255, 255, 100))
        screen.blit(sc, (self.sw // 2 - sc.get_width() // 2, 295))

        restart = self.font_small.render("SPACE / ESC — 메뉴로 돌아가기", True, (180, 180, 220))
        screen.blit(restart, (self.sw // 2 - restart.get_width() // 2, 380))

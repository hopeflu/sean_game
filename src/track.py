import pygame
import math

# 트랙 종류별 도로 렌더링과 위치 계산을 담당하는 클래스
class Track:
    ROAD_COLOR    = (55, 55, 55)    # 아스팔트 색
    MOUNTAIN_ROAD = (75, 68, 60)    # 산악 아스팔트
    LANE_LINE     = (200, 200, 200) # 차선 색

    def __init__(self, track_data, screen_width, screen_height):
        self.name        = track_data["name"]
        self.track_type  = track_data["type"]
        self.road_width  = track_data["width"]
        self.amplitude   = float(track_data["amplitude"])  # 커브 좌우 폭
        self.period      = track_data["period"]            # 커브 주기(프레임)

        self.screen_width  = screen_width
        self.screen_height = screen_height

        self.frame            = 0
        self.road_offset      = 0.0   # 현재 도로 중심의 좌우 오프셋
        self.lane_line_offset = 0.0   # 차선 점선 스크롤 위치

    # ── 매 프레임 호출 ──────────────────────────────────────
    def update(self, scroll_speed):
        self.frame += 1
        self.lane_line_offset = (self.lane_line_offset + scroll_speed) % 60

        # 직선 트랙이 아닌 경우 도로가 좌우로 흔들림
        if self.amplitude > 0 and self.period > 1:
            self.road_offset = self.amplitude * math.sin(
                2 * math.pi * self.frame / self.period
            )

    # ── 도로 중심 x 좌표 ────────────────────────────────────
    def get_road_center_x(self):
        return self.screen_width // 2 + int(self.road_offset)

    # ── 도로 왼쪽·오른쪽 경계 반환 ──────────────────────────
    def get_road_bounds(self):
        cx   = self.get_road_center_x()
        half = self.road_width // 2
        return cx - half, cx + half

    # ── 차선 x 좌표 목록 반환 (장애물 스폰에 사용) ──────────
    def get_lane_xs(self, obstacle_width=46):
        left, right = self.get_road_bounds()
        rw          = right - left
        lw          = rw // 3
        return [left + lw * i + lw // 2 - obstacle_width // 2 for i in range(3)]

    # ── 화면 그리기 ─────────────────────────────────────────
    def draw(self, screen):
        left, right = self.get_road_bounds()
        rw = right - left

        # 트랙 종류별 배경색
        if self.track_type == "mountain":
            screen.fill((90, 70, 50))     # 갈색 산악 지형
        elif self.track_type == "circuit":
            screen.fill((15, 70, 20))     # 진한 초록 서킷
        elif self.track_type == "winding":
            screen.fill((25, 90, 30))     # 숲 초록
        else:
            screen.fill((34, 139, 34))    # 잔디

        # 도로 본체
        road_c = self.MOUNTAIN_ROAD if self.track_type == "mountain" else self.ROAD_COLOR
        pygame.draw.rect(screen, road_c, (left, 0, rw, self.screen_height))

        # 트랙별 추가 장식
        if self.track_type == "mountain":
            self._draw_rocks(screen, left, right)
        elif self.track_type == "circuit":
            self._draw_circuit_curbs(screen, left, right)
        elif self.track_type == "winding":
            self._draw_winding_barriers(screen, left, right)

        # 도로 경계선
        border_c = (255, 255, 255) if self.track_type != "winding" else (255, 80, 80)
        pygame.draw.rect(screen, border_c, (left - 5, 0, 5, self.screen_height))
        pygame.draw.rect(screen, border_c, (right,     0, 5, self.screen_height))

        # 차선 점선 (3차선 → 2개의 구분선)
        lw = rw // 3
        for i in range(1, 3):
            lx = left + lw * i
            y  = -60 + self.lane_line_offset
            while y < self.screen_height:
                pygame.draw.rect(screen, self.LANE_LINE, (lx - 2, int(y), 4, 35))
                y += 60

    # ── 산악 트랙: 양쪽에 바위 그리기 ───────────────────────
    def _draw_rocks(self, screen, left, right):
        rock_c  = (110, 95, 80)
        shade_c = (75, 60, 48)
        # 스크롤에 따라 바위 위치가 내려오는 효과
        for base_y in range(0, self.screen_height + 80, 90):
            ry = int((base_y + self.lane_line_offset * 3) % (self.screen_height + 90)) - 45

            # 왼쪽 바위 (도로 밖)
            pygame.draw.ellipse(screen, rock_c,  (left - 55, ry,      60, 38))
            pygame.draw.ellipse(screen, shade_c, (left - 50, ry + 8,  44, 20))
            pygame.draw.ellipse(screen, rock_c,  (left - 30, ry - 14, 38, 28))

            # 오른쪽 바위
            pygame.draw.ellipse(screen, rock_c,  (right - 5,  ry,      60, 38))
            pygame.draw.ellipse(screen, shade_c, (right + 5,  ry + 8,  44, 20))
            pygame.draw.ellipse(screen, rock_c,  (right - 10, ry - 14, 38, 28))

    # ── 서킷 트랙: 빨강/하양 체크무늬 커브 ─────────────────
    def _draw_circuit_curbs(self, screen, left, right):
        curb_h = 18
        colors = [(255, 50, 50), (255, 255, 255)]
        y = int(self.lane_line_offset * 2) % (curb_h * 2) - curb_h * 2
        while y < self.screen_height:
            col = colors[(int(y) // curb_h) % 2]
            pygame.draw.rect(screen, col, (left - 12, y, 12, curb_h))
            pygame.draw.rect(screen, col, (right,     y, 12, curb_h))
            y += curb_h

    # ── 구불구불 트랙: 빨강 가드레일 ───────────────────────
    def _draw_winding_barriers(self, screen, left, right):
        barrier_c = (200, 50, 50)
        y = -20 + self.lane_line_offset
        while y < self.screen_height:
            pygame.draw.rect(screen, barrier_c, (left - 12, int(y), 12, 25))
            pygame.draw.rect(screen, barrier_c, (right,      int(y), 12, 25))
            pygame.draw.line(screen, (220, 220, 220),
                             (left - 6, int(y)), (left - 6, int(y) + 25), 2)
            pygame.draw.line(screen, (220, 220, 220),
                             (right + 6, int(y)), (right + 6, int(y) + 25), 2)
            y += 50

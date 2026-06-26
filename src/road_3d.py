import pygame

# ─────────────────────────────────────────────────────────────
#  Pseudo-3D 도로 렌더러 (Outrun / F-Zero 스타일 스캔라인 방식)
#
#  핵심 공식:
#   • wz = DEPTH × (sh−hy) / (y−hy)  : 화면 행 y 의 세계 깊이
#   • road_w_px = road_hw × DEPTH / wz : 원근 도로 폭 (가까울수록 넓음)
#   • t = DEPTH / wz                  : 원근 비율 (1.0=하단, →0=수평선)
#   • road_cx = sw/2 + crv×(1−t)×55  : 커브로 인한 소실점 이동
#   • steer   = player_x × 60×(1−t)  : 조향 시 시점 이동 (반응성)
# ─────────────────────────────────────────────────────────────

class Road3D:
    STEP    = 2      # 스캔라인 보폭 (픽셀)
    DEPTH   = 380    # 투영 기준 깊이 (이 z에서 도로가 화면 맨 아래)
    SEG_LEN = 1000   # 세그먼트 1개의 세계 단위 길이
                     # 6 segs/km → 보통속도(10/frame×60fps) 기준 1km ≈ 10초

    def __init__(self, sw, sh, seg_curves, road_half, grass_color=(34,140,34)):
        self.sw        = sw
        self.sh        = sh
        self.road_hw   = float(road_half)
        self.grass_base = grass_color

        # (curve, count) → 평탄화된 세그먼트 배열
        self.segs = []
        for crv, n in seg_curves:
            self.segs.extend([float(crv)] * int(n))
        if not self.segs:
            self.segs = [0.0]

        self.horizon_y   = int(sh * 0.36)
        self.camera_z    = 0.0
        self.frame       = 0
        self._smooth_crv = 0.0   # lerp된 커브값

        # draw() 후 채워짐 (장애물 투영에 사용)
        self._row_cx: dict = {}

    # ── 전진 ────────────────────────────────────────────────
    def advance(self, speed: float):
        self.camera_z += speed
        self.frame    += 1
        target = self._seg_at(self.camera_z)
        self._smooth_crv += (target - self._smooth_crv) * 0.05

    def _seg_at(self, abs_z: float) -> float:
        idx = int(abs(abs_z) / self.SEG_LEN) % len(self.segs)
        return self.segs[idx]

    def current_curve(self) -> float:
        return self._smooth_crv

    # ── 스캔라인 도로 렌더링 ──────────────────────────────
    def draw(self, screen, player_x_cam: float = 0.0) -> tuple:
        """
        player_x_cam : 조향 시 카메라 시점 이동 (-1~+1)
                       우측 이동 시 도로가 왼쪽으로 살짝 이동 → 반응성 피드백
        반환: (road_center_x_at_bottom, road_half_px_at_bottom)
        """
        sw, sh, hy = self.sw, self.sh, self.horizon_y
        DEPTH, STEP = self.DEPTH, self.STEP
        crv = self._smooth_crv

        # ── 하늘 그라데이션 ────────────────────────────────
        for y in range(hy):
            t = y / max(1, hy)
            pygame.draw.rect(screen,
                             (int(8+t*55), int(18+t*75), int(90+t*110)),
                             (0, y, sw, 1))

        # ── 도로 스캔라인 ──────────────────────────────────
        self._row_cx.clear()
        road_cx_bottom = sw // 2
        road_w_bottom  = int(self.road_hw)

        for y in range(sh - STEP, hy, -STEP):
            wz    = DEPTH * (sh - hy) / max(1, y - hy)
            abs_z = self.camera_z + wz

            # 도로 너비 (원근)
            road_w_px = max(4, int(self.road_hw * DEPTH / wz))

            # 원근 비율
            t = max(0.001, DEPTH / wz)

            # 소실점 = 커브 이동 + 조향 피드백
            # 커브: 멀수록 크게 (1-t), 강도 55
            # 조향: 우측 이동 시 도로가 왼쪽으로 이동 → player_x_cam × -60
            road_cx = (sw // 2
                       + int(crv * (1.0 - t) * 55)
                       + int(player_x_cam * (1.0 - t) * -60))

            self._row_cx[y] = road_cx

            if y < sh - STEP * 2:
                road_cx_bottom = road_cx
                road_w_bottom  = road_w_px

            # 교대 줄무늬 (속도감)
            stripe   = int(abs_z / (self.SEG_LEN // 5)) % 2
            road_c   = (88, 88, 88) if stripe else (70, 70, 70)
            rumble_c = (215, 30, 30) if stripe else (240, 240, 240)
            dash_on  = (stripe == 1)

            g = self.grass_base
            grass_c = (min(255,g[0]+8), min(255,g[1]+15), min(255,g[2]+8)) if stripe else g

            rumble_w = max(3, road_w_px // 7)
            lx = road_cx - road_w_px
            rx = road_cx + road_w_px

            if lx - rumble_w > 0:
                pygame.draw.rect(screen, grass_c,  (0, y, max(0,lx-rumble_w), STEP))
            pygame.draw.rect(screen, rumble_c, (max(0,lx-rumble_w), y, rumble_w, STEP))
            pygame.draw.rect(screen, road_c,   (lx, y, road_w_px*2, STEP))
            if road_w_px > 22 and dash_on:
                dw = max(2, road_w_px // 13)
                pygame.draw.rect(screen, (240,240,240), (road_cx-dw, y, dw*2, STEP))
            pygame.draw.rect(screen, rumble_c, (rx, y, rumble_w, STEP))
            if rx + rumble_w < sw:
                pygame.draw.rect(screen, grass_c, (rx+rumble_w, y, sw-rx-rumble_w, STEP))

        return road_cx_bottom, road_w_bottom

    # ── 장애물 화면 좌표 투영 ────────────────────────────
    def project_obstacle(self, lane_norm: float, z_rel: float):
        """
        lane_norm : -1.0(왼) ~ 0.0(중) ~ +1.0(우)
        z_rel     : 플레이어 기준 전방 거리 (양수=앞)
        반환: (screen_x, screen_y, scale) 또는 None
        """
        if z_rel <= 2:
            return None
        DEPTH = self.DEPTH
        sh, hy = self.sh, self.horizon_y

        sy = hy + int(DEPTH * (sh - hy) / z_rel)
        if not (hy < sy < sh + 50):   # 화면 아래 약간까지 허용
            return None

        y_key   = (sy // self.STEP) * self.STEP
        road_cx = self._row_cx.get(y_key, self.sw // 2)
        road_w_px = max(4, int(self.road_hw * DEPTH / z_rel))

        sx    = road_cx + int(lane_norm * road_w_px * 0.58)
        scale = max(0.05, min(2.0, DEPTH / z_rel))
        return sx, sy, scale

    # ── 플레이어 위치 도로 경계 ──────────────────────────
    def road_bounds_at_bottom(self):
        y_key = ((self.sh - self.STEP * 2) // self.STEP) * self.STEP
        cx    = self._row_cx.get(y_key, self.sw // 2)
        rw    = int(self.road_hw)
        return cx - rw, cx + rw

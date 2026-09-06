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

        # 원경 대기 안개(atmospheric perspective) 색 — 수평선에서 도로/잔디가
        # 이 색으로 흐려지며 고전 레이싱 게임 특유의 깊이감을 만든다.
        haze = (150, 165, 195)

        def fog(col, f):
            return (int(col[0]*(1-f)+haze[0]*f),
                    int(col[1]*(1-f)+haze[1]*f),
                    int(col[2]*(1-f)+haze[2]*f))

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

            # 리지드 체이스 뷰:
            #  • 커브 소실점 이동: 멀수록 크게 (1-t), 강도 55
            #  • 플레이어 횡위치는 "월드를 반대로 밀기"로 표현 → 차는 화면 중앙 고정.
            #    근거리일수록(road_w_px 큼) 더 많이 밀려 올바른 원근 횡이동이 됨.
            road_cx = (sw // 2
                       + int(crv * (1.0 - t) * 55)
                       - int(player_x_cam * road_w_px * 0.58))

            self._row_cx[y] = road_cx

            # 원경 안개 강도 (수평선=1.0 → 하단=0.0), 근거리는 완만하게
            f = max(0.0, min(1.0, 1.0 - t))
            f *= f

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

            # 원경 안개 적용 → 멀수록 색이 대기색으로 흐려져 깊이감 상승
            road_c   = fog(road_c,   f)
            rumble_c = fog(rumble_c, f)
            grass_c  = fog(grass_c,  f)

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

        # ── 도로변 표지판 (원근 깊이 + 속도감) ────────────────
        # 일정 간격의 세계 z마다 좌우에 빨강/흰색 폴을 세워 원근으로 투영.
        self._draw_poles(screen)

        return road_cx_bottom, road_w_bottom

    # ── 도로변 폴 렌더링 ──────────────────────────────────
    def _draw_poles(self, screen):
        sw, sh, hy = self.sw, self.sh, self.horizon_y
        DEPTH, STEP = self.DEPTH, self.STEP
        spacing = self.SEG_LEN // 2
        base = (int(self.camera_z) // spacing) * spacing

        # 먼 것부터 그려 가까운 폴이 위에 오도록
        for i in range(46, 0, -1):
            world_z = base + i * spacing
            z_rel   = world_z - self.camera_z
            if z_rel < 30:
                continue
            sy = hy + int(DEPTH * (sh - hy) / z_rel)
            if not (hy < sy < sh):
                continue

            y_key   = (sy // STEP) * STEP
            road_cx = self._row_cx.get(y_key, sw // 2)
            road_w  = max(4, int(self.road_hw * DEPTH / z_rel))
            scale   = DEPTH / z_rel

            ph  = max(2, int(70 * scale))   # 폴 높이
            pw  = max(1, int(7  * scale))   # 폴 두께
            off = int(road_w * 1.22)        # 도로 바깥쪽 간격
            alt = (world_z // spacing) % 2
            top = (225, 45, 45) if alt else (238, 238, 238)

            for sign in (-1, 1):
                px = road_cx + sign * off
                if -20 < px < sw + 20:
                    pygame.draw.rect(screen, (60, 60, 60),
                                     (px - pw // 2, sy - ph, pw, ph))
                    pygame.draw.rect(screen, top,
                                     (px - pw, sy - ph, pw * 2,
                                      max(2, int(12 * scale))))

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

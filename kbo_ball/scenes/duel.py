"""
투타 대결 씬 — Phase 1 의 본편.

한 반 이닝(3아웃)을 플레이한다. 유저는 타자, CPU는 투수를 맡는다.
1경기 모드로 확장할 때는 이 씬을 그대로 두고 `engine.rules.Scoreboard` 로
공수 교대만 감싸면 되도록, 규칙 처리는 전부 engine 쪽에 있다.

타석 진행 상태
--------------
READY   → 타자 소개 (짧은 정지)
WINDUP  → 투수 와인드업
FLIGHT  → 공이 날아옴. 이 구간에서만 조준·스윙 입력을 받는다
BATTED  → 배트에 맞음. 탑다운 구장 화면으로 전환해 타구를 중계
RESULT  → 결과 배너 표시 후 다음 투구/타자로
"""

import random
import pygame

from .. import config as C
from .. import sfx
from ..engine import batted_ball as bbmod
from ..engine import swing as swingmod
from ..engine.pitch import PitcherAI
from ..engine.rules import HalfInning
from ..fonts import draw_text
from ..retro import vgradient, dashed_rect, shake_offset
from ..ui import sprites, widgets, field_view
from .base import Scene

# 상태 상수
READY, WINDUP, FLIGHT, BATTED, RESULT = "READY", "WINDUP", "FLIGHT", "BATTED", "RESULT"

CURSOR_SPEED = 2.3          # 조준 커서 이동 속도(px/frame)
SWING_FRAMES = 9            # 스윙 모션 길이


class DuelScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.rng = random.Random()
        self.half = HalfInning()
        self.ai = PitcherAI(app.pitcher)

        self.batter_idx = 0
        self.pitch = None
        self.contact = None
        self.bb = None                     # BattedBall

        # 조준 커서 — 존 한복판에서 시작
        self.cur_x = C.ZONE_X + C.ZONE_W / 2
        self.cur_y = C.ZONE_Y + C.ZONE_H / 2

        self.swing_frame = -1              # 스윙 모션 진행 프레임 (-1=대기)
        self.swung = False                 # 이번 공에 이미 스윙했는가
        self.shake = 0                     # 화면 흔들림 잔여 프레임

        self.state = READY
        self.timer = 50
        self.banner = None                 # (제목, 부제, 색)
        self.last_pitch_name = "-"

    # ── 현재 타자 ─────────────────────────────────────────
    @property
    def batter(self):
        return self.app.lineup[self.batter_idx % len(self.app.lineup)]

    # ── 입력 ──────────────────────────────────────────────
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            from .title import TitleScene
            self.next_scene = TitleScene(self.app)
            return

        # 결과 배너는 SPACE로 빨리 넘길 수 있다
        if self.state == RESULT and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.timer = 0
            return

        # 스윙 — 공이 날아오는 동안 한 번만
        if (self.state == FLIGHT and not self.swung
                and event.key in (pygame.K_SPACE, pygame.K_z)):
            self._do_swing()

    def _read_cursor_keys(self):
        """방향키를 눌린 상태로 읽어 커서를 부드럽게 움직인다."""
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - \
             (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - \
             (keys[pygame.K_UP] or keys[pygame.K_w])
        self.cur_x += dx * CURSOR_SPEED
        self.cur_y += dy * CURSOR_SPEED

        # 존보다 조금 넓은 범위까지만 (유인구를 쫓아갈 수 있도록)
        m = 16
        self.cur_x = max(C.ZONE_X - m, min(C.ZONE_X + C.ZONE_W + m, self.cur_x))
        self.cur_y = max(C.ZONE_Y - m, min(C.ZONE_Y + C.ZONE_H + m, self.cur_y))

    # ── 갱신 ──────────────────────────────────────────────
    def update(self):
        if self.shake > 0:
            self.shake -= 1

        if self.state == READY:
            self.timer -= 1
            if self.timer <= 0:
                self._begin_pitch()

        elif self.state == WINDUP:
            self.timer -= 1
            self._read_cursor_keys()
            if self.timer <= 0:
                sfx.play("pitch")
                self.state = FLIGHT

        elif self.state == FLIGHT:
            self._read_cursor_keys()
            if self.swing_frame >= 0:
                self.swing_frame += 1
            self.pitch.update()
            if self.pitch.done:
                self._resolve_no_contact()

        elif self.state == BATTED:
            self.timer += 1
            if self.timer >= 78:
                self._show_batted_result()

        elif self.state == RESULT:
            self.timer -= 1
            if self.timer <= 0:
                self._advance()

    # ── 타석 진행 ─────────────────────────────────────────
    def _begin_pitch(self):
        c = self.half.count
        self.pitch = self.ai.choose(c.balls, c.strikes)
        self.last_pitch_name = self.pitch.type["name"]
        self.swung = False
        self.swing_frame = -1
        self.contact = None
        self.bb = None
        self.state = WINDUP
        self.timer = 26

    def _do_swing(self):
        """SPACE 입력 → 컨택 판정."""
        self.swung = True
        self.swing_frame = 0
        sfx.play("swing")

        self.contact = swingmod.judge(
            self.pitch, self.pitch.t, (self.cur_x, self.cur_y),
            self.batter["contact"])

        if not self.contact.made:
            return                       # 헛스윙 — 공은 계속 날아간다

        sfx.play("hit")
        self.shake = 8
        self.bb = bbmod.resolve(self.contact, self.batter, self.rng)

        if self.bb.is_foul:
            # 파울은 중계 없이 바로 결과 처리
            strikeout = self.half.count.add_strike(foul=True)
            self._banner("파울", f"{self.last_pitch_name} · {self.contact.label}", C.GRAY)
            self.state = RESULT
            self.timer = 42
            return

        # 페어 타구 → 탑다운 중계 화면으로
        self.state = BATTED
        self.timer = 0

    def _resolve_no_contact(self):
        """스윙을 안 했거나 헛스윙한 공이 포수 미트에 들어갔을 때."""
        c = self.half.count
        if self.swung:
            out = c.add_strike()
            if out:
                sfx.play("out")
                self.half.apply_strikeout()
                self._banner("삼진 아웃", "헛스윙 삼진", C.RED)
            else:
                sfx.play("strike")
                self._banner("헛스윙", f"{self.last_pitch_name} · 스트라이크", C.YELLOW)
        elif self.pitch.in_strike_zone():
            out = c.add_strike()
            if out:
                sfx.play("out")
                self.half.apply_strikeout()
                self._banner("삼진 아웃", "루킹 삼진", C.RED)
            else:
                sfx.play("strike")
                self._banner("스트라이크", f"{self.last_pitch_name} · 존 통과", C.YELLOW)
        else:
            walked = c.add_ball()
            if walked:
                sfx.play("select")
                self.half.apply_walk()
                self._banner("볼넷", "출루!", C.CYAN)
            else:
                sfx.play("ball")
                self._banner("볼", f"{self.last_pitch_name} · 존 바깥", C.GREEN)

        self.state = RESULT
        self.timer = 46

    def _show_batted_result(self):
        """탑다운 중계가 끝난 뒤 실제 결과를 규칙에 반영한다."""
        bb = self.bb
        if bb.is_hit:
            if bb.result == "HR":
                sfx.play("hr")
                self.shake = 14
            self.half.apply_hit(bb)
            color = C.YELLOW if bb.result == "HR" else C.GREEN
        else:
            sfx.play("out")
            self.half.apply_out(bb.desc)
            color = C.RED

        sub = (f"타구속도 {int(bb.exit_v * 100)}  발사각 {bb.launch:.0f}°  "
               f"비거리 {bb.distance:.0f}m")
        self._banner(bb.desc, sub, color)
        self.state = RESULT
        self.timer = 82

    def _banner(self, title, sub, color):
        self.banner = (title, sub, color)

    def _advance(self):
        """결과 배너 종료 — 다음 투구 또는 다음 타자."""
        self.banner = None

        if self.half.over:
            from .result import ResultScene
            self.next_scene = ResultScene(self.app, self.half)
            return

        # 카운트가 리셋되었다면 타석이 끝난 것 → 다음 타자
        c = self.half.count
        if c.balls == 0 and c.strikes == 0:
            self.batter_idx += 1
            self.state = READY
            self.timer = 40
        else:
            self._begin_pitch()

    # ── 픽셀 아트 레이어 ──────────────────────────────────
    def draw_playfield(self, pf):
        if self.state == BATTED:
            self._draw_batted(pf)
        else:
            self._draw_plate_view(pf)

    def _draw_plate_view(self, pf):
        """포수 뒤 시점 — 투수·타자·스트라이크존·공."""
        my, opp = self.app.my_team, self.app.opp_team

        # ── 배경 ──────────────────────────────────────────
        # 야간 하늘 → 관중석 → 외야 펜스 → 내야 잔디 → 홈플레이트 흙
        vgradient(pf, (0, 0, C.PF_W, 30), (14, 14, 32), (36, 44, 84), bands=5)
        for x in range(0, C.PF_W, 4):                    # 관중 실루엣
            pygame.draw.rect(pf, (50, 50, 76), (x, 24 + (x % 3), 3, 14))
        pygame.draw.rect(pf, (26, 30, 52), (0, 38, C.PF_W, 6))   # 외야 펜스
        pygame.draw.rect(pf, (90, 96, 120), (0, 38, C.PF_W, 1))

        # 잔디 — 아래로 갈수록 밝아지는 줄무늬(원근감)
        for i, y in enumerate(range(44, 176, 11)):
            col = C.TURF if i % 2 == 0 else C.TURF_DARK
            pygame.draw.rect(pf, col, (0, y, C.PF_W, 11))

        # 홈플레이트 흙 — 위쪽 경계를 타원으로 깎아 자연스럽게
        pygame.draw.rect(pf, C.DIRT, (0, 176, C.PF_W, C.PF_H - 176))
        pygame.draw.ellipse(pf, C.DIRT, (-40, 158, 400, 40))

        # 마운드
        pygame.draw.ellipse(pf, C.DIRT, (C.RELEASE_X - 32, C.MOUND_Y - 6, 64, 20))
        pygame.draw.ellipse(pf, C.DIRT_DARK, (C.RELEASE_X - 32, C.MOUND_Y - 6, 64, 20), 1)
        pygame.draw.rect(pf, C.LINE_WHITE, (C.RELEASE_X - 5, C.MOUND_Y + 2, 11, 2))

        # 타석 라인 + 홈플레이트
        pygame.draw.rect(pf, C.LINE_WHITE, (88, C.HOME_PLATE_Y - 26, 34, 40), 1)
        pygame.draw.rect(pf, C.LINE_WHITE, (198, C.HOME_PLATE_Y - 26, 34, 40), 1)
        hp = C.HOME_PLATE_Y
        pygame.draw.polygon(pf, C.BONE,
                            [(152, hp), (168, hp), (168, hp + 5), (160, hp + 10),
                             (152, hp + 5)])

        # ── 투수 (와인드업 진행도) ────────────────────────
        if self.state == WINDUP:
            wind = 1.0 - self.timer / 26
        elif self.state == FLIGHT:
            wind = 1.0
        else:
            wind = 0.0
        sprites.draw_pitcher(pf, C.RELEASE_X, C.MOUND_Y + 6, opp, wind_up=wind)

        # 스트라이크존
        dashed_rect(pf, (C.ZONE_X, C.ZONE_Y, C.ZONE_W, C.ZONE_H),
                    (200, 200, 220), dash=3, gap=3)
        for i in range(1, C.ZONE_COLS):                  # 3x3 격자
            x = C.ZONE_X + i * C.CELL_W
            pygame.draw.line(pf, (90, 90, 110), (x, C.ZONE_Y + 2),
                             (x, C.ZONE_Y + C.ZONE_H - 2))
        for i in range(1, C.ZONE_ROWS):
            y = C.ZONE_Y + i * C.CELL_H
            pygame.draw.line(pf, (90, 90, 110), (C.ZONE_X + 2, y),
                             (C.ZONE_X + C.ZONE_W - 2, y))

        # 공
        if self.pitch and self.state in (FLIGHT,) and not (self.contact and self.contact.made):
            x, y = self.pitch.position()
            sprites.draw_ball(pf, x, y, self.pitch.radius(),
                              spin_phase=self.frame * self.pitch.type["spin"],
                              trail=self.pitch.trail)

        # 타자 / 포수
        sp = 0.0 if self.swing_frame < 0 else min(1.0, self.swing_frame / SWING_FRAMES)
        sprites.draw_batter(pf, 105, C.BATTER_Y, my, swing_phase=sp)
        sprites.draw_catcher(pf, 160, C.CATCHER_Y, opp)

        # 조준 커서
        if self.state in (WINDUP, FLIGHT):
            sprites.draw_cursor(pf, int(self.cur_x), int(self.cur_y),
                                frame=self.frame)

        # 타격 순간 섬광 — 공을 친 직후 몇 프레임만, 작게.
        # (홈런 연출로 shake를 크게 준 뒤 결과 화면까지 남지 않도록 상태를 함께 검사)
        if (self.state == FLIGHT and self.contact
                and self.contact.made and self.shake > 3):
            r = 2 + self.shake // 2
            pygame.draw.circle(pf, C.WHITE, (int(self.cur_x), int(self.cur_y)), r)
            pygame.draw.circle(pf, C.YELLOW, (int(self.cur_x), int(self.cur_y)), r + 2, 1)

    def _draw_batted(self, pf):
        """탑다운 구장 중계."""
        field_view.draw_field(pf, self.app.opp_team)
        progress = min(1.0, self.timer / 58.0)
        field_view.draw_ball_flight(pf, self.bb, progress)
        # 타자 주자 — 안타면 진루 수만큼, 아웃이면 1루까지만 달린다
        field_view.draw_runner(pf, self.app.my_team,
                               min(1.0, self.timer / 70.0),
                               self.bb.bases if self.bb.is_hit else 1)
        if progress >= 1.0:
            field_view.draw_landing_mark(pf, self.bb, self.frame)

    # ── HUD 레이어 ────────────────────────────────────────
    def draw_hud(self, win):
        half = self.half
        widgets.count_board(win, 24, 24, half, self.app.pitcher["name"], self.batter)
        widgets.runner_board(win, C.WIN_W - 224, 24, half)

        # 팀 표시
        draw_text(win, f"{self.app.my_team['code']} 공격", (C.WIN_W // 2, 30),
                  size=22, color=self.app.my_team["accent"], bold=True, anchor="midtop")
        draw_text(win, f"vs {self.app.opp_team['name']}", (C.WIN_W // 2, 58),
                  size=16, color=(170, 180, 210), anchor="midtop")

        # 좌측 — 타석 기록 로그 (카운트 보드 아래).
        # 결과 배너(폭 480, 중앙 정렬)와 겹치지 않도록 폭을 200으로 제한한다.
        widgets.panel(win, (24, 204, 200, 152))
        draw_text(win, "타석 기록", (38, 216), size=16, color=C.CYAN, bold=True)
        widgets.pitch_log(win, 38, 242, half.log)

        # 하단 — 성적 한 줄 + 조작 안내 (스프라이트를 가리지 않도록 얇게)
        widgets.panel(win, (0, C.WIN_H - 58, C.WIN_W, 58), alpha=235)
        widgets.stat_line(win, 24, C.WIN_H - 40, half.stats)
        draw_text(win, C.CONTROL_HINT, (C.WIN_W - 24, C.WIN_H - 40),
                  size=15, color=(130, 140, 175), anchor="topright")

        # 결과 배너
        if self.state == RESULT and self.banner:
            title, sub, color = self.banner
            widgets.result_banner(win, title, sub, color)

        # 타자 소개
        if self.state == READY:
            b = self.batter
            widgets.result_banner(
                win, f"{b['order']}번 {b['pos']}  {b['name']}",
                f"컨택 {b['contact']}  파워 {b['power']}  선구안 {b['eye']}",
                self.app.my_team["accent"])

    # ── 화면 흔들림 (App이 사용) ──────────────────────────
    def playfield_offset(self):
        return shake_offset(self.shake, magnitude=3)

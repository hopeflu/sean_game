"""
타석 진행 엔진 — 투타 대결 씬과 1경기 씬이 **공유**하는 부분.

씬에서 이 로직을 떼어낸 이유
---------------------------
1경기 모드는 반 이닝마다 공격/수비가 뒤바뀐다. 타석 진행과 포수 뒤 시점
렌더를 씬 안에 두면 두 씬이 같은 300줄을 복사해야 하므로, 여기로 옮기고
씬은 "누가 타자이고 누가 투수인가"만 알려준다.

호스트(씬) 규약
---------------
엔진은 아래 속성/메서드를 호스트에서 읽는다.

    host.half          HalfInning          현재 반 이닝
    host.batter        dict                현재 타자
    host.pitcher       dict                현재 투수
    host.bat_team      dict                공격 팀 (타자 유니폼 색)
    host.field_team    dict                수비 팀 (투수·포수 유니폼 색)
    host.batter_player  1 | 2 | None       타석에 선 사람(None=CPU)
    host.pitcher_player 1 | 2 | None       마운드에 선 사람(None=CPU)
    host.pitcher_ai    PitcherAI           투수가 CPU일 때 쓰는 AI
    host.batter_ai     BatterAI            타자가 CPU일 때 쓰는 AI
    host.next_batter()                     다음 타자로 넘긴다
    host.should_end_half() -> bool         (선택) 끝내기 등 조기 종료 판정

타석 상태
---------
READY   타자 소개 (짧은 정지)
SELECT  유저 투구일 때만 — 구종과 코스를 고른다
WINDUP  와인드업
FLIGHT  공이 날아온다. 타격/투구 어느 쪽이든 이 구간에서 스윙이 일어난다
BATTED  배트에 맞음 — 탑다운 구장 화면으로 타구 중계
RESULT  결과 배너
DONE    반 이닝 종료 (호스트가 이 상태를 보고 다음 처리를 한다)
"""

import pygame

from .. import config as C
from .. import sfx
from ..engine import batted_ball as bbmod
from ..engine import defense
from ..engine import swing as swingmod
from ..data.teams import contrast_uniform
from ..engine.pitch import PITCH_TYPES, cell_center as pitch_cell_center, make_pitch_at
from ..retro import vgradient, dashed_rect
from ..ui import sprites, field_view

READY, SELECT, WINDUP, FLIGHT, BATTED, RESULT, DONE = (
    "READY", "SELECT", "WINDUP", "FLIGHT", "BATTED", "RESULT", "DONE")

CURSOR_SPEED = 2.3          # 조준 커서 이동 속도(px/frame)
SWING_FRAMES = 9            # 스윙 모션 길이
WINDUP_FRAMES = 26

# 구종 선택 단축키 (투수 역할 공통)
PITCH_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)
# 수비 시프트 순환
SHIFT_PREV, SHIFT_NEXT = pygame.K_q, pygame.K_e

# ── 입력 장치는 **역할**을 따라간다 ───────────────────────
# 타자 = 마우스, 투수 = 키보드(구종) + 넘패드(코스).
# 2인용에서는 반 이닝마다 두 사람이 마우스와 키보드를 주고받는다.
# 장치가 갈려 있으므로 1P/2P 키를 따로 나눌 필요가 없다.
#
# 넘패드 배열이 스트라이크존 3x3 격자와 그대로 겹친다:
#     7 8 9   ← 높은 코스
#     4 5 6
#     1 2 3   ← 낮은 코스
NUMPAD_CELLS = {
    pygame.K_KP7: (0, 0), pygame.K_KP8: (1, 0), pygame.K_KP9: (2, 0),
    pygame.K_KP4: (0, 1), pygame.K_KP5: (1, 1), pygame.K_KP6: (2, 1),
    pygame.K_KP1: (0, 2), pygame.K_KP2: (1, 2), pygame.K_KP3: (2, 2),
}
# 넘패드가 없는 키보드를 위한 대체 키 (상단 숫자열은 구종이 쓰므로 U~M 3x3)
FALLBACK_CELLS = {
    pygame.K_u: (0, 0), pygame.K_i: (1, 0), pygame.K_o: (2, 0),
    pygame.K_j: (0, 1), pygame.K_k: (1, 1), pygame.K_l: (2, 1),
    pygame.K_m: (0, 2), pygame.K_COMMA: (1, 2), pygame.K_PERIOD: (2, 2),
}
OUTSIDE_KEYS = (pygame.K_KP0, pygame.K_KP_PERIOD, pygame.K_SLASH)
THROW_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)
SWING_KEYS = (pygame.K_SPACE, pygame.K_z)          # 마우스 없이도 칠 수 있게
BAT_ARROWS = {"left": (pygame.K_LEFT,), "right": (pygame.K_RIGHT,),
              "up": (pygame.K_UP,), "down": (pygame.K_DOWN,)}

# 유인구 모드에서 존 가장자리 바깥으로 밀어내는 거리(px)
OUTSIDE_PUSH = 16


class AtBatEngine:
    def __init__(self, host, rng):
        self.host = host
        self.rng = rng

        self.pitch = None
        self.contact = None
        self.bb = None                 # BattedBall
        self.plan = None               # CPU 타자의 스윙 계획 (유저 투구 시)

        # 조준 커서를 역할별로 따로 둔다. 2인용에서는 투수가 코스를 잡는 동안
        # 타자도 미리 배트를 겨눌 수 있어야 하므로 하나로는 부족하다.
        self.bat_x = C.ZONE_X + C.ZONE_W / 2      # 타자 배트 조준
        self.bat_y = C.ZONE_Y + C.ZONE_H / 2
        # 투수 목표 코스는 넘패드로 고른 3x3 칸에서 계산한다
        self.course_cell = (1, 1)      # (열, 행) — 넘패드 5 = 한복판
        self.outside = False           # True면 존 가장자리 바깥(유인구)
        self.pit_x, self.pit_y = self._course_xy()
        self.pitch_idx = 0             # 선택한 구종
        self.shift_idx = 0             # 선택한 수비 시프트

        self.swing_frame = -1
        self.swung = False
        self.shake = 0
        self.frame = 0
        # 마우스를 움직이면 배트 커서가 따라오고, 방향키를 쓰면 잠시 꺼진다.
        # (마우스가 없는 환경에서 커서가 구석에 박히는 것을 막는다)
        self._mouse_active = True

        self.state = READY
        self.timer = 50
        self.banner = None             # (제목, 부제, 색)
        self.last_pitch_name = "-"

    # ── 조회 ──────────────────────────────────────────────
    @property
    def selected_type(self) -> dict:
        return PITCH_TYPES[self.pitch_idx]

    @property
    def selected_shift(self) -> dict:
        return defense.SHIFTS[self.shift_idx]

    @property
    def batter_is_human(self) -> bool:
        return self.host.batter_player is not None

    @property
    def pitcher_is_human(self) -> bool:
        return self.host.pitcher_player is not None

    @property
    def two_humans(self) -> bool:
        """양쪽 다 사람 = 2인용 대전."""
        return self.batter_is_human and self.pitcher_is_human

    @property
    def course_label(self) -> str:
        """HUD 표시용 코스 이름."""
        col, row = self.course_cell
        v = ("높은", "가운데", "낮은")[row]
        h = ("몸쪽", "한복판", "바깥쪽")[col]
        base = f"{v} {h}"
        return base + (" · 유인구" if self.outside else "")

    def _course_xy(self):
        """
        고른 3x3 칸 → 홈플레이트 목표 좌표.
        유인구 모드면 칸의 방향으로 존 밖까지 밀어낸다(한복판은 그대로).
        """
        col, row = self.course_cell
        cx, cy = pitch_cell_center(col, row)
        if self.outside:
            cx += (col - 1) * OUTSIDE_PUSH
            cy += (row - 1) * OUTSIDE_PUSH
        return cx, cy

    # ── 입력 ──────────────────────────────────────────────
    def handle_event(self, event) -> bool:
        """처리했으면 True. 씬은 남은 키(ESC 등)를 직접 처리한다."""

        # 마우스를 움직이면 배트 커서 추종을 다시 켠다
        if event.type == pygame.MOUSEMOTION:
            self._mouse_active = True
            return False

        # ── 마우스: 타자 스윙 / 배너 넘기기 ───────────────
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == RESULT:
                self.timer = 0
                return True
            if (self.state == FLIGHT and self.batter_is_human
                    and not self.swung):
                self._do_swing(self.pitch.t, (self.bat_x, self.bat_y))
                return True
            return False

        if event.type != pygame.KEYDOWN:
            return False

        # 결과 배너는 아무 결정키로나 빨리 넘긴다
        if self.state == RESULT and event.key in SWING_KEYS + THROW_KEYS:
            self.timer = 0
            return True

        # ── 사람 투수 — 구종(숫자) · 코스(넘패드) · 시프트 · 투구 ──
        if self.state == SELECT and self.pitcher_is_human:
            if event.key in PITCH_KEYS:
                self.pitch_idx = PITCH_KEYS.index(event.key)
                sfx.play("move")
                return True

            cell = NUMPAD_CELLS.get(event.key, FALLBACK_CELLS.get(event.key))
            if cell is not None:
                self.course_cell = cell
                self.pit_x, self.pit_y = self._course_xy()
                sfx.play("move")
                return True

            if event.key in OUTSIDE_KEYS:
                self.outside = not self.outside
                self.pit_x, self.pit_y = self._course_xy()
                sfx.play("move")
                return True

            if event.key in (SHIFT_PREV, SHIFT_NEXT):
                step = -1 if event.key == SHIFT_PREV else 1
                self.shift_idx = (self.shift_idx + step) % len(defense.SHIFTS)
                sfx.play("move")
                return True

            if event.key in THROW_KEYS:
                self._throw_user_pitch()
                return True
            return False

        # ── 사람 타자 — 키보드 보조 스윙(마우스가 주 조작) ──
        if (self.state == FLIGHT and self.batter_is_human and not self.swung
                and event.key in SWING_KEYS):
            self._do_swing(self.pitch.t, (self.bat_x, self.bat_y))
            return True

        return False

    @staticmethod
    def _clamp(x, y, margin):
        return (max(C.ZONE_X - margin, min(C.ZONE_X + C.ZONE_W + margin, x)),
                max(C.ZONE_Y - margin, min(C.ZONE_Y + C.ZONE_H + margin, y)))

    @staticmethod
    def window_to_playfield(pos):
        """창 좌표 → 플레이필드 좌표. 창은 플레이필드의 정수배 확대이다."""
        x, y = pos
        return x / C.SCALE, y / C.SCALE

    def _read_batter_input(self, mouse_pos=None, keys=None):
        """
        타자 배트 조준 — **마우스가 주 조작**이다.

        mouse_pos / keys 는 테스트에서 주입하기 위한 것이다. SDL dummy 드라이버는
        set_pos 가 반영되지 않아 실제 마우스로는 좌표 변환을 검증할 수 없다.
        """
        if not self.batter_is_human:
            return

        if self._mouse_active:
            if mouse_pos is None:
                mouse_pos = pygame.mouse.get_pos()
            px, py = self.window_to_playfield(mouse_pos)
            self.bat_x, self.bat_y = self._clamp(px, py, 16)

        if keys is None:
            keys = pygame.key.get_pressed()
        dx = any(keys[k] for k in BAT_ARROWS["right"]) - \
             any(keys[k] for k in BAT_ARROWS["left"])
        dy = any(keys[k] for k in BAT_ARROWS["down"]) - \
             any(keys[k] for k in BAT_ARROWS["up"])
        if dx or dy:
            self._mouse_active = False     # 방향키를 쓰면 마우스 추종을 끈다
            self.bat_x, self.bat_y = self._clamp(
                self.bat_x + dx * CURSOR_SPEED,
                self.bat_y + dy * CURSOR_SPEED, 16)

    # ── 갱신 ──────────────────────────────────────────────
    def update(self):
        self.frame += 1
        if self.shake > 0:
            self.shake -= 1

        if self.state == READY:
            self.timer -= 1
            if self.timer <= 0:
                self._begin_pitch()

        elif self.state == SELECT:
            # 투수가 코스를 잡는 동안 타자도 미리 겨눌 수 있다
            self._read_batter_input()

        elif self.state == WINDUP:
            self.timer -= 1
            self._read_batter_input()
            if self.timer <= 0:
                sfx.play("pitch")
                self.state = FLIGHT

        elif self.state == FLIGHT:
            self._read_batter_input()
            if self.swing_frame >= 0:
                self.swing_frame += 1
            self.pitch.update()

            # CPU 타자는 계획한 시점에 스윙한다
            if (not self.batter_is_human and not self.swung
                    and self.plan is not None and self.pitch.t >= self.plan[0]):
                self._do_swing(self.plan[0], self.plan[1])

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
    def _reset_pitch_flags(self):
        self.swung = False
        self.swing_frame = -1
        self.contact = None
        self.bb = None
        self.plan = None

    def _begin_pitch(self):
        """다음 공. 유저가 투수면 구종/코스 선택 화면으로 넘어간다."""
        self._reset_pitch_flags()
        if self.pitcher_is_human:
            self.state = SELECT           # 사람이 구종·코스·시프트를 고른다
            return

        c = self.host.half.count
        self.pitch = self.host.pitcher_ai.choose(c.balls, c.strikes)
        self.last_pitch_name = self.pitch.type["name"]
        self._plan_cpu_swing()
        self.state = WINDUP
        self.timer = WINDUP_FRAMES

    def _throw_user_pitch(self):
        """유저가 고른 구종·코스로 공을 만든다."""
        ptype = self.selected_type
        self.pitch = make_pitch_at(ptype, (self.pit_x, self.pit_y),
                                   self.host.pitcher, self.rng)
        self.last_pitch_name = ptype["name"]
        self._plan_cpu_swing()

        sfx.play("select")
        self.state = WINDUP
        self.timer = WINDUP_FRAMES

    def _plan_cpu_swing(self):
        """타자가 CPU면 이 공에 대한 스윙 계획을 확정한다."""
        if self.batter_is_human:
            self.plan = None
            return
        c = self.host.half.count
        self.plan = self.host.batter_ai.plan(
            self.pitch, self.host.batter, c.balls, c.strikes)

    def _do_swing(self, swing_t, aim_xy):
        """스윙 실행 — 유저/CPU 공통 경로."""
        self.swung = True
        self.swing_frame = 0
        sfx.play("swing")

        self.contact = swingmod.judge(self.pitch, swing_t, aim_xy,
                                      self.host.batter["contact"])
        if not self.contact.made:
            return                       # 헛스윙 — 공은 계속 날아간다

        sfx.play("hit")
        self.shake = 8
        self.bb = bbmod.resolve(self.contact, self.host.batter, self.rng,
                                shift=self.selected_shift["key"])

        if self.bb.is_foul:
            self.host.half.count.add_strike(foul=True)
            self._banner("파울", f"{self.last_pitch_name} · {self.contact.label}", C.GRAY)
            self.state = RESULT
            self.timer = 42
            return

        self.state = BATTED              # 페어 타구 → 탑다운 중계
        self.timer = 0

    def _resolve_no_contact(self):
        """스윙을 안 했거나 헛스윙한 공이 포수 미트에 들어갔을 때."""
        half = self.host.half
        c = half.count
        if self.swung:
            if c.add_strike():
                sfx.play("out")
                half.apply_strikeout()
                self._banner("삼진 아웃", "헛스윙 삼진", C.RED)
            else:
                sfx.play("strike")
                self._banner("헛스윙", f"{self.last_pitch_name} · 스트라이크", C.YELLOW)
        elif self.pitch.in_strike_zone():
            if c.add_strike():
                sfx.play("out")
                half.apply_strikeout()
                self._banner("삼진 아웃", "루킹 삼진", C.RED)
            else:
                sfx.play("strike")
                self._banner("스트라이크", f"{self.last_pitch_name} · 존 통과", C.YELLOW)
        else:
            if c.add_ball():
                sfx.play("select")
                half.apply_walk()
                self._banner("볼넷", "출루!", C.CYAN)
            else:
                sfx.play("ball")
                self._banner("볼", f"{self.last_pitch_name} · 존 바깥", C.GREEN)

        self.state = RESULT
        self.timer = 46

    def _show_batted_result(self):
        """탑다운 중계가 끝난 뒤 실제 결과를 규칙에 반영한다."""
        bb = self.bb
        half = self.host.half
        if bb.is_hit:
            if bb.result == "HR":
                sfx.play("hr")
                self.shake = 14
            half.apply_hit(bb)
            color = C.YELLOW if bb.result == "HR" else C.GREEN
        else:
            sfx.play("out")
            half.apply_out(bb.desc)
            color = C.RED

        sub = (f"타구속도 {int(bb.exit_v * 100)}  발사각 {bb.launch:.0f}°  "
               f"비거리 {bb.distance:.0f}m")
        self._banner(bb.desc, sub, color)
        self.state = RESULT
        self.timer = 82

    def _banner(self, title, sub, color):
        self.banner = (title, sub, color)

    def _advance(self):
        """결과 배너 종료 — 다음 투구 / 다음 타자 / 반 이닝 종료."""
        self.banner = None

        # 끝내기처럼 3아웃 전에 끝나는 경우를 호스트가 알려준다
        early = getattr(self.host, "should_end_half", None)
        if self.host.half.over or (early and early()):
            self.state = DONE
            return

        # 카운트가 리셋되었다면 타석이 끝난 것 → 다음 타자
        c = self.host.half.count
        if c.balls == 0 and c.strikes == 0:
            self.host.next_batter()
            self._reset_pitch_flags()
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
        bat_team = self.host.bat_team
        # 두 팀 주색이 비슷하면(예: KIA vs LG, 둘 다 빨강) 투수와 타자를
        # 구분할 수 없으므로 수비 팀에 대비 유니폼을 입힌다.
        field_team = contrast_uniform(self.host.field_team, bat_team)

        # ── 배경 ──────────────────────────────────────────
        # 야간 하늘 → 관중석 → 외야 펜스 → 내야 잔디 → 홈플레이트 흙
        vgradient(pf, (0, 0, C.PF_W, 30), (14, 14, 32), (36, 44, 84), bands=5)
        for x in range(0, C.PF_W, 4):                    # 관중 실루엣
            pygame.draw.rect(pf, (50, 50, 76), (x, 24 + (x % 3), 3, 14))
        pygame.draw.rect(pf, (26, 30, 52), (0, 38, C.PF_W, 6))   # 외야 펜스
        pygame.draw.rect(pf, (90, 96, 120), (0, 38, C.PF_W, 1))

        for i, y in enumerate(range(44, 176, 11)):       # 잔디 줄무늬
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
            wind = 1.0 - self.timer / WINDUP_FRAMES
        elif self.state == FLIGHT:
            wind = 1.0
        else:
            wind = 0.0
        sprites.draw_pitcher(pf, C.RELEASE_X, C.MOUND_Y + 6, field_team, wind_up=wind)

        # ── 스트라이크존 ──────────────────────────────────
        dashed_rect(pf, (C.ZONE_X, C.ZONE_Y, C.ZONE_W, C.ZONE_H),
                    (200, 200, 220), dash=3, gap=3)
        for i in range(1, C.ZONE_COLS):
            x = C.ZONE_X + i * C.CELL_W
            pygame.draw.line(pf, (90, 90, 110), (x, C.ZONE_Y + 2),
                             (x, C.ZONE_Y + C.ZONE_H - 2))
        for i in range(1, C.ZONE_ROWS):
            y = C.ZONE_Y + i * C.CELL_H
            pygame.draw.line(pf, (90, 90, 110), (C.ZONE_X + 2, y),
                             (C.ZONE_X + C.ZONE_W - 2, y))

        # ── 공 ────────────────────────────────────────────
        if (self.pitch and self.state == FLIGHT
                and not (self.contact and self.contact.made)):
            x, y = self.pitch.position()
            sprites.draw_ball(pf, x, y, self.pitch.radius(),
                              spin_phase=self.frame * self.pitch.type["spin"],
                              trail=self.pitch.trail)

        # ── 타자 / 포수 ───────────────────────────────────
        sp = 0.0 if self.swing_frame < 0 else min(1.0, self.swing_frame / SWING_FRAMES)
        sprites.draw_batter(pf, 105, C.BATTER_Y, bat_team, swing_phase=sp)
        sprites.draw_catcher(pf, 160, C.CATCHER_Y, field_team)

        # ── 조준 커서 ─────────────────────────────────────
        # 배트 조준은 노란색, 투구 목표 코스는 하늘색으로 역할을 구분한다.
        # 투구 커서는 **SELECT 동안만** 보인다. 던진 뒤에도 계속 보이면 타자가
        # 도착 지점을 그대로 읽어버리므로, 투수는 마지막 순간에 코스를 옮겨
        # 속일 수 있어야 한다(2인용에서 특히 중요).
        if self.pitcher_is_human and self.state == SELECT:
            sprites.draw_cursor(pf, int(self.pit_x), int(self.pit_y),
                                color=C.CYAN, frame=self.frame)
        if self.batter_is_human and self.state in (SELECT, WINDUP, FLIGHT):
            sprites.draw_cursor(pf, int(self.bat_x), int(self.bat_y),
                                color=C.YELLOW, frame=self.frame)

        # 타격 순간 섬광 — 공을 친 직후 몇 프레임만, 작게
        if (self.state == FLIGHT and self.contact
                and self.contact.made and self.shake > 3):
            cx = self.bat_x if self.batter_is_human else self.pitch.plate_x
            cy = self.bat_y if self.batter_is_human else self.pitch.plate_y
            r = 2 + self.shake // 2
            pygame.draw.circle(pf, C.WHITE, (int(cx), int(cy)), r)
            pygame.draw.circle(pf, C.YELLOW, (int(cx), int(cy)), r + 2, 1)

    def _draw_batted(self, pf):
        """탑다운 구장 중계."""
        field_view.draw_field(pf,
                              contrast_uniform(self.host.field_team,
                                               self.host.bat_team))
        progress = min(1.0, self.timer / 58.0)
        field_view.draw_ball_flight(pf, self.bb, progress)
        field_view.draw_runner(pf, self.host.bat_team,
                               min(1.0, self.timer / 70.0),
                               self.bb.bases if self.bb.is_hit else 1)
        if progress >= 1.0:
            field_view.draw_landing_mark(pf, self.bb, self.frame)

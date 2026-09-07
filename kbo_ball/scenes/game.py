"""
1경기 씬 (Phase 2) — 9이닝 정규 경기.

유저는 **홈(후공)** 을 맡는다. 그래서 1회초부터 곧바로 투구를 하게 되고,
9회말에 끝내기가 가능해 마지막까지 긴장이 유지된다.

반 이닝마다 공수가 바뀌지만 타석 진행과 렌더는 `atbat.AtBatEngine` 이 그대로
처리한다. 이 씬은 "지금 누가 치고 누가 던지는가"를 알려주고(호스트 규약),
반 이닝이 끝나면 전광판에 기록하고 다음 반 이닝을 세팅한다.

씬 상태
-------
INTRO     이닝 시작 안내 ("3회말 — KIA 공격")
PLAY      타석 진행 (엔진에 위임)
HALF_END  반 이닝 종료 요약
"""

import random
import pygame

from .. import config as C
from .. import sfx
from ..engine.batter_ai import BatterAI
from ..engine.pitch import PITCH_TYPES, PitcherAI
from ..engine.rules import HalfInning, Scoreboard, Stats
from ..fonts import draw_text
from ..retro import shake_offset
from ..ui import widgets
from . import atbat
from .base import Scene

INTRO, PLAY, HALF_END = "INTRO", "PLAY", "HALF_END"

# CPU 타자 강도 1~5. 8경기 시뮬레이션 기준:
#   3 → CPU 0.9점/.173 (유저가 너무 쉽게 이긴다)
#   4 → CPU 1.9점/.239, 유저 6승 2패  ← 기본값
#   5 → CPU 2.5점/.306, 유저 3승 5패 (사람보다 정밀한 봇 기준이라 과하다)
CPU_DIFFICULTY = 4


class GameScene(Scene):
    hide_cursor = True    # 타자 조준이 마우스라 OS 커서를 숨긴다

    def __init__(self, app):
        super().__init__(app)
        self.rng = random.Random()
        self.board = Scoreboard(innings=9, max_innings=12)

        # 1P는 홈(후공), 2P(또는 CPU)는 원정(선공).
        # 1인용에서 유저가 홈이면 1회초 투구부터 시작하고 9회말 끝내기가 살아난다.
        self.two_player = bool(getattr(app, "two_player", False))
        self.user_side = "home"
        self.teams = {"away": app.opp_team, "home": app.my_team}
        self.lineups = {"away": app.opp_lineup, "home": app.lineup}
        self.pitchers = {"away": app.pitcher, "home": app.my_pitcher}
        self.order = {"away": 0, "home": 0}          # 팀별 타순 (이닝 넘어도 이어짐)
        self.game_stats = {"away": Stats(), "home": Stats()}

        # 유저가 타격할 때 상대할 CPU 투수 / 유저가 투구할 때 상대할 CPU 타자
        self.pitcher_ai = PitcherAI(self.pitchers["away"])
        self.batter_ai = BatterAI(difficulty=CPU_DIFFICULTY, rng=self.rng)

        self.half = HalfInning(rng=self.rng)
        self.engine = atbat.AtBatEngine(self, self.rng)

        self.state = INTRO
        self.timer = 80
        self.half_summary = ""
        # HALF_END 화면에서 쓸 "방금 끝난 반 이닝" 정보
        self.finished_text = self.board.half_text()
        self.finished_team = self.bat_team

    # ── 호스트 규약 ───────────────────────────────────────
    @property
    def batting_side(self) -> str:
        return "away" if self.board.top else "home"

    @property
    def fielding_side(self) -> str:
        return "home" if self.board.top else "away"

    @property
    def bat_team(self):
        return self.teams[self.batting_side]

    @property
    def field_team(self):
        return self.teams[self.fielding_side]

    @property
    def batter(self):
        lineup = self.lineups[self.batting_side]
        return lineup[self.order[self.batting_side] % len(lineup)]

    @property
    def pitcher(self):
        return self.pitchers[self.fielding_side]

    # 키가 사람을 따라가도록 1P=홈, 2P=원정으로 고정한다.
    # 역할(타자/투수)은 반 이닝마다 바뀌지만 각자 쓰는 키는 그대로다.
    def _player_of(self, side: str):
        if self.two_player:
            return 1 if side == "home" else 2
        return 1 if side == self.user_side else None

    @property
    def batter_player(self):
        return self._player_of(self.batting_side)

    @property
    def pitcher_player(self):
        return self._player_of(self.fielding_side)

    @property
    def user_bats(self) -> bool:
        """1인용 HUD 표기용 — 지금 사람이 타격 중인가."""
        return self.batter_player is not None

    def next_batter(self):
        self.order[self.batting_side] += 1

    def should_end_half(self) -> bool:
        """끝내기 — 말 공격 도중 홈팀이 앞서면 3아웃 전에도 경기가 끝난다."""
        return self.board.check_walkoff(self.half.runs)

    # ── 입력 ──────────────────────────────────────────────
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from .title import TitleScene
            self.next_scene = TitleScene(self.app)
            return

        if self.state == INTRO or self.state == HALF_END:
            # 안내 화면은 SPACE로 건너뛴다
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE,
                                                              pygame.K_RETURN):
                self.timer = 0
            return

        self.engine.handle_event(event)

    # ── 갱신 ──────────────────────────────────────────────
    def update(self):
        if self.state == INTRO:
            self.timer -= 1
            if self.timer <= 0:
                self.state = PLAY

        elif self.state == PLAY:
            self.engine.update()
            if self.engine.state == atbat.DONE:
                self._end_half()

        elif self.state == HALF_END:
            self.timer -= 1
            if self.timer <= 0:
                self._start_next_half()

    def _end_half(self):
        """반 이닝 종료 — 전광판 기록, 끝내기 판정, 누적 성적 합산."""
        side = self.batting_side
        walkoff = self.board.check_walkoff(self.half.runs)

        # board.advance() 이후에는 half_text()/bat_team 이 **다음** 반 이닝을
        # 가리킨다. HALF_END 화면은 방금 끝난 반 이닝을 보여줘야 하므로
        # 진행 전 값을 붙잡아 둔다.
        self.finished_text = self.board.half_text()
        self.finished_team = self.bat_team

        self.game_stats[side].merge(self.half.stats)

        if walkoff:
            self.board.finish_walkoff(self.half.runs)
            self.half_summary = "끝내기!"
            sfx.play("hr")
        else:
            self.board.record(self.half.runs)
            self.board.advance()
            self.half_summary = (f"{self.half.runs}점" if self.half.runs
                                 else "무득점")
            sfx.play("select")

        self.state = HALF_END
        self.timer = 80

    def _start_next_half(self):
        """다음 반 이닝 준비. 경기가 끝났으면 결과 화면으로."""
        if self.board.final:
            from .game_result import GameResultScene
            self.next_scene = GameResultScene(
                self.app, self.board, self.teams, self.game_stats,
                self.user_side, two_player=self.two_player)
            return

        self.half = HalfInning(rng=self.rng)
        self.engine = atbat.AtBatEngine(self, self.rng)
        self.state = INTRO
        self.timer = 70

    # ── 렌더 ──────────────────────────────────────────────
    def draw_playfield(self, pf):
        self.engine.draw_playfield(pf)

    def draw_hud(self, win):
        half = self.half
        board = self.board

        widgets.count_board(win, 24, 24, half, self.pitcher["name"], self.batter)
        widgets.runner_board(win, C.WIN_W - 224, 24, half)
        widgets.linescore(win, 262, 24, board,
                          self.teams["away"], self.teams["home"],
                          self.game_stats["away"], self.game_stats["home"])

        # 지금 이닝 / 역할 — 반 이닝 종료 화면에서는 방금 끝난 쪽을 보여준다
        if self.two_player:
            role = (f"{self.batter_player}P 타격   ·   "
                    f"{self.pitcher_player}P 투구·수비")
        else:
            role = "내 차례 — " + ("타격" if self.user_bats else "투구")
        if self.state == HALF_END:
            head_team, head_text, head_sub = (
                self.finished_team, self.finished_text, "종료")
        else:
            head_team, head_text, head_sub = (
                self.bat_team, board.half_text(), role)

        draw_text(win, f"{head_text}  ·  {head_team['code']} 공격",
                  (262 + 218, 112), size=18, color=head_team["accent"],
                  bold=True, anchor="midtop")
        draw_text(win, head_sub, (262 + 218, 138), size=15,
                  color=(170, 180, 210), anchor="midtop")

        # 좌측 — 타석 기록
        widgets.panel(win, (24, 204, 200, 152))
        draw_text(win, "타석 기록", (38, 216), size=16, color=C.CYAN, bold=True)
        widgets.pitch_log(win, 38, 242, half.log)

        # 하단 — 투수가 사람이면 구종·시프트 선택 줄, 아니면 타격 성적 한 줄
        widgets.panel(win, (0, C.WIN_H - 58, C.WIN_W, 58), alpha=235)
        if self.pitcher_player is not None:
            widgets.pitch_selector(win, 14, C.WIN_H - 46,
                                   PITCH_TYPES, self.engine.pitch_idx, w=470)
            widgets.shift_indicator(win, 494, C.WIN_H - 46,
                                    self.engine.selected_shift)
            # 시프트 표시(x 494~690) 오른쪽 좁은 칸에만 그린다
            draw_text(win, C.CONTROL_HINT_ROLE_PITCH, (C.WIN_W - 14, C.WIN_H - 48),
                      size=14, color=(150, 160, 195), anchor="topright")
            draw_text(win, C.CONTROL_HINT_ROLE_BAT, (C.WIN_W - 14, C.WIN_H - 28),
                      size=14, color=(150, 160, 195), anchor="topright")
        else:
            widgets.stat_line(win, 24, C.WIN_H - 40, half.stats)
            draw_text(win, C.CONTROL_HINT_BAT, (C.WIN_W - 24, C.WIN_H - 40),
                      size=15, color=(130, 140, 175), anchor="topright")

        # ── 배너 ──────────────────────────────────────────
        if self.state == INTRO:
            widgets.result_banner(
                win, f"{board.half_text()}",
                f"{self.bat_team['name']} 공격  ·  내 차례 {role}",
                self.bat_team["accent"])
        elif self.state == HALF_END:
            widgets.result_banner(
                win, self.half_summary,
                f"{self.teams['away']['code']} {board.total('away')}"
                f"  -  "
                f"{board.total('home')} {self.teams['home']['code']}",
                C.YELLOW if self.half.runs else C.GRAY)
        elif self.engine.state == atbat.RESULT and self.engine.banner:
            title, sub, color = self.engine.banner
            widgets.result_banner(win, title, sub, color)
        elif self.engine.state == atbat.READY:
            b = self.batter
            widgets.result_banner(
                win, f"{b['order']}번 {b['pos']}  {b['name']}",
                f"컨택 {b['contact']}  파워 {b['power']}  선구안 {b['eye']}",
                self.bat_team["accent"])
        elif self.engine.state == atbat.SELECT:
            # 유저 투구 — 무엇을 해야 하는지 짧게 안내
            eng = self.engine
            widgets.panel(win, (C.WIN_W // 2 - 250, C.WIN_H - 152, 500, 82))
            draw_text(win,
                      f"{eng.selected_type['name']}  ·  {eng.course_label}",
                      (C.WIN_W // 2, C.WIN_H - 144), size=20,
                      color=eng.selected_type["color"], bold=True, anchor="midtop")
            draw_text(win, "넘패드 1-9 코스   0 유인구   1-5 구종",
                      (C.WIN_W // 2, C.WIN_H - 116), size=14,
                      color=(170, 180, 210), anchor="midtop")
            draw_text(win, "Q E 수비 시프트   ENTER 투구",
                      (C.WIN_W // 2, C.WIN_H - 96), size=14,
                      color=(170, 180, 210), anchor="midtop")

    def playfield_offset(self):
        return shake_offset(self.engine.shake, magnitude=3)

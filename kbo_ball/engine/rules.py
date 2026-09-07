"""
야구 규칙 상태 기계.

Phase 1(투타 대결)에서는 `HalfInning` 하나만 쓴다.
Phase 2(1경기 완주)에서는 `Scoreboard` 가 이닝을 누적하고 공수를 교대시키므로,
이 파일만 확장하면 되도록 규칙 로직을 씬(scene)에서 완전히 분리해 두었다.
"""

import random

from .. import config as C

# 안타 종류별 주자 추가 진루 확률.
# 모든 주자를 정확히 n루만 보내면 2루 주자가 단타에 홈을 밟지 못해
# 득점이 거의 나오지 않는다(실측 이닝당 0.07점). 실제 야구에서는 단타에
# 2루 주자가 홈까지 들어오는 경우가 흔하므로, 주자별로 한 루를 더 갈
# 기회를 준다.
EXTRA_BASE_CHANCE = {1: 0.55, 2: 0.60, 3: 1.0, 4: 1.0}


# ── 타석 하나의 카운트 ────────────────────────────────────
class Count:
    def __init__(self):
        self.balls = 0
        self.strikes = 0

    def reset(self):
        self.balls = 0
        self.strikes = 0

    def add_ball(self) -> bool:
        """볼 추가. 볼넷이면 True."""
        self.balls += 1
        return self.balls >= C.BALLS_PER_WALK

    def add_strike(self, foul: bool = False) -> bool:
        """
        스트라이크 추가. 삼진이면 True.
        파울은 2스트라이크에서는 카운트가 늘지 않는다(실제 규칙과 동일).
        """
        if foul and self.strikes >= C.STRIKES_PER_OUT - 1:
            return False
        self.strikes += 1
        return self.strikes >= C.STRIKES_PER_OUT

    def __str__(self):
        return f"{self.balls}-{self.strikes}"


# ── 타격 성적 누적 ────────────────────────────────────────
class Stats:
    """타자 팀 기준 누적 기록."""

    def __init__(self):
        self.pa = 0        # 타석
        self.ab = 0        # 타수 (볼넷 제외)
        self.hits = 0
        self.doubles = 0
        self.triples = 0
        self.hr = 0
        self.walks = 0
        self.strikeouts = 0
        self.rbi = 0
        self.runs = 0

    # 누적 대상 필드 — merge()가 이 목록만 더한다
    _FIELDS = ("pa", "ab", "hits", "doubles", "triples", "hr",
               "walks", "strikeouts", "rbi", "runs")

    @property
    def avg(self) -> float:
        return self.hits / self.ab if self.ab else 0.0

    def avg_text(self) -> str:
        """.333 형태의 야구식 타율 표기."""
        if not self.ab:
            return ".000"
        return f"{self.avg:.3f}".lstrip("0")

    def merge(self, other: "Stats"):
        """반 이닝 기록을 경기 누적 기록에 더한다(1경기 모드에서 사용)."""
        for f in self._FIELDS:
            setattr(self, f, getattr(self, f) + getattr(other, f))


# ── 반 이닝 (공격 한 번) ──────────────────────────────────
class HalfInning:
    """아웃 카운트와 주자 상태를 관리한다."""

    def __init__(self, rng=None):
        self.outs = 0
        self.bases = [False, False, False]   # 1루, 2루, 3루
        self.runs = 0
        self.count = Count()
        self.stats = Stats()
        self.log = []                        # 타석 결과 문자열 목록
        self.rng = rng or random.Random()    # 추가 진루 판정용

    @property
    def over(self) -> bool:
        return self.outs >= C.OUTS_PER_INNING

    @property
    def runners_text(self) -> str:
        occupied = [n for n, b in zip(("1루", "2루", "3루"), self.bases) if b]
        return " ".join(occupied) if occupied else "주자 없음"

    # ── 결과 반영 ─────────────────────────────────────────
    def apply_out(self, desc: str):
        self.outs += 1
        self.stats.pa += 1
        self.stats.ab += 1
        self._log(desc)
        self.count.reset()

    def apply_strikeout(self):
        self.outs += 1
        self.stats.pa += 1
        self.stats.ab += 1
        self.stats.strikeouts += 1
        self._log("삼진 아웃")
        self.count.reset()

    def apply_walk(self):
        self.stats.pa += 1
        self.stats.walks += 1
        self._advance_forced()
        self._log("볼넷")
        self.count.reset()

    def apply_hit(self, bb):
        """BattedBall(안타)을 주루에 반영하고 타점을 계산한다."""
        self.stats.pa += 1
        self.stats.ab += 1
        self.stats.hits += 1
        if bb.bases == 2:
            self.stats.doubles += 1
        elif bb.bases == 3:
            self.stats.triples += 1
        elif bb.bases == 4:
            self.stats.hr += 1

        scored = self._advance(bb.bases)
        self.stats.rbi += scored
        self.runs += scored
        self.stats.runs += scored

        suffix = f"  ({scored}타점)" if scored else ""
        self._log(bb.desc + suffix)
        self.count.reset()

    # ── 주루 처리 ─────────────────────────────────────────
    def _advance(self, n: int) -> int:
        """
        기존 주자를 n루(+추가 진루) 보내고 타자를 (n-1)루에 놓는다.
        홈을 밟은 주자 수를 반환한다.

        추가 진루는 주자마다 독립으로 굴린다. 앞선 주자를 추월할 수 없으므로
        3루 주자부터 역순으로 처리하고, 도착 루가 이미 차 있으면 추가 진루를
        취소해 최소 진루(i+n)에 머무른다.

        모든 주자가 최소 i+n(>= n)루에 서므로 타자 자리인 n-1루는 항상 비어
        있다 — 그래서 타자는 별도 충돌 처리 없이 그대로 놓을 수 있다.
        """
        scored = 0
        new = [False, False, False]
        extra_p = EXTRA_BASE_CHANCE.get(n, 0.0)

        for i in range(2, -1, -1):
            if not self.bases[i]:
                continue
            dest = i + n
            if dest < 3 and self.rng.random() < extra_p:
                dest += 1              # 한 루 더
            if dest >= 3:
                scored += 1
                continue
            if new[dest]:              # 앞 주자에 막히면 추가 진루 취소
                dest = i + n
            new[dest] = True

        if n < 4:
            new[n - 1] = True          # 타자 주자
        else:
            scored += 1                # 홈런은 타자도 득점

        self.bases = new
        return scored

    def _advance_forced(self) -> int:
        """볼넷 — 밀어내기 상황에서만 주자가 움직인다."""
        scored = 0
        if not self.bases[0]:
            self.bases[0] = True
        elif not self.bases[1]:
            self.bases[1] = True
        elif not self.bases[2]:
            self.bases[2] = True
        else:
            scored = 1                 # 만루 밀어내기
            self.runs += 1
            self.stats.runs += 1
            self.stats.rbi += 1
        return scored

    def _log(self, text: str):
        self.log.append(f"{self.stats.pa}타석  {text}")
        if len(self.log) > 8:
            self.log.pop(0)


# ── 정규 경기 전광판 ──────────────────────────────────────
class Scoreboard:
    """
    이닝별 득점을 누적하고 경기 종료를 판정한다.

    구현한 규칙
    -----------
    * 홈팀이 9회초를 마친 시점에 앞서 있으면 **9회말을 하지 않고** 경기 종료
    * 9회말(또는 연장 말)에 홈팀이 역전하는 순간 **끝내기**로 즉시 종료
    * 정규 이닝 후 동점이면 연장, `max_innings`까지 가고도 동점이면 **무승부**

    리스트를 미리 채우지 않고 append로 늘리기 때문에 연장 이닝이 자연히 들어간다.
    """

    def __init__(self, innings: int = 9, max_innings: int = 12):
        self.regulation = innings
        self.max_innings = max_innings
        self.away: list = []             # 원정(선공) 이닝별 득점
        self.home: list = []             # 홈(후공)  이닝별 득점
        self.inning = 1
        self.top = True                  # True=초, False=말
        self.final = False               # 경기 종료 여부
        self.walkoff = False             # 끝내기로 끝났는가

    # ── 조회 ──────────────────────────────────────────────
    def total(self, side: str) -> int:
        row = self.away if side == "away" else self.home
        return sum(r for r in row if r is not None)

    @property
    def innings_played(self) -> int:
        """전광판에 표시할 이닝 수 (최소 정규 이닝)."""
        return max(self.regulation, len(self.away), len(self.home), self.inning)

    def row(self, side: str, length: int) -> list:
        """길이를 맞춘 이닝별 득점 행. 아직 안 한 이닝은 None."""
        r = list(self.away if side == "away" else self.home)
        r += [None] * (length - len(r))
        return r[:length]

    @property
    def winner(self) -> str:
        """'away' | 'home' | 'draw' — 종료되지 않았으면 진행 중 기준으로 판단."""
        a, h = self.total("away"), self.total("home")
        if a == h:
            return "draw"
        return "away" if a > h else "home"

    # ── 진행 ──────────────────────────────────────────────
    def record(self, runs: int):
        """방금 끝난 반 이닝의 득점을 기록한다."""
        row = self.away if self.top else self.home
        # 홈팀이 9회말을 건너뛴 경우 등 빈 칸이 생기지 않도록 길이를 맞춘다
        while len(row) < self.inning - 1:
            row.append(None)
        if len(row) < self.inning:
            row.append(runs)
        else:
            row[self.inning - 1] = runs

    def check_walkoff(self, live_runs: int) -> bool:
        """
        말 공격 도중 호출. 홈팀이 앞서는 순간 끝내기.
        live_runs 는 아직 record 되지 않은 현재 반 이닝의 득점.
        """
        if self.top or self.inning < self.regulation:
            return False
        return self.total("home") + live_runs > self.total("away")

    def finish_walkoff(self, live_runs: int):
        """끝내기로 경기를 끝낸다."""
        self.record(live_runs)
        self.walkoff = True
        self.final = True

    def advance(self):
        """반 이닝 종료 후 다음 반 이닝으로. 종료 조건도 여기서 판정한다."""
        if self.final:
            return

        if self.top:
            # 9회초 종료 시점에 홈팀이 앞서면 말 공격이 필요 없다
            if (self.inning >= self.regulation
                    and self.total("home") > self.total("away")):
                self.final = True
                return
            self.top = False
            return

        # 말 공격 종료
        if self.inning >= self.regulation and self.total("away") != self.total("home"):
            self.final = True
            return
        if self.inning >= self.max_innings:
            self.final = True          # 연장 한계 — 동점이면 무승부
            return

        self.inning += 1
        self.top = True

    # ── 표시용 ────────────────────────────────────────────
    def half_text(self) -> str:
        return f"{self.inning}회{'초' if self.top else '말'}"

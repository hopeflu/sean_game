"""
칩튠 효과음 — 외부 오디오 파일 없이 파형을 직접 합성한다.

패미컴 음원을 흉내내기 위해 사각파(square)와 노이즈만 쓴다.
사운드 장치가 없는 환경(헤드리스, 컨테이너)에서도 게임이 멈추지 않도록
초기화·재생 전부 예외를 삼킨다.
"""

import array
import math
import random

import pygame

SAMPLE_RATE = 22050

_enabled = False
_cache: dict = {}


def init():
    """믹서 초기화. 실패하면 무음 모드로 계속 진행한다."""
    global _enabled
    try:
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 256)
        pygame.mixer.init()
        _enabled = True
    except Exception:
        _enabled = False
    return _enabled


def _square(freq, ms, vol=0.25, duty=0.5, decay=True):
    """사각파 한 음. int16 모노 버퍼를 만들어 Sound로 감싼다."""
    n = int(SAMPLE_RATE * ms / 1000)
    buf = array.array("h")
    period = SAMPLE_RATE / max(1.0, freq)
    for i in range(n):
        env = (1.0 - i / n) if decay else 1.0
        phase = (i % period) / period
        amp = vol * env * (1.0 if phase < duty else -1.0)
        buf.append(int(max(-1.0, min(1.0, amp)) * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _noise(ms, vol=0.3, decay=True):
    """노이즈 — 배트 타격음·환호에 사용."""
    n = int(SAMPLE_RATE * ms / 1000)
    buf = array.array("h")
    for i in range(n):
        env = (1.0 - i / n) if decay else 1.0
        buf.append(int(random.uniform(-1, 1) * vol * env * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _sweep(f0, f1, ms, vol=0.25):
    """주파수가 미끄러지는 사각파 — 홈런 팡파르 상승음."""
    n = int(SAMPLE_RATE * ms / 1000)
    buf = array.array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f0 + (f1 - f0) * t
        phase += freq / SAMPLE_RATE
        env = 1.0 - t * 0.5
        amp = vol * env * (1.0 if (phase % 1.0) < 0.5 else -1.0)
        buf.append(int(amp * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


# ── 효과음 정의 ───────────────────────────────────────────
_BUILDERS = {
    "pitch":   lambda: _square(220, 60, 0.12, duty=0.25),
    "swing":   lambda: _noise(70, 0.16),
    "hit":     lambda: _noise(90, 0.42),
    "hr":      lambda: _sweep(300, 1100, 420, 0.28),
    "strike":  lambda: _square(660, 90, 0.20),
    "ball":    lambda: _square(300, 90, 0.16),
    "out":     lambda: _square(160, 220, 0.20, duty=0.25),
    "select":  lambda: _square(880, 55, 0.18),
    "move":    lambda: _square(520, 35, 0.12),
}


def play(key: str):
    """효과음 재생. 최초 호출 시 파형을 만들어 캐싱한다."""
    if not _enabled:
        return
    try:
        snd = _cache.get(key)
        if snd is None:
            builder = _BUILDERS.get(key)
            if builder is None:
                return
            snd = _cache[key] = builder()
        snd.play()
    except Exception:
        pass

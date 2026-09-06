"""
고전 8비트 느낌을 내는 렌더 유틸.

핵심 아이디어
-------------
* 플레이필드는 320x240 서피스에 그린 뒤 **정수배 nearest-neighbor 확대**한다.
  smoothscale을 쓰면 픽셀이 뭉개져 8비트 감성이 사라지므로 반드시 scale 사용.
* 스캔라인 오버레이는 매 프레임 만들지 않고 한 번 만들어 캐싱한다.
"""

import pygame

from . import config as C


def new_playfield() -> pygame.Surface:
    """플레이필드용 저해상도 서피스."""
    return pygame.Surface((C.PF_W, C.PF_H)).convert()


def blit_scaled(dest: pygame.Surface, playfield: pygame.Surface):
    """저해상도 플레이필드를 창 전체에 정수배로 확대해 올린다."""
    scaled = pygame.transform.scale(playfield, (C.WIN_W, C.WIN_H))
    dest.blit(scaled, (0, 0))


# ── 스캔라인 ──────────────────────────────────────────────
_scanlines = None


def scanline_overlay() -> pygame.Surface:
    """CRT 느낌의 가로 주사선. 창 크기에 맞춰 한 번만 생성해 재사용."""
    global _scanlines
    if _scanlines is None:
        surf = pygame.Surface((C.WIN_W, C.WIN_H), pygame.SRCALPHA)
        for y in range(0, C.WIN_H, C.SCALE):
            pygame.draw.line(surf, (0, 0, 0, 54), (0, y), (C.WIN_W, y))
        _scanlines = surf
    return _scanlines


# ── 그리기 도우미 ─────────────────────────────────────────
def vgradient(surf, rect, top_color, bottom_color, bands: int = 12):
    """
    세로 그라디언트를 **띠(band) 단위**로 칠한다.
    부드러운 그라디언트 대신 계단식으로 칠해야 8비트 팔레트처럼 보인다.
    """
    x, y, w, h = rect
    for i in range(bands):
        t = i / max(1, bands - 1)
        col = tuple(int(a + (b - a) * t) for a, b in zip(top_color, bottom_color))
        bh = h // bands + (1 if i < h % bands else 0)
        pygame.draw.rect(surf, col, (x, y, w, bh))
        y += bh


def bevel_box(surf, rect, fill, light, dark, border: int = 1):
    """고전 UI의 입체 테두리 상자."""
    x, y, w, h = rect
    pygame.draw.rect(surf, fill, rect)
    for i in range(border):
        pygame.draw.line(surf, light, (x + i, y + i), (x + w - 1 - i, y + i))
        pygame.draw.line(surf, light, (x + i, y + i), (x + i, y + h - 1 - i))
        pygame.draw.line(surf, dark, (x + i, y + h - 1 - i), (x + w - 1 - i, y + h - 1 - i))
        pygame.draw.line(surf, dark, (x + w - 1 - i, y + i), (x + w - 1 - i, y + h - 1 - i))


def dashed_rect(surf, rect, color, dash: int = 3, gap: int = 3, width: int = 1):
    """점선 사각형 — 스트라이크존 표시에 사용."""
    x, y, w, h = rect
    for px in range(x, x + w, dash + gap):
        pygame.draw.line(surf, color, (px, y), (min(px + dash, x + w), y), width)
        pygame.draw.line(surf, color, (px, y + h), (min(px + dash, x + w), y + h), width)
    for py in range(y, y + h, dash + gap):
        pygame.draw.line(surf, color, (x, py), (x, min(py + dash, y + h)), width)
        pygame.draw.line(surf, color, (x + w, py), (x + w, min(py + dash, y + h)), width)


def shake_offset(frames_left: int, magnitude: int = 2):
    """화면 흔들림 오프셋. 프레임이 줄어들수록 진폭도 줄어든다."""
    if frames_left <= 0:
        return 0, 0
    import random
    m = max(1, magnitude * frames_left // 8)
    return random.randint(-m, m), random.randint(-m, m)

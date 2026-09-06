"""
한글 폰트 로더.

pygame 기본 폰트는 한글 글리프가 없어 □ 로 렌더된다.
Windows / Linux 양쪽에서 동작하도록 후보 경로를 순서대로 탐색하고,
모두 실패하면 SysFont 후보군으로 폴백한다.
"""

import os
import pygame

# 후보 폰트 경로 (앞에 있을수록 우선)
_CANDIDATES_REGULAR = [
    r"C:\Windows\Fonts\NanumGothic.ttf",
    r"C:\Windows\Fonts\malgun.ttf",
    r"C:\Windows\Fonts\gulim.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]
_CANDIDATES_BOLD = [
    r"C:\Windows\Fonts\NanumGothicBold.ttf",
    r"C:\Windows\Fonts\malgunbd.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]

# SysFont 폴백 후보 (설치 폰트 이름 기준)
_SYSFONT_NAMES = "nanumgothic,malgungothic,applegothic,wenquanyizenhei,notosanscjkkr"

_cache: dict = {}
_resolved_path: dict = {}


def _resolve(bold: bool):
    """실제로 존재하는 폰트 파일 경로를 찾아 캐싱한다. 없으면 None."""
    if bold in _resolved_path:
        return _resolved_path[bold]

    candidates = (_CANDIDATES_BOLD if bold else []) + _CANDIDATES_REGULAR
    path = next((p for p in candidates if os.path.exists(p)), None)
    _resolved_path[bold] = path
    return path


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """크기별로 캐싱된 한글 폰트를 반환한다."""
    key = (size, bold)
    if key in _cache:
        return _cache[key]

    path = _resolve(bold)
    if path:
        font = pygame.font.Font(path, size)
        # .ttf 볼드 파일이 없을 때는 합성 볼드로 대체
        if bold and "Bold" not in path and "bd" not in path.lower():
            font.set_bold(True)
    else:
        font = pygame.font.SysFont(_SYSFONT_NAMES, size, bold=bold)

    _cache[key] = font
    return font


def draw_text(surf, text, pos, size=16, color=(255, 255, 255),
              bold=False, anchor="topleft", shadow=True):
    """
    텍스트를 그리고 그려진 Rect를 반환한다.

    anchor : "topleft" | "center" | "midtop" | "topright" | "midbottom"
    shadow : 고전 게임 느낌의 1px 검정 그림자
    """
    font = get_font(size, bold)
    img = font.render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        shade = font.render(text, True, (0, 0, 0))
        surf.blit(shade, (rect.x + 2, rect.y + 2))
    surf.blit(img, rect)
    return rect

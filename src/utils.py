import pygame
import os

# 나눔고딕 폰트 경로 (Windows 시스템 폰트 폴더)
_FONT_PATH_NORMAL = r"C:\Windows\Fonts\NanumGothic.ttf"
_FONT_PATH_BOLD   = r"C:\Windows\Fonts\NanumGothicBold.ttf"

# 폰트 객체를 크기별로 캐싱 (같은 크기를 매번 새로 만들지 않도록)
_cache: dict = {}

def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """나눔고딕 폰트를 반환한다. 없으면 맑은고딕으로 대체."""
    key = (size, bold)
    if key in _cache:
        return _cache[key]

    path = _FONT_PATH_BOLD if bold else _FONT_PATH_NORMAL
    if os.path.exists(path):
        font = pygame.font.Font(path, size)
    else:
        # 나눔고딕이 없으면 맑은고딕으로 대체
        font = pygame.font.SysFont("malgungothic", size, bold=bold)

    _cache[key] = font
    return font

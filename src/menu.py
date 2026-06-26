import os
import pygame
from src.data  import (DIFFICULTY_ORDER, DIFFICULTIES, CAR_COLOR_ORDER, CAR_COLORS,
                       RACERS, TIRES, TIRE_COLORS, TIRE_DESCRIPTIONS, CIRCUITS)
from src.utils import get_font

# circuit/ 폴더 기준 경로
_CIRCUIT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "circuit")

# 게임 시작 전 옵션 선택 메뉴 (6단계)
class SelectionMenu:
    STEPS = [
        {"key": "difficulty", "title": "난이도 선택"},
        {"key": "car",        "title": "차 색깔 선택"},
        {"key": "racer",      "title": "레이서 선택"},
        {"key": "circuit",    "title": "서킷 선택"},
        {"key": "tire",       "title": "타이어 선택"},
    ]

    MAX_VISIBLE   = 8   # 한 번에 보여줄 최대 항목 수
    _img_cache: dict = {}  # 서킷 이미지 캐시 (클래스 공유)

    def __init__(self, screen_width, screen_height):
        self.screen_width  = screen_width
        self.screen_height = screen_height
        self.step       = 0
        self.cursor     = 0
        self.selections = {}
        self.done       = False

        self.font_title = get_font(32, bold=True)
        self.font_item  = get_font(24)
        self.font_tiny  = get_font(17)

    # ── 현재 단계의 항목 목록 ──────────────────────────────────
    def _get_items(self):
        key = self.STEPS[self.step]["key"]
        if key == "difficulty": return DIFFICULTY_ORDER
        if key == "car":        return CAR_COLOR_ORDER
        if key == "racer":      return [r["name"] for r in RACERS]
        if key == "circuit":    return [c["name"] for c in CIRCUITS]
        if key == "tire":       return TIRES
        return []

    def _get_description(self, key, item):
        if key == "difficulty":
            d = DIFFICULTIES.get(item, {})
            return f"속도 {d.get('obstacle_speed','?')}  생성간격 {d.get('spawn_interval','?')}"
        if key == "racer":
            for r in RACERS:
                if r["name"] == item:
                    return f"Team: {r['team']}"
        if key == "tire":
            return TIRE_DESCRIPTIONS.get(item, "")
        return ""

    # ── 서킷 이미지 로드 (캐시 활용) ─────────────────────────
    def _load_circuit_img(self, name, size):
        key = (name, size)
        if key not in self._img_cache:
            path = os.path.join(_CIRCUIT_DIR, f"{name}.webp")
            try:
                raw = pygame.image.load(path).convert()
                self._img_cache[key] = pygame.transform.smoothscale(raw, size)
            except Exception:
                self._img_cache[key] = None
        return self._img_cache[key]

    # ── ESC: 한 단계 뒤로 ────────────────────────────────────
    def go_back(self):
        if self.step > 0:
            self.step -= 1
            key = self.STEPS[self.step]["key"]
            self.selections.pop(key, None)
            self.cursor = 0
            return True
        return False

    # ── 키 입력 ──────────────────────────────────────────────
    def handle_event(self, event):
        if self.done:
            return
        items = self._get_items()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.cursor = (self.cursor - 1) % len(items)
            elif event.key == pygame.K_DOWN:
                self.cursor = (self.cursor + 1) % len(items)
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                key = self.STEPS[self.step]["key"]
                self.selections[key] = items[self.cursor]
                self.step  += 1
                self.cursor = 0
                if self.step >= len(self.STEPS):
                    self.done = True

    def get_selections(self):
        return self.selections

    # ── 화면 그리기 ─────────────────────────────────────────
    def draw(self, screen):
        if self.done:
            return

        step_data = self.STEPS[self.step]
        items     = self._get_items()
        key       = step_data["key"]
        is_circuit_step = (key == "circuit")

        # ── 배경 ─────────────────────────────────────────────
        screen.fill((8, 10, 30))
        for i in range(0, self.screen_height, 60):
            pygame.draw.rect(screen, (12, 14, 38), (0, i, self.screen_width, 28))

        # ── 단계 / 제목 ──────────────────────────────────────
        step_txt = self.font_tiny.render(
            f"Step {self.step + 1} / {len(self.STEPS)}", True, (130, 130, 200))
        screen.blit(step_txt, (self.screen_width // 2 - step_txt.get_width() // 2, 18))

        title_txt = self.font_title.render(step_data["title"], True, (255, 220, 0))
        screen.blit(title_txt, (self.screen_width // 2 - title_txt.get_width() // 2, 42))
        pygame.draw.line(screen, (60, 60, 120), (30, 86), (self.screen_width - 30, 86), 2)

        # ── 서킷 단계: 아이템은 좌측 절반만 사용 ─────────────
        item_x_max = self.screen_width - 30 if not is_circuit_step else (self.screen_width // 2 - 10)

        # ── 스크롤 윈도우 ─────────────────────────────────────
        visible = min(self.MAX_VISIBLE, len(items))
        scroll  = max(0, min(self.cursor - visible // 2, len(items) - visible))

        item_y, item_h = 96, 50

        for i, item in enumerate(items[scroll : scroll + visible]):
            actual_idx = i + scroll
            selected   = (actual_idx == self.cursor)
            iy = item_y + i * item_h
            ix = 30

            row_w = item_x_max - ix + 8
            if selected:
                pygame.draw.rect(screen, (40, 70, 160),
                                 (ix - 4, iy - 3, row_w, item_h - 4), border_radius=8)
                pygame.draw.rect(screen, (90, 140, 255),
                                 (ix - 4, iy - 3, row_w, item_h - 4), 2, border_radius=8)

            prefix   = "▶  " if selected else "    "
            text_col = (255, 255, 255) if selected else (150, 150, 200)
            item_surf = self.font_item.render(prefix + item, True, text_col)
            screen.blit(item_surf, (ix + 6, iy + 4))

            desc = self._get_description(key, item)
            if desc:
                desc_c = (200, 200, 120) if selected else (90, 90, 120)
                screen.blit(self.font_tiny.render(desc, True, desc_c), (ix + 12, iy + 28))

            # 차 색깔 미리보기
            if key == "car":
                cc = CAR_COLORS.get(item, (200, 200, 200))
                pygame.draw.rect(screen, cc,
                                 (self.screen_width - 70, iy + 4, 40, item_h - 12), border_radius=5)
                if selected:
                    dark_cc = tuple(max(0, v - 80) for v in cc)
                    pygame.draw.rect(screen, dark_cc,
                                     (self.screen_width - 62, iy + 10, 24, item_h - 24), border_radius=3)

            # 타이어 미리보기
            if key == "tire":
                tc = TIRE_COLORS.get(item, (200, 200, 200))
                cx = self.screen_width - 55
                cy = iy + item_h // 2 - 2
                pygame.draw.circle(screen, tc, (cx, cy), 14)
                pygame.draw.circle(screen, (20, 20, 20), (cx, cy), 7)
                pygame.draw.circle(screen, (180, 180, 180), (cx, cy), 14, 2)

        # ── 서킷 이미지 미리보기 (우측 절반) ─────────────────
        if is_circuit_step:
            selected_circuit = items[self.cursor]
            img_w, img_h = 254, 170
            img_x = self.screen_width // 2 + 6
            img_y = 100

            img = self._load_circuit_img(selected_circuit, (img_w, img_h))
            if img:
                # 이미지 테두리
                pygame.draw.rect(screen, (255, 220, 0),
                                 (img_x - 2, img_y - 2, img_w + 4, img_h + 4), 2, border_radius=4)
                screen.blit(img, (img_x, img_y))

                # 서킷 이름 라벨
                name_surf = self.font_tiny.render(selected_circuit, True, (220, 220, 255))
                nx = img_x + img_w // 2 - name_surf.get_width() // 2
                ny = img_y + img_h + 6
                screen.blit(name_surf, (nx, ny))

        # 스크롤바
        if len(items) > visible:
            self._draw_scroll_indicator(screen, scroll, len(items), visible,
                                        right_x=item_x_max + (12 if is_circuit_step else 0))

        # 선택 요약 + 조작 안내
        self._draw_summary(screen)
        hint = self.font_tiny.render(
            "↑↓ 이동   SPACE/ENTER 선택   ESC 뒤로", True, (100, 100, 160))
        screen.blit(hint, (self.screen_width // 2 - hint.get_width() // 2,
                            self.screen_height - 28))

    def _draw_scroll_indicator(self, screen, scroll, total, visible, right_x=None):
        bar_x   = (right_x or self.screen_width) - 14
        bar_y   = 96
        bar_h   = visible * 50
        thumb_h = max(20, bar_h * visible // total)
        thumb_y = bar_y + (bar_h - thumb_h) * scroll // max(1, total - visible)
        pygame.draw.rect(screen, (40, 40, 60),    (bar_x, bar_y, 8, bar_h), border_radius=4)
        pygame.draw.rect(screen, (120, 120, 200), (bar_x, thumb_y, 8, thumb_h), border_radius=4)

    def _draw_summary(self, screen):
        if not self.selections:
            return
        y0 = self.screen_height - 28 - len(self.selections) * 20
        for v in self.selections.values():
            surf = self.font_tiny.render(f"✓ {v}", True, (80, 200, 100))
            screen.blit(surf, (8, y0))
            y0 += 20

import pygame
from src.data import (DIFFICULTY_ORDER, DIFFICULTIES, CAR_COLOR_ORDER, CAR_COLORS,
                      RACERS, TRACKS, TIRES, TIRE_COLORS, TIRE_DESCRIPTIONS)

# 게임 시작 전 옵션 선택 메뉴 (5단계)
class SelectionMenu:
    # 5단계 선택 순서와 각 단계의 데이터
    STEPS = [
        {"key": "difficulty", "title": "난이도 선택",  "emoji": "🎮"},
        {"key": "car",        "title": "차 색깔 선택", "emoji": "🏎"},
        {"key": "racer",      "title": "레이서 선택",  "emoji": "👨‍✈️"},
        {"key": "track",      "title": "트랙 선택",    "emoji": "🛣"},
        {"key": "tire",       "title": "타이어 선택",  "emoji": "🔧"},
    ]

    MAX_VISIBLE = 8  # 한 화면에 보여줄 최대 항목 수

    def __init__(self, screen_width, screen_height):
        self.screen_width  = screen_width
        self.screen_height = screen_height

        self.step       = 0   # 현재 단계 (0~4)
        self.cursor     = 0   # 현재 선택된 항목 인덱스
        self.selections = {}  # 확정된 선택값 저장
        self.done       = False

        self.font_title = pygame.font.SysFont("malgungothic", 32, bold=True)
        self.font_item  = pygame.font.SysFont("malgungothic", 24)
        self.font_sub   = pygame.font.SysFont("malgungothic", 19)
        self.font_tiny  = pygame.font.SysFont("malgungothic", 17)

    # ── 현재 단계의 선택 가능 항목 목록 반환 ─────────────────
    def _get_items(self):
        key = self.STEPS[self.step]["key"]
        if key == "difficulty": return DIFFICULTY_ORDER
        if key == "car":        return CAR_COLOR_ORDER
        if key == "racer":      return [r["name"] for r in RACERS]
        if key == "track":      return [t["name"] for t in TRACKS]
        if key == "tire":       return TIRES
        return []

    # ── 항목의 부가 설명 ─────────────────────────────────────
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

    # ── 키 입력 처리 ─────────────────────────────────────────
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
                # 현재 선택을 저장하고 다음 단계로
                key = self.STEPS[self.step]["key"]
                self.selections[key] = items[self.cursor]
                self.step   += 1
                self.cursor  = 0
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

        # 배경
        screen.fill((8, 10, 30))
        # 배경 줄무늬
        for i in range(0, self.screen_height, 60):
            pygame.draw.rect(screen, (12, 14, 38), (0, i, self.screen_width, 28))

        # ── 단계 표시 ────────────────────────────────────────
        step_txt = self.font_tiny.render(
            f"Step {self.step + 1} / {len(self.STEPS)}", True, (130, 130, 200))
        screen.blit(step_txt, (self.screen_width // 2 - step_txt.get_width() // 2, 18))

        # ── 단계 제목 ────────────────────────────────────────
        title_txt = self.font_title.render(
            f"{step_data['title']}", True, (255, 220, 0))
        screen.blit(title_txt, (self.screen_width // 2 - title_txt.get_width() // 2, 42))

        # 구분선
        pygame.draw.line(screen, (60, 60, 120),
                         (30, 86), (self.screen_width - 30, 86), 2)

        # ── 스크롤 윈도우 계산 ───────────────────────────────
        visible = min(self.MAX_VISIBLE, len(items))
        scroll  = max(0, min(self.cursor - visible // 2, len(items) - visible))

        item_y  = 96
        item_h  = 52

        for i, item in enumerate(items[scroll : scroll + visible]):
            actual_idx = i + scroll
            selected   = (actual_idx == self.cursor)
            iy = item_y + i * item_h
            ix = 30

            # 선택된 항목 배경 강조
            if selected:
                pygame.draw.rect(screen, (40, 70, 160),
                                 (ix - 4, iy - 3, self.screen_width - ix * 2 + 8, item_h - 4),
                                 border_radius=8)
                pygame.draw.rect(screen, (90, 140, 255),
                                 (ix - 4, iy - 3, self.screen_width - ix * 2 + 8, item_h - 4),
                                 2, border_radius=8)

            # 항목 이름
            prefix    = "▶  " if selected else "    "
            text_col  = (255, 255, 255) if selected else (150, 150, 200)
            item_surf = self.font_item.render(prefix + item, True, text_col)
            screen.blit(item_surf, (ix + 6, iy + 4))

            # 부가 설명
            desc = self._get_description(key, item)
            if desc:
                desc_col  = (200, 200, 120) if selected else (90, 90, 120)
                desc_surf = self.font_tiny.render(desc, True, desc_col)
                screen.blit(desc_surf, (ix + 12, iy + 28))

            # 미리보기: 차 색깔 박스
            if key == "car":
                cc = CAR_COLORS.get(item, (200, 200, 200))
                pygame.draw.rect(screen, cc,
                                 (self.screen_width - 70, iy + 4, 40, item_h - 12),
                                 border_radius=5)
                # 선택된 경우 F1카 실루엣 느낌
                if selected:
                    dark_cc = tuple(max(0, v - 80) for v in cc)
                    pygame.draw.rect(screen, dark_cc,
                                     (self.screen_width - 62, iy + 10, 24, item_h - 24),
                                     border_radius=3)

            # 미리보기: 타이어 색깔 원
            if key == "tire":
                tc = TIRE_COLORS.get(item, (200, 200, 200))
                cx = self.screen_width - 55
                cy = iy + item_h // 2 - 2
                pygame.draw.circle(screen, tc, (cx, cy), 14)
                pygame.draw.circle(screen, (20, 20, 20), (cx, cy), 7)
                pygame.draw.circle(screen, (180, 180, 180), (cx, cy), 14, 2)

        # 스크롤 표시 (항목이 많을 때)
        if len(items) > visible:
            self._draw_scroll_indicator(screen, scroll, len(items), visible)

        # ── 이전 선택 요약 (화면 오른쪽 하단) ──────────────
        self._draw_summary(screen)

        # ── 조작 안내 ────────────────────────────────────────
        hint = self.font_tiny.render(
            "↑↓ 이동   SPACE 또는 ENTER 선택", True, (100, 100, 160))
        screen.blit(hint, (self.screen_width // 2 - hint.get_width() // 2,
                            self.screen_height - 28))

    def _draw_scroll_indicator(self, screen, scroll, total, visible):
        # 오른쪽에 작은 스크롤바
        bar_x  = self.screen_width - 14
        bar_y  = 96
        bar_h  = visible * 52
        thumb_h = max(20, bar_h * visible // total)
        thumb_y = bar_y + (bar_h - thumb_h) * scroll // max(1, total - visible)
        pygame.draw.rect(screen, (40, 40, 60), (bar_x, bar_y, 8, bar_h), border_radius=4)
        pygame.draw.rect(screen, (120, 120, 200), (bar_x, thumb_y, 8, thumb_h), border_radius=4)

    def _draw_summary(self, screen):
        # 확정된 선택 요약 (왼쪽 하단)
        if not self.selections:
            return
        y0 = self.screen_height - 28 - len(self.selections) * 20
        for k, v in self.selections.items():
            summary = self.font_tiny.render(f"✓ {v}", True, (80, 200, 100))
            screen.blit(summary, (8, y0))
            y0 += 20

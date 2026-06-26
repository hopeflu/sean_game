import pygame
import sys
from src.title_screen import TitleScreen
from src.menu         import SelectionMenu
from src.game         import Game

# ────────────────────────────────────────────────────────────
#  Full Acceleration with Sean Kim
#  조작: ← → 또는 A D  |  F11: 전체화면  |  ESC: 뒤로
# ────────────────────────────────────────────────────────────

LOGICAL_W = 720   # 게임 내부 해상도 — 3D에 적합한 가로 넓은 비율
LOGICAL_H = 800
FPS = 60

STATE_TITLE = "title"
STATE_MENU  = "menu"
STATE_GAME  = "game"


def make_screen(fullscreen):
    """창 모드 또는 전체화면 모드로 화면 생성"""
    if fullscreen:
        info = pygame.display.Info()
        return pygame.display.set_mode(
            (info.current_w, info.current_h), pygame.FULLSCREEN)
    else:
        return pygame.display.set_mode((LOGICAL_W, LOGICAL_H))


def blit_logical(screen, logical, fullscreen):
    """논리 화면을 실제 화면에 맞게 스케일해서 출력"""
    if fullscreen:
        sw, sh = screen.get_size()
        scale   = min(sw / LOGICAL_W, sh / LOGICAL_H)
        scaled_w = int(LOGICAL_W * scale)
        scaled_h = int(LOGICAL_H * scale)
        scaled = pygame.transform.smoothscale(logical, (scaled_w, scaled_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled, ((sw - scaled_w) // 2, (sh - scaled_h) // 2))
    else:
        screen.blit(logical, (0, 0))


def main():
    pygame.init()

    fullscreen = False
    screen  = make_screen(fullscreen)
    logical = pygame.Surface((LOGICAL_W, LOGICAL_H))  # 항상 이 면에 그림
    pygame.display.set_caption("Full Acceleration with Sean Kim")
    clock = pygame.time.Clock()

    state        = STATE_TITLE
    title_screen = TitleScreen(LOGICAL_W, LOGICAL_H)
    menu         = None
    game         = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # ── F11: 전체화면 토글 ────────────────────────────
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                fullscreen = not fullscreen
                screen = make_screen(fullscreen)

            # ── ESC: 한 단계씩 뒤로 ──────────────────────────
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state == STATE_GAME:
                    # 게임 중 → 메뉴로
                    state = STATE_MENU
                    menu  = SelectionMenu(LOGICAL_W, LOGICAL_H)
                    game  = None
                elif state == STATE_MENU:
                    # 메뉴 이전 단계 or 타이틀로
                    went_back = menu.go_back()
                    if not went_back:
                        state        = STATE_TITLE
                        title_screen = TitleScreen(LOGICAL_W, LOGICAL_H)
                        menu         = None
                else:
                    # 타이틀 → 종료
                    pygame.quit()
                    sys.exit()

            if state == STATE_TITLE:
                title_screen.handle_event(event)
            elif state == STATE_MENU and menu is not None:
                menu.handle_event(event)
            elif state == STATE_GAME and game is not None:
                result = game.handle_event(event)
                if result == "to_menu":
                    state = STATE_MENU
                    menu  = SelectionMenu(LOGICAL_W, LOGICAL_H)
                    game  = None

        # ── 상태 전환 ────────────────────────────────────────
        if state == STATE_TITLE and title_screen.done:
            state = STATE_MENU
            menu  = SelectionMenu(LOGICAL_W, LOGICAL_H)

        elif state == STATE_MENU and menu is not None and menu.done:
            state = STATE_GAME
            game  = Game(LOGICAL_W, LOGICAL_H, menu.get_selections())
            menu  = None

        # ── 업데이트 ─────────────────────────────────────────
        if state == STATE_TITLE:
            title_screen.update()
        elif state == STATE_GAME and game is not None:
            keys = pygame.key.get_pressed()
            game.handle_input(keys)
            game.update()

        # ── 논리 화면에 그리기 ───────────────────────────────
        if state == STATE_TITLE:
            title_screen.draw(logical)
        elif state == STATE_MENU and menu is not None:
            menu.draw(logical)
        elif state == STATE_GAME and game is not None:
            game.draw(logical)

        # 논리 화면 → 실제 화면 출력
        blit_logical(screen, logical, fullscreen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()

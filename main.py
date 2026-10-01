import pygame
import sys
from src.title_screen import TitleScreen
from src.menu         import SelectionMenu
from src.game         import Game

# ────────────────────────────────────────────────────────────
#  Full Acceleration with Sean Kim
#  조작: ← → 또는 A D   |   ESC: 타이틀로   |   SPACE: 선택/재시작
# ────────────────────────────────────────────────────────────

SCREEN_WIDTH  = 480
SCREEN_HEIGHT = 700
FPS = 60

# 게임의 큰 상태 (화면 단위)
STATE_TITLE = "title"
STATE_MENU  = "menu"
STATE_GAME  = "game"


def main():
    pygame.init()

    # 창 생성
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Full Acceleration with Sean Kim")
    clock = pygame.time.Clock()

    # 초기 상태: 타이틀 화면
    state        = STATE_TITLE
    title_screen = TitleScreen(SCREEN_WIDTH, SCREEN_HEIGHT)
    menu         = None
    game         = None

    # ── 메인 루프 ────────────────────────────────────────────
    while True:
        # ── 이벤트 처리 ──────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # ESC: 게임 중이면 타이틀로, 그 외에는 종료
                if state == STATE_GAME:
                    state        = STATE_TITLE
                    title_screen = TitleScreen(SCREEN_WIDTH, SCREEN_HEIGHT)
                    game         = None
                elif state == STATE_MENU:
                    state        = STATE_TITLE
                    title_screen = TitleScreen(SCREEN_WIDTH, SCREEN_HEIGHT)
                    menu         = None
                else:
                    pygame.quit()
                    sys.exit()

            if state == STATE_TITLE:
                title_screen.handle_event(event)
            elif state == STATE_MENU:
                menu.handle_event(event)
            elif state == STATE_GAME:
                result = game.handle_event(event)
                if result == "restart":
                    # 게임 오버 후 메뉴로
                    state = STATE_MENU
                    menu  = SelectionMenu(SCREEN_WIDTH, SCREEN_HEIGHT)
                    game  = None

        # ── 상태 전환 확인 ───────────────────────────────────
        if state == STATE_TITLE and title_screen.done:
            state = STATE_MENU
            menu  = SelectionMenu(SCREEN_WIDTH, SCREEN_HEIGHT)

        elif state == STATE_MENU and menu is not None and menu.done:
            state = STATE_GAME
            game  = Game(SCREEN_WIDTH, SCREEN_HEIGHT, menu.get_selections())
            menu  = None

        # ── 업데이트 ─────────────────────────────────────────
        if state == STATE_TITLE:
            title_screen.update()

        elif state == STATE_GAME and game is not None:
            keys = pygame.key.get_pressed()
            game.handle_input(keys)
            game.update()

        # ── 그리기 ───────────────────────────────────────────
        if state == STATE_TITLE:
            title_screen.draw(screen)
        elif state == STATE_MENU and menu is not None:
            menu.draw(screen)
        elif state == STATE_GAME and game is not None:
            game.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()

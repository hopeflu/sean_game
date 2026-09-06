"""
씬(Scene) 기반 구조.

모든 화면은 Scene 을 상속하고 두 개의 그리기 메서드를 나눠 구현한다.
  draw_playfield(pf)  — 320x240 픽셀 아트 레이어
  draw_hud(win)       — 960x720 텍스트/HUD 레이어

씬 전환은 `self.next_scene` 에 다음 씬 인스턴스를 넣거나,
`self.quit = True` 로 게임을 종료한다.
"""


class Scene:
    def __init__(self, app):
        self.app = app            # App 인스턴스 (공유 상태 접근용)
        self.next_scene = None    # 다음 씬 (None이면 유지)
        self.quit = False
        self.frame = 0            # 씬 진입 후 경과 프레임 (깜빡임 연출용)

    # ── 하위 클래스에서 구현 ──────────────────────────────
    def handle_event(self, event):
        pass

    def update(self):
        pass

    def draw_playfield(self, pf):
        pf.fill((0, 0, 0))

    def draw_hud(self, win):
        pass

    # ── 공통 ──────────────────────────────────────────────
    def tick(self):
        self.frame += 1

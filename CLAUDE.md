# Pygame 게임 프로젝트

## 프로젝트 개요

- Python + Pygame으로 만드는 2D 게임
- 아이와 함께 코딩 학습 목적

## 환경

- Python 3.13.13
- pygame 라이브러리
- 실행 명령: `python main.py`
- 패키지 설치: `pip install pygame`

## 폴더 구조

- 저장소 루트에 게임 2개가 함께 있음 (GitHub `hopeflu/sean_game`, 기준 브랜치 `main`)
- **레이싱 게임 (Full Acceleration)** — 실행: `python main.py` 또는 `update_and_run.bat`
  - `main.py` : 레이싱 게임 진입점 (타이틀 → 서킷 선택 → 게임)
  - `src/` : 게임 로직 모듈 — `game.py`(게임 루프), `road_3d.py`(유사 3D 도로 렌더러), `track.py`(트랙), `player.py`(플레이어 차), `obstacle.py`(장애물 차량), `booster.py`(부스터), `ui.py`(HUD), `menu.py`(서킷 선택), `title_screen.py`(타이틀), `data.py`(공용 상수), `utils.py`(폰트 등 공용 함수)
  - `circuit/` : F1 서킷 이미지 23개 (서킷 선택 화면에서 사용)
- **야구 게임 (KBO 8-BIT BASEBALL)** — 실행: `python -m kbo_ball` 또는 `run_kbo_ball.bat`
  - `kbo_ball/` : 야구 게임 패키지 — `app.py`(앱 루프), `config.py`(설정), `engine/`(투구·스윙·타구·수비·규칙), `scenes/`(화면별 장면), `ui/`(필드·스프라이트·위젯), `data/`(구단·선수 명단), `docs/screenshots/`(화면 캡처)
  - 자세한 조작·규칙은 `kbo_ball/README.md`
- `update_and_run.bat`, `run_kbo_ball.bat` : `git pull origin main` → pygame 설치 확인 → 실행
- `Mapping-Hotas5_MFS.jpg`, `thrustmaster-...webp` : HOTAS 조종기 키 매핑 참고 이미지 (게임 코드와 무관)

## 코딩 규칙

- 함수/변수명은 영문 소문자 + 언더스코어
- 모든 코드에 한국어 주석 작성 (아이가 읽을 수 있도록)
- 파일 하나에 기능 하나 (모듈화)
- 복잡한 로직은 단계별로 설명 포함

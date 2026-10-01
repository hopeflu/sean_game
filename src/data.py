# 게임 전체에서 공유되는 데이터 상수 모음

# ── 2026 F1 드라이버 명단 ──────────────────────────────────
RACERS = [
    {"name": "Max Verstappen",   "team": "Red Bull"},
    {"name": "Lando Norris",     "team": "McLaren"},
    {"name": "Charles Leclerc",  "team": "Ferrari"},
    {"name": "Lewis Hamilton",   "team": "Ferrari"},
    {"name": "George Russell",   "team": "Mercedes"},
    {"name": "Carlos Sainz Jr.", "team": "Williams"},
    {"name": "Fernando Alonso",  "team": "Aston Martin"},
    {"name": "Oscar Piastri",    "team": "McLaren"},
    {"name": "Kimi Antonelli",   "team": "Mercedes"},
    {"name": "Sergio Perez",     "team": "Cadillac"},
]

# ── 난이도 설정 ────────────────────────────────────────────
DIFFICULTIES = {
    "쉬움":     {"obstacle_speed": 4,  "spawn_interval": 100, "speed_inc": 0.3},
    "보통":     {"obstacle_speed": 6,  "spawn_interval": 80,  "speed_inc": 0.5},
    "어려움":   {"obstacle_speed": 9,  "spawn_interval": 60,  "speed_inc": 0.7},
    "익스트림": {"obstacle_speed": 12, "spawn_interval": 45,  "speed_inc": 1.0},
}
DIFFICULTY_ORDER = ["쉬움", "보통", "어려움", "익스트림"]

# ── 플레이어 차 색깔 ───────────────────────────────────────
CAR_COLORS = {
    "빨강": (220, 30,  30),
    "파랑": (30,  100, 220),
    "노랑": (220, 200, 0),
    "초록": (30,  180, 60),
}
CAR_COLOR_ORDER = ["빨강", "파랑", "노랑", "초록"]

# ── 트랙 목록 ─────────────────────────────────────────────
# amplitude: 도로가 좌우로 흔들리는 최대 픽셀
# period:    흔들림 한 주기(프레임 수)
TRACKS = [
    {"name": "완전 직선 트랙", "type": "straight", "width": 300, "amplitude": 0,  "period": 1},
    {"name": "서킷 트랙",      "type": "circuit",  "width": 280, "amplitude": 80, "period": 300},
    {"name": "구불구불 트랙",  "type": "winding",  "width": 260, "amplitude": 70, "period": 150},
    {"name": "산악 트랙",      "type": "mountain", "width": 200, "amplitude": 45, "period": 200},
]

# ── 타이어 종류 ───────────────────────────────────────────
# (현재 단계에서는 시각적 표시만, 효과 차이는 추후 구현)
TIRES = ["소프트", "미디엄", "하드", "웻"]
TIRE_COLORS = {
    "소프트": (255, 80,  80),
    "미디엄": (255, 200, 0),
    "하드":   (220, 220, 220),
    "웻":     (80,  120, 255),
}
TIRE_DESCRIPTIONS = {
    "소프트": "빠르지만 마모 빠름 (추후 구현)",
    "미디엄": "균형 잡힌 타이어 (추후 구현)",
    "하드":   "내구성 높음 (추후 구현)",
    "웻":     "빗길 전용 (추후 구현)",
}

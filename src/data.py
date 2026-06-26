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
    "쉬움":     {"obstacle_speed": 3,  "spawn_interval": 110, "speed_inc": 0.3},
    "보통":     {"obstacle_speed": 5,  "spawn_interval": 85,  "speed_inc": 0.5},
    "어려움":   {"obstacle_speed": 8,  "spawn_interval": 62,  "speed_inc": 0.7},
    "익스트림": {"obstacle_speed": 11, "spawn_interval": 45,  "speed_inc": 1.0},
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

# ── 서킷 커브 기본 패턴 ───────────────────────────────────
# 각 항목: (curve값, 반복횟수)  /  음수=왼쪽, 양수=오른쪽, 크기=커브 강도
def _c(curve_type):
    if curve_type == "hairpin_city":    # Monaco·Singapore·Baku — 좁고 꼬인 시가지
        return [(0.0,4),(2.2,3),(0.0,2),(3.5,2),(-1.4,5),(0.0,3),(3.8,2),(-1.0,6),(0.0,3),(1.8,2),(-2.8,2)]
    if curve_type == "flowing_high":    # Silverstone·Spa·Losail·Barcelona·Albert Park
        return [(0.0,5),(1.4,4),(-0.9,3),(1.2,3),(0.0,2),(-1.6,4),(0.9,3),(0.0,3)]
    if curve_type == "long_straight":   # Monza·Bahrain·Jeddah·Las Vegas — 고속 직선
        return [(0.0,8),(2.3,2),(-2.3,2),(0.0,6),(1.9,2),(-1.9,2),(0.0,5),(-1.3,3),(0.0,2)]
    if curve_type == "technical_mix":   # Suzuka·Hungaroring·COTA·Zandvoort·Shanghai
        return [(0.0,3),(1.8,3),(-2.4,4),(1.5,2),(0.0,2),(-1.8,3),(0.6,5),(3.1,3),(-2.0,2)]
    if curve_type == "mountain_narrow": # Red Bull Ring·Madring — 산악·짧은 서킷
        return [(1.5,3),(-1.0,2),(0.0,3),(2.1,2),(0.0,4),(-1.7,3),(1.0,2),(0.0,2),(-2.4,2)]
    if curve_type == "street_flow":     # Gilles·Miami·Mexico·Interlagos
        return [(0.0,4),(2.0,3),(0.0,3),(-1.6,2),(0.0,5),(3.1,2),(-2.0,3),(0.0,3),(1.5,2),(0.0,2)]
    return [(0.0, 10)]


def _make_seg(curve_type, n_segs):
    """
    커브 패턴을 n_segs 개수에 맞게 반복 확장한다.
    반환: (curve값, 횟수) 튜플 리스트 (Road3D가 소비하는 형식)

    SEG_LEN=1000 기준, 6 segs/km → 1km ≈ 6,000 world units
    보통 속도(10 units/frame × 60fps=600/sec) → 랩 = (n_segs*1000)/600 초
    예) Monaco 20 segs → 20초, Spa 42 segs → 70초
    """
    # 기본 패턴을 평탄화
    flat = []
    for crv, cnt in _c(curve_type):
        flat.extend([crv] * int(cnt))

    # n_segs 개가 될 때까지 반복
    full = []
    while len(full) < n_segs:
        full.extend(flat)
    full = full[:n_segs]

    # 연속된 같은 커브를 묶어 (curve, count) 형식으로 반환
    result = []
    if full:
        cur, cnt = full[0], 1
        for v in full[1:]:
            if v == cur:
                cnt += 1
            else:
                result.append((cur, cnt))
                cur, cnt = v, 1
        result.append((cur, cnt))
    return result


# ── F1 서킷 목록 ──────────────────────────────────────────
# km: 실제 서킷 길이 (formula-timer.com/circuit 기준)
# n_segs: km × 6 (반올림)  → 보통 속도 기준 랩타임 = n_segs×1000/600 초
# road_half: 도로 반폭 (세계 단위)
# grass: 도로 밖 지형 색
CIRCUITS = [
    {"name": "Circuit de Monaco",
     "curve": _make_seg("hairpin_city",    20), "km": 3.337, "road_half": 155, "grass": (30,100,30)},
    {"name": "Autodromo Nazionale Monza",
     "curve": _make_seg("long_straight",   35), "km": 5.793, "road_half": 275, "grass": (34,140,34)},
    {"name": "Silverstone Circuit",
     "curve": _make_seg("flowing_high",    35), "km": 5.891, "road_half": 255, "grass": (28,130,28)},
    {"name": "Circuit de Spa-Francorchamps",
     "curve": _make_seg("flowing_high",    42), "km": 7.004, "road_half": 245, "grass": (22,120,22)},
    {"name": "Suzuka Circuit",
     "curve": _make_seg("technical_mix",   35), "km": 5.807, "road_half": 225, "grass": (34,130,40)},
    {"name": "Circuit of the Americas",
     "curve": _make_seg("technical_mix",   33), "km": 5.513, "road_half": 235, "grass": (30,140,30)},
    {"name": "Hungaroring",
     "curve": _make_seg("technical_mix",   26), "km": 4.381, "road_half": 205, "grass": (40,150,30)},
    {"name": "Circuit Zandvoort",
     "curve": _make_seg("technical_mix",   26), "km": 4.259, "road_half": 215, "grass": (30,140,50)},
    {"name": "Bahrain International Circuit",
     "curve": _make_seg("long_straight",   32), "km": 5.412, "road_half": 275, "grass": (120,100,60)},
    {"name": "Jeddah Corniche Circuit",
     "curve": _make_seg("long_straight",   37), "km": 6.174, "road_half": 255, "grass": (90,80,50)},
    {"name": "Las Vegas Strip Street Circuit",
     "curve": _make_seg("long_straight",   37), "km": 6.201, "road_half": 295, "grass": (20,20,60)},
    {"name": "Losail International Circuit",
     "curve": _make_seg("flowing_high",    33), "km": 5.419, "road_half": 275, "grass": (100,90,60)},
    {"name": "Baku City Circuit",
     "curve": _make_seg("hairpin_city",    36), "km": 6.003, "road_half": 215, "grass": (40,100,40)},
    {"name": "Marina Bay Street Circuit",
     "curve": _make_seg("hairpin_city",    30), "km": 5.063, "road_half": 195, "grass": (20,80,40)},
    {"name": "Albert Park Grand Prix Circuit",
     "curve": _make_seg("flowing_high",    32), "km": 5.278, "road_half": 255, "grass": (34,150,34)},
    {"name": "Circuit Gilles Villeneuve",
     "curve": _make_seg("street_flow",     26), "km": 4.361, "road_half": 235, "grass": (30,140,50)},
    {"name": "Circuit de Barcelona-Catalunya",
     "curve": _make_seg("flowing_high",    28), "km": 4.675, "road_half": 255, "grass": (34,140,34)},
    {"name": "Shanghai International Circuit",
     "curve": _make_seg("technical_mix",   33), "km": 5.451, "road_half": 255, "grass": (30,120,30)},
    {"name": "Autódromo José Carlos Pace",
     "curve": _make_seg("street_flow",     26), "km": 4.309, "road_half": 225, "grass": (30,140,30)},
    {"name": "Autódromo Hermanos Rodríguez",
     "curve": _make_seg("street_flow",     26), "km": 4.304, "road_half": 235, "grass": (50,140,30)},
    {"name": "Miami International Autodrome",
     "curve": _make_seg("street_flow",     32), "km": 5.410, "road_half": 245, "grass": (20,100,80)},
    {"name": "Red Bull Ring",
     "curve": _make_seg("mountain_narrow", 26), "km": 4.318, "road_half": 205, "grass": (34,150,40)},
    {"name": "Madring",
     "curve": _make_seg("mountain_narrow", 33), "km": 5.470, "road_half": 185, "grass": (30,130,30)},
]

# ── 타이어 종류 ───────────────────────────────────────────
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

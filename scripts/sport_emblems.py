"""종목 엠블럼 — 한 획으로 그린 코스.

다섯 종목에 서로 다른 그림을 넣는 대신, 하나의 조형 언어로 묶었다.
calrank 가 다루는 것은 결국 "코스"이므로, 모든 엠블럼은 선으로 그린
경로다. 트레일은 고도 단면의 봉우리, 자전거는 바퀴로 꺼지는 선,
철인3종은 물결·호·직선 세 구간, 인라인은 바퀴 넷 위를 지나는 주행선,
마라톤은 결승 기둥으로 올라가는 코스 선.

28px 로 줄여도 읽히도록 획 굵기를 3.5 로 고정하고 세부 묘사를 넣지 않았다.
색은 style.css 의 --marathon/--trail/... 과 같은 값을 쓴다.
"""

SPORTS = {
    "marathon":  {"label": "마라톤",  "color": "#FF3D1A"},
    "trail":     {"label": "트레일",  "color": "#4CAF7D"},
    "cycling":   {"label": "자전거",  "color": "#5B8DEF"},
    "triathlon": {"label": "철인3종", "color": "#B37FEA"},
    "inline":    {"label": "인라인",  "color": "#00C2A8"},
}

# 64x64 기준. 안쪽 여백 12px.
_ART = {
    # 코스 선이 결승선 기둥으로 들어간다
    "marathon": """
    <path d="M12 48 L20 44 L26 33 L36 30"/>
    <path d="M41 51 L41 15"/>
    <path d="M41 16 L54 20 L41 24"/>
    <circle cx="12" cy="48" r="2.8" fill="currentColor" stroke="none"/>""",
    # 고도 단면. 뾰족한 봉우리 둘
    "trail": """
    <path d="M12 45 L23 27 L31 37 L40 20 L52 45"/>
    <circle cx="40" cy="20" r="2.6" fill="currentColor" stroke="none"/>""",
    # 코스 선이 바퀴 두 개로 꺼진다
    "cycling": """
    <circle cx="20" cy="40" r="9"/>
    <circle cx="44" cy="40" r="9"/>
    <path d="M20 40 L29 25 L41 25 L44 40"/>
    <path d="M29 25 L36 40"/>""",
    # 수영(물결) · 사이클(호) · 달리기(직선)
    "triathlon": """
    <path d="M13 23 q6 -6 12 0 t12 0 t12 0"/>
    <path d="M13 36 q19 -11 38 0"/>
    <path d="M13 47 L51 47"/>""",
    # 프레임 아래 바퀴 넷, 그 위로 주행선
    "inline": """
    <path d="M13 27 q13 -9 25 -4 q8 3 14 1"/>
    <path d="M15 39 L49 39"/>
    <circle cx="18" cy="47" r="3.1" fill="currentColor" stroke="none"/>
    <circle cx="28" cy="47" r="3.1" fill="currentColor" stroke="none"/>
    <circle cx="38" cy="47" r="3.1" fill="currentColor" stroke="none"/>
    <circle cx="48" cy="47" r="3.1" fill="currentColor" stroke="none"/>""",
}


def emblem_svg(sport: str, size: int = 64, ring: bool = True,
               title: str | None = None) -> str:
    """종목 엠블럼 하나를 인라인 SVG 로 돌려준다."""
    meta = SPORTS[sport]
    art = _ART[sport].strip()
    label = title if title is not None else f"{meta['label']} 대회"
    ring_el = (f'<circle cx="32" cy="32" r="29" fill="none" '
               f'stroke="{meta["color"]}" stroke-opacity=".32" stroke-width="1.6"/>'
               if ring else "")
    return (
        f'<svg class="emblem emblem-{sport}" width="{size}" height="{size}" '
        f'viewBox="0 0 64 64" role="img" aria-label="{label}" '
        f'style="color:{meta["color"]}">'
        f'{ring_el}'
        f'<g fill="none" stroke="currentColor" stroke-width="3.5" '
        f'stroke-linecap="round" stroke-linejoin="round">{art}</g>'
        f"</svg>"
    )


def emblem_lockup(sport: str, size: int = 64) -> str:
    """엠블럼 + 한글 이름. 랜딩 헤더용."""
    meta = SPORTS[sport]
    return (f'<span class="emblem-lockup">{emblem_svg(sport, size)}'
            f'<b style="color:{meta["color"]}">{meta["label"]}</b></span>')


EMBLEM_CSS = """
.emblem{display:block;flex:0 0 auto;}
.emblem-lockup{display:inline-flex;align-items:center;gap:10px;}
.emblem-lockup b{font-family:var(--font-display);font-weight:900;
  font-size:15px;letter-spacing:.5px;}
"""

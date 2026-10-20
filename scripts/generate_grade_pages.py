"""
calrank 기록 등급표 정적 페이지 생성 스크립트

level.html의 계산기는 "내가 숫자를 넣어야" 결과가 나오기 때문에, 검색엔진
입장에서는 아무 내용도 없는 빈 페이지에 가깝다. 실제 검색 수요는
"10km 기록 등급표", "나이별 러닝 수준", "여자 마라톤 등급표"처럼
표 자체를 찾는 질의에 몰려 있다.

그래서 계산기와 완전히 동일한 모델(level.js)로 경계값을 미리 계산해,
거리 4종 x 성별 2종 = 8개의 정적 등급표 페이지와 허브 1개를 만든다.
표에 적힌 시간은 "그 등급을 받기 위한 가장 느린 기록"이며, 계산기에
같은 값을 넣으면 반드시 같은 등급이 나오도록 경계를 보정한다.

level.js의 상수가 바뀌면 표와 계산기가 어긋나므로, 생성 전에 level.js를
직접 읽어 상수를 대조하고 다르면 즉시 중단한다.

사용 예시:
  python scripts/generate_grade_pages.py
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_nav import site_header  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# level.js와 동일한 모델 (아래 verify_models()가 매 실행마다 대조)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 등급 모델 — WMA 2025 연령 기준표를 기준축으로 쓴다.
#
# 전에는 나이·성별 보정 계수와 등급 구간을 자체적으로 정해 두고 있었다.
# 출처를 댈 수 없는 숫자였고, 그 탓에 같은 '꾸준한 러너'이라도 나이·성별·거리에
# 따라 실제 실력이 연령등급 41.9~49.1%까지 벌어져 있었다. WMA 기준표로
# 옮기면서 그 흔들림이 사라졌다 — 등급이 곧 연령등급 %다.
#
# 연령등급 % = 그 나이·성별의 기준기록 ÷ 내 기록 × 100.
# 100%가 세계기록 수준이고, 어느 age-grading 계산기에 넣어도 같은 값이 나온다.
# 출처와 라이선스는 wma_standards.py 머리에 적어 두었다.
# ---------------------------------------------------------------------------
import wma_standards as wma  # noqa: E402

# 거리 키 — WMA가 보간 없이 직접 산출하는 네 거리.
DIST_KEY = ((5.0, "5km"), (10.0, "10km"), (21.0975, "half"), (42.195, "full"))

# 내림차순(빠른 순). 값은 그 등급을 받기 위한 연령등급 % 하한.
#
# 경계는 종전 난이도를 그대로 옮긴 것이다(전 구간 2.6만 개 지점을 대조해
# 84.2%가 같은 등급을 유지한다). 바뀌는 쪽은 자체 계수가 WMA와 어긋나 있던
# 구간 — 25~40세와 55세 이상 여성 — 이고, 그건 교정이다.
TIER_BOUNDS = [
    (72, "상당한 러너"),
    (65, "러닝 상급자"),
    (59, "매우 좋은 편"),
    (51, "상당히 좋은 편"),
    (45, "꾸준한 러너"),
    (39, "보통"),
    (0,  "이제 시작"),
]
# '꾸준한 러너'은 연령등급 45%에 걸려 있었는데 실제 중앙값은 57%였다.
# 이름이 사실과 달라 '꾸준한 러너'로 바꿨다. '이제 시작'도 더 부드럽게.
BOUND = {label: pct for pct, label in TIER_BOUNDS}

TABLE_TIERS = TIER_BOUNDS[:-1]
LAST_TIER_LABEL = TIER_BOUNDS[-1][1]

AGES = [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]

INTRO = {
    "5km": (
        "5km는 기록을 재는 거리 중에서는 가장 짧지만, 그만큼 변명이 통하지 않는 거리이기도 합니다. "
        "페이스 조절로 숨길 수 있는 구간이 거의 없어서 현재 심폐 능력이 거의 그대로 드러나죠. "
        "아래 표는 나이와 성별에 따른 보정을 거친 뒤, 같은 조건의 동호인 사이에서 내 5km 기록이 "
        "어디쯤 놓이는지 가늠해 볼 수 있도록 정리한 것입니다."
    ),
    "10km": (
        "10km는 국내 동호인 대회에서 가장 많이 열리고, 가장 많이 비교되는 거리입니다. "
        "속도와 지구력이 반씩 섞여 있어서 '지금 내 수준'을 한 번에 보여 주는 거리이기도 하고요. "
        "아래 표는 나이와 성별 차이를 보정한 뒤 같은 조건의 러너들 사이에서 내 10km 기록이 "
        "어느 구간에 들어가는지 확인할 수 있게 만든 등급표입니다."
    ),
    "half": (
        "하프마라톤부터는 '얼마나 빠른가'보다 '무너지지 않고 유지할 수 있는가'가 기록을 가릅니다. "
        "그래서 10km는 꽤 빠른데 하프에서 뒤쪽 5km가 급격히 느려지는 경우가 흔하죠. "
        "아래 표는 WMA 연령 기준표를 그대로 적용해, "
        "하프 기록이 동호인 전체에서 어느 수준인지 비교할 수 있도록 정리했습니다."
    ),
    "full": (
        "풀코스는 훈련량이 가장 정직하게 드러나는 거리입니다. "
        "30km 이후를 어떻게 버텼는지가 최종 기록의 대부분을 결정하기 때문에, "
        "같은 10km 기록을 가진 두 사람의 풀코스 기록이 30분 이상 벌어지기도 합니다. "
        "아래 표는 나이와 성별을 보정한 뒤, 완주 기록이 동호인 전체에서 어느 구간에 "
        "해당하는지 확인할 수 있게 만든 등급표입니다."
    ),
}

HOW_TO_READ = (
    "표의 숫자는 <strong>그 등급을 받기 위한 가장 느린 기록</strong>입니다. "
    "예를 들어 어떤 칸에 1:02:24가 적혀 있다면, 그 시간까지는 해당 등급에 들어가고 "
    "1초라도 더 걸리면 한 칸 아래 등급이 됩니다. 표에 없는 나이라면 가까운 두 줄 "
    "사이 어딘가로 보시면 되고, 정확한 값은 계산기에서 바로 확인할 수 있습니다."
)

METHOD = (
    "등급 기준은 WMA(세계마스터즈육상연맹)가 내는 연령 기준표를 그대로 가져다 씁니다. "
    "나이와 성별마다 세계 최고 수준에 해당하는 기록이 정해져 있는데, 내 기록이 그 기준의 "
    "몇 %쯤 되는지를 연령등급이라고 해요. 100%면 세계기록 수준이고요. "
    "이 숫자는 어느 age-grading 계산기에 넣어도 같은 값이 나오니까, 여기서 받은 등급이 "
    "맞는지 직접 확인해 보셔도 됩니다. "
    "5km·10km·하프·풀코스는 WMA가 거리마다 기준을 따로 내기 때문에, 거리끼리 환산하지 "
    "않고 각 거리의 기준으로 바로 비교합니다. "
    "기준표 출처와 계산식, 일곱 구간을 나눈 자리까지 "
    "<a href=\"grade-method.html\">등급 기준과 근거</a>에 전부 적어 두었어요."
)


DISTANCES = [
    {"key": "5km", "km": 5.0, "label": "5km", "search": "5km"},
    {"key": "10km", "km": 10.0, "label": "10km", "search": "10km"},
    {"key": "half", "km": 21.0975, "label": "하프(21.1km)", "search": "하프마라톤"},
    {"key": "full", "km": 42.195, "label": "풀코스(42.195km)", "search": "풀코스 마라톤"},
]
GENDERS = [
    {"key": "male", "label": "남성", "josa": "남성"},
    {"key": "female", "label": "여성", "josa": "여성"},
]

BASE = "https://calrank.vercel.app"


# ---------------------------------------------------------------------------
# 모델
# ---------------------------------------------------------------------------
def dist_key(km: float) -> str | None:
    """거리를 WMA 표의 키로. 표에 없는 거리는 None (등급을 매기지 않는다)."""
    for value, key in DIST_KEY:
        if abs(km - value) < 0.05:
            return key
    return None


def age_grade(finish_sec: float, age: int, gender: str, km: float) -> float:
    """연령등급 %. 그 나이·성별의 기준기록 ÷ 내 기록 × 100."""
    key = dist_key(km)
    if key is None:
        raise ValueError(f"WMA 표에 없는 거리: {km}")
    return wma.standard(gender, key, age) / float(finish_sec) * 100.0


def tier_of(finish_sec: float, age: int, gender: str, km: float) -> str:
    pct = age_grade(finish_sec, age, gender, km)
    return next(label for bound, label in TIER_BOUNDS if pct >= bound)


def boundary_seconds(bound_pct: int, age: int, gender: str, km: float) -> int:
    """그 등급을 받을 수 있는 가장 느린 기록(초).

    연령등급은 기록에 반비례하므로 경계는 나눗셈 한 번으로 바로 나온다.
    내림으로 맞춰 표에 적힌 시간이 실제로 그 등급에 들어가게 한다.

    math.floor(a / b) 로 적은 것은 일부러다. 파이썬의 a // b 는 결과가 정수에
    아주 가까울 때 1초 어긋나는 경우가 있어서, 같은 식을 쓰는 자바스크립트
    (grade-model.js, level.js)와 값이 갈린다. 96개 지점 중 10개가 그랬다.
    """
    key = dist_key(km)
    if key is None:
        raise ValueError(f"WMA 표에 없는 거리: {km}")
    return math.floor(wma.standard(gender, key, age) / (bound_pct / 100.0))


def fmt_time(sec: int) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def fmt_pace(sec_per_km: float) -> str:
    m = int(sec_per_km // 60)
    s = int(round(sec_per_km % 60))
    if s == 60:
        m, s = m + 1, 0
    return f"{m}:{s:02d}"


# ---------------------------------------------------------------------------
# level.js 상수 대조 — 어긋나면 생성하지 않는다
# ---------------------------------------------------------------------------
def _js_tier_bounds(src: str) -> list[tuple[int, str]]:
    # level.js 는 설명 문구가 뒤에 더 붙고 grade-model.js 는 두 칸뿐이라,
    # 라벨 뒤가 쉼표든 닫는 대괄호든 받아들인다.
    return [(int(b), lab) for b, lab in
            re.findall(r"\[\s*(\d+)\s*,\s*\"([^\"]+)\"\s*[,\]]", src)]


def _js_wma_table(src: str) -> dict:
    """wma-standards.js 가 품은 기준기록 표를 읽어 온다."""
    out = {}
    for gender in ("male", "female"):
        block = re.search(gender + r":\s*\{(.*?)\n  \}", src, re.S)
        if not block:
            sys.exit(f"[grade pages] wma-standards.js 에서 {gender} 표를 못 찾았습니다.")
        rows = {}
        for key, body in re.findall(r'"(\w+)":\s*\[([^\]]*)\]', block.group(1)):
            rows[key] = [int(x) for x in body.split(",")]
        out[gender] = rows
    return out


def verify_models() -> None:
    """계산기·기록증·등급표가 같은 기준을 쓰는지 매 실행마다 확인한다.

    값이 갈라지면 같은 기록에 다른 등급이 나온다. 이 프로젝트에서 실제로
    났던 사고라, 어긋나면 페이지를 만들지 않고 멈춘다.
    """
    for name in ("level.js", "grade-model.js"):
        path = ROOT / name
        if not path.exists():
            sys.exit(f"[grade pages] {name} 을 찾을 수 없어 중단합니다.")
        bounds = _js_tier_bounds(path.read_text(encoding="utf-8"))
        if bounds[:len(TIER_BOUNDS)] != TIER_BOUNDS:
            sys.exit(f"[grade pages] {name} TIER_BOUNDS 불일치: {bounds[:len(TIER_BOUNDS)]}")

    js_path = ROOT / "wma-standards.js"
    if not js_path.exists():
        sys.exit("[grade pages] wma-standards.js 를 찾을 수 없어 중단합니다.")
    js = _js_wma_table(js_path.read_text(encoding="utf-8"))
    for gender in ("male", "female"):
        for key in ("5km", "10km", "half", "full"):
            if js[gender][key] != wma.STD[gender][key]:
                sys.exit(f"[grade pages] wma-standards.js {gender}/{key} 기준표 불일치")

    print("[grade pages] 등급 기준 대조 통과 (level.js · grade-model.js · WMA 표)")


def faq_items(dist, gender):
    d, g = dist["label"], gender["label"]
    return [
        (
            f"{dist['search']} 기록이 몇 분이면 잘 뛰는 편인가요?",
            f"나이에 따라 기준이 꽤 달라집니다. 같은 기록이라도 20대와 60대의 평가가 다르기 때문에, "
            f"위 표에서 본인 나이대 줄을 먼저 찾은 뒤 기록이 어느 칸에 들어가는지 보시는 게 정확합니다. "
            f"{g} 기준으로 '꾸준한 러너' 칸 안쪽이면 또래 동호인 평균보다 좋은 편이라고 볼 수 있습니다.",
        ),
        (
            "나이를 왜 보정하나요?",
            "같은 훈련을 해도 심폐 능력과 회복력은 연령에 따라 차이가 납니다. 보정 없이 절대 기록만 "
            "비교하면 나이가 많은 러너는 아무리 잘 달려도 늘 아래쪽에 머물게 되죠. "
            "그래서 나이와 성별마다 기준기록이 따로 있는 WMA 표를 써서, '같은 조건이라면 어느 정도인가'를 "
            "볼 수 있게 했습니다.",
        ),
        (
            f"다른 거리 기록으로도 {d} 등급을 알 수 있나요?",
            "가능합니다. 모든 거리를 10km 환산 페이스로 바꿔서 비교하기 때문에, 하프나 풀코스 기록을 "
            "넣어도 같은 기준으로 등급이 나옵니다. 아래 계산기에서 거리만 바꿔 입력해 보세요.",
        ),
        (
            "이 등급이 공식 기준인가요?",
            "아닙니다. 일반적으로 통용되는 동호인 페이스 구간을 참고해 만든 자체 기준이며, "
            "대회 입상 기준이나 의학적 체력 평가와는 무관한 참고용 지표입니다.",
        ),
    ]


# ---------------------------------------------------------------------------
# 페이지 생성
# ---------------------------------------------------------------------------
NAV = site_header("grade")

FOOTER = """<footer class="site-footer">
<div class="wrap">
<p>기준표는 WMA(세계마스터즈육상연맹) 2025년판이고, 출처와 계산식은 모두 공개돼 있습니다. 다만 공인 기록이나 의학적 판단은 아니고, 코스와 날씨에 따라 체감이 달라질 수 있는 참고용입니다.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>"""

PAGE_CSS = """  .gr-wrap { max-width: 860px; margin: 0 auto; padding: 44px 20px 80px; }
  .gr-title { font-family: var(--font-display); font-size: clamp(23px, 3.4vw, 33px); line-height: 1.3; margin-bottom: 12px; }
  .gr-lead { font-size: 15px; line-height: 1.8; color: #C9C3BF; margin-bottom: 22px; }
  .gr-switch { display: flex; flex-wrap: wrap; gap: 7px; margin: 18px 0 26px; }
  .gr-switch a { font-size: 13px; padding: 7px 14px; border: 1px solid var(--border, #2A2A2A); border-radius: 999px; color: #D6D1CD; text-decoration: none; }
  .gr-switch a:hover { border-color: var(--accent); }
  .gr-switch a.on { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 700; }
  .gr-tablebox { position: relative; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid var(--border, #2A2A2A); border-radius: 10px; }
  table.gr-table { border-collapse: separate; border-spacing: 0; width: 100%; min-width: 640px; font-size: 13px; }
  table.gr-table th, table.gr-table td { padding: 10px 8px; text-align: center; white-space: nowrap; border-bottom: 1px solid rgba(255,255,255,0.07); }
  table.gr-table thead th { background: #171514; color: #E8E4E1; font-weight: 700; font-size: 12px; line-height: 1.4; }
  /* 모바일 비중이 높아 가로 스크롤 시 나이 칸이 항상 보이도록 고정 */
  table.gr-table tbody th { background: #121010; color: var(--accent); font-weight: 700; text-align: left; padding-left: 14px; position: sticky; left: 0; z-index: 2; border-right: 1px solid rgba(255,255,255,0.09); }
  table.gr-table thead th:first-child { position: sticky; left: 0; z-index: 3; border-right: 1px solid rgba(255,255,255,0.09); }
  table.gr-table tbody tr:nth-child(even) td { background: rgba(255,255,255,0.02); }
  .gr-swipe { display: none; font-size: 12px; color: #8E8884; margin: 8px 2px 0; }
  @media (max-width: 680px) {
    .gr-wrap { padding: 32px 14px 70px; }
    table.gr-table { font-size: 12.5px; }
    table.gr-table th, table.gr-table td { padding: 9px 7px; }
    .gr-swipe { display: block; }
  }
  .gr-note { font-size: 13px; line-height: 1.8; color: #A9A29E; margin-top: 14px; }
  .gr-h2 { font-size: 18px; margin: 38px 0 12px; }
  .gr-p { font-size: 14.5px; line-height: 1.85; color: #C3BDB9; }
  .gr-faq { margin-top: 10px; }
  .gr-faq details { border: 1px solid var(--border, #2A2A2A); border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
  .gr-faq summary { cursor: pointer; font-size: 14px; font-weight: 700; color: #E8E4E1; }
  .gr-faq p { margin-top: 9px; font-size: 14px; line-height: 1.8; color: #B5AFAB; }
  .gr-cta { margin-top: 34px; padding: 22px; background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 10px; text-align: center; }
  .gr-cta p { font-size: 14.5px; color: #C9C3BF; }
  .gr-cta a { display: inline-block; margin-top: 12px; background: var(--accent); color: #fff; font-weight: 700; padding: 12px 24px; border-radius: 6px; text-decoration: none; }
  .gr-links { margin-top: 26px; font-size: 13.5px; line-height: 2; }
  .gr-links a { color: #D6D1CD; text-decoration: none; border-bottom: 1px dashed #5E5A57; }
  .gr-links a:hover { color: var(--accent); border-color: var(--accent); }"""


def head_block(title, desc, slug, ld_blocks):
    lds = "\n".join(f'<script type="application/ld+json">{b}</script>' for b in ld_blocks)
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{BASE}/og-image.png">
<meta property="og:url" content="{BASE}/{slug}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0B0B0B">
<link rel="canonical" href="{BASE}/{slug}">
<link rel="stylesheet" href="style.css">
{lds}
<style>
{PAGE_CSS}
</style>
</head>
<body>
{NAV}'''


def slug_for(dist_key, gender_key):
    return f"grade-{dist_key}-{gender_key}.html"


ON = ' class="on"'


def build_switch(cur_dist, cur_gender):
    dist_links = "".join(
        '<a href="{}"{}>{}</a>'.format(
            slug_for(d["key"], cur_gender), ON if d["key"] == cur_dist else "", d["label"]
        )
        for d in DISTANCES
    )
    gender_links = "".join(
        '<a href="{}"{}>{}</a>'.format(
            slug_for(cur_dist, g["key"]), ON if g["key"] == cur_gender else "", g["label"]
        )
        for g in GENDERS
    )
    return f'<div class="gr-switch">{dist_links}</div>\n<div class="gr-switch">{gender_links}</div>'


def build_table(dist, gender):
    km = dist["km"]
    gk = gender["key"]
    head_cells = "".join(f"<th>{label}</th>" for _, label in TABLE_TIERS)
    head = f"<tr><th>나이</th>{head_cells}<th>그 이상</th></tr>"

    rows = []
    for age in AGES:
        cells = "".join(
            f"<td>{fmt_time(boundary_seconds(bound, age, gk, km))}</td>"
            for bound, _ in TABLE_TIERS
        )
        rows.append(f"<tr><th>{age}세</th>{cells}<td>{LAST_TIER_LABEL}</td></tr>")

    return (
        '<div class="gr-tablebox"><table class="gr-table">\n'
        f"<thead>{head}</thead>\n<tbody>\n" + "\n".join(rows) + "\n</tbody>\n</table></div>\n"
        '<p class="gr-swipe">표를 좌우로 밀면 나머지 등급이 보입니다. 나이 칸은 고정됩니다.</p>'
    )


def build_page(dist, gender):
    dk, gk = dist["key"], gender["key"]
    slug = slug_for(dk, gk)
    title = f"{dist['search']} 기록 등급표 ({gender['label']}·나이별) — 내 러닝 수준 확인 | calrank"
    # 본문 ref_line 과 같은 40세 경계를 쓴다. 소개와 페이지가 어긋나면 안 된다.
    ref40 = fmt_time(boundary_seconds(45, 40, gk, dist["km"]))
    desc = (
        f"40세 {gender['label']} {dist['search']} '꾸준한 러너' 경계는 {ref40}입니다. "
        f"20세부터 75세까지 한 살 단위 {gender['label']} 등급 기준을 표에서 확인하고 "
        f"내 기록을 바로 대입해 보세요."
    )
    h1 = f"{dist['search']} 기록 등급표 — {gender['label']}·나이별"

    faqs = faq_items(dist, gender)
    faq_ld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }, ensure_ascii=False)
    page_ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebPage",
        "name": title, "description": desc, "url": f"{BASE}/{slug}",
        "inLanguage": "ko-KR",
        "isPartOf": {"@type": "WebSite", "name": "calrank", "url": f"{BASE}/"},
    }, ensure_ascii=False)
    crumb_ld = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": f"{BASE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "기록 등급표", "item": f"{BASE}/grade.html"},
            {"@type": "ListItem", "position": 3, "name": h1},
        ],
    }, ensure_ascii=False)

    faq_html = "\n".join(
        f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faqs
    )

    other = [
        f'<a href="{slug_for(d["key"], gk)}">{d["search"]} {gender["label"]} 등급표</a>'
        for d in DISTANCES if d["key"] != dk
    ]
    other.append(f'<a href="{slug_for(dk, "female" if gk == "male" else "male")}">{dist["search"]} '
                 f'{"여성" if gk == "male" else "남성"} 등급표</a>')
    links_html = "<br>".join(other)

    # 표 아래에 쓸 실제 수치 한 줄 (40세 기준 '꾸준한 러너' 경계)
    ref_age = 40
    ref = fmt_time(boundary_seconds(45, ref_age, gk, dist["km"]))
    ref_line = (
        f"예를 들어 {ref_age}세 {gender['label']}이 {dist['label']}을 {ref} 안에 들어왔다면 "
        f"'꾸준한 러너' 구간에 들어갑니다."
    )

    body = f'''
<main class="gr-wrap">
<h1 class="gr-title">{h1}</h1>
<p class="gr-lead">{INTRO[dk]}</p>
{build_switch(dk, gk)}
{build_table(dist, gender)}
<p class="gr-note">{HOW_TO_READ} {ref_line}</p>

<h2 class="gr-h2">등급은 어떻게 계산했나</h2>
<p class="gr-p">{METHOD}</p>

<h2 class="gr-h2">자주 묻는 질문</h2>
<div class="gr-faq">
{faq_html}
</div>

<div class="gr-cta">
<p>표에 없는 나이거나, 기록을 정확히 넣어 보고 싶다면 계산기를 쓰는 편이 빠릅니다.</p>
<a href="level.html">내 기록으로 등급 계산하기 →</a>
</div>

<div class="gr-links">
{links_html}<br>
<a href="grade.html">전체 등급표 한눈에 보기</a><br>
<a href="index.html">다가오는 대회 일정 보기</a>
</div>
</main>
{FOOTER}
</body>
</html>
'''
    html = head_block(title, desc, slug, [page_ld, faq_ld, crumb_ld]) + body
    return slug, html


def build_method_page():
    """등급의 근거를 한곳에 모은 페이지.

    등급표마다 출처를 조금씩 적어 두는 대신, 전부 여기로 모으고 각 페이지가
    여기를 가리키게 한다. 경쟁 등급표를 여섯 개 살펴봤는데 숫자가 어디서
    나왔는지 확인할 수 있는 곳이 하나도 없었다. 체감으로 구간을 나누면
    보여 줄 계산 과정이 없기 때문이다. 그 자리가 비어 있어서 우리가 선다.
    """
    slug = "grade-method.html"
    title = "calrank 등급은 어떻게 매기나 — 기준표와 계산식 전부 공개 | calrank"
    desc = ("나이·성별 기준은 세계마스터즈육상연맹(WMA) 2025년 표를 그대로 씁니다. "
            "연령등급 % 계산식과 출처, 일곱 구간을 나눈 자리까지 전부 적어 두었어요. "
            "같은 숫자를 직접 따라 해 보실 수 있습니다.")

    # 예시는 모델로 직접 뽑는다. 손으로 적으면 모델이 바뀔 때 어긋난다.
    ex_age, ex_finish = 47, 52 * 60 + 30
    ex_std = wma.standard("male", "10km", ex_age)
    ex_pct = ex_std / ex_finish * 100
    ex_bound, ex_tier = next((b, l) for b, l in TIER_BOUNDS if ex_pct >= b)

    oc_rows = "".join(
        f"<tr><td>{d['label']}</td><td>{fmt_time(int(wma.OC['male'][d['key']]))}</td>"
        f"<td>{fmt_time(int(wma.OC['female'][d['key']]))}</td></tr>"
        for d in DISTANCES)

    tier_rows = "".join(
        f"<tr><td><b>{label}</b></td><td>{pct}% 이상</td>"
        f"<td>{fmt_time(boundary_seconds(pct, 40, 'male', 10.0))}</td>"
        f"<td>{fmt_time(boundary_seconds(pct, 40, 'female', 10.0))}</td></tr>"
        for pct, label in TIER_BOUNDS if pct > 0)
    tier_rows += (f"<tr><td><b>{TIER_BOUNDS[-1][1]}</b></td><td>{TIER_BOUNDS[-2][0]}% 미만</td>"
                  f"<td>그보다 느림</td><td>그보다 느림</td></tr>")

    page_ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebPage",
        "name": title, "description": desc, "url": f"{BASE}/{slug}", "inLanguage": "ko-KR",
    }, ensure_ascii=False)
    crumb_ld = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": f"{BASE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "기록 등급표", "item": f"{BASE}/grade.html"},
            {"@type": "ListItem", "position": 3, "name": "등급 기준과 근거"},
        ],
    }, ensure_ascii=False)

    body = f"""
<main class="gr-wrap">
<h1 class="gr-title">calrank 등급은 어떻게 매기나</h1>
<p class="gr-lead">러닝 등급표는 많은데, 그 숫자가 어디서 나왔는지 확인할 수 있는 곳은 드뭅니다.
체감이나 커뮤니티 의견으로 구간을 나누면 보여 줄 계산 과정이 없기 때문이에요.
calrank가 쓰는 기준표와 계산식, 구간을 나눈 자리까지 여기 전부 적어 두었습니다.
읽고 나면 같은 숫자를 직접 따라 해 보실 수 있습니다.</p>

<h2>한 줄로 말하면</h2>
<p>내 기록을 <b>그 나이·성별의 세계 최고 수준 기록</b>과 견줍니다. 그 비율이 <b>연령등급</b>이고,
100%면 세계기록 수준이에요. 등급 이름은 이 숫자를 읽기 쉽게 일곱 칸으로 나눈 것뿐입니다.</p>

<h2>나이·성별 기준 — WMA 2025 연령 기준표</h2>
<p>calrank가 쓰는 기준표는 저희가 만든 것이 아닙니다. <b>세계마스터즈육상연맹(World Masters
Athletics)</b> 의 연령 기준표로, 전 세계 마스터즈 대회가 연령대별 성적을 매길 때 쓰는 바로 그
표입니다. 2025년판은 2025년 1월 10일 <b>미국육상연맹(USATF) 마스터즈 장거리위원회</b> 의 승인을
거쳤고, 나이 한 살 단위(10~100세)로 남녀 각각의 기준기록이 거리별로 적혀 있습니다.</p>
<p>그래서 여기 나오는 등급은 calrank가 임의로 정한 것이 아니라, 이미 쓰이고 있는 국제 기준을
그대로 가져다 쓴 결과입니다.</p>
<details class="gr-srcbox">
<summary>직접 확인해 보고 싶다면 — 원본 표와 작성자</summary>
<ul class="gr-src">
<li><b>작성</b> Alan Jones · Rex Harvey · Tom Bernhard · Ken Young</li>
<li><b>원본</b> <a href="https://github.com/AlanLyttonJones/Age-Grade-Tables" rel="nofollow noopener" target="_blank">원본 표 내려받기</a> — 2025 Files 폴더</li>
<li><b>라이선스</b> CC0 1.0 Universal — 퍼블릭 도메인이라 누구나 받아서 확인할 수 있습니다</li>
</ul>
</details>
<p>calrank가 쓰는 네 거리(5km·하프·풀코스·10km)는 WMA가 다른 거리에서 끌어와 추정하지 않고
직접 산출하는 거리입니다. 그래서 거리끼리 환산하는 공식을 끼워 넣을 필요가 없어요.
각 거리의 기준을 그대로 씁니다.</p>

<h2>계산은 나눗셈 하나입니다</h2>
<p>{ex_age}세 남성이 10km를 {fmt_time(ex_finish)}에 뛰었다면:</p>
<div class="table-scroll">
<table class="tier-data-table">
<tr><th>항목</th><th>값</th><th>어디서</th></tr>
<tr><td>내 기록</td><td>{fmt_time(ex_finish)}</td><td>입력</td></tr>
<tr><td>{ex_age}세 남성 10km 기준기록</td><td>{fmt_time(ex_std)}</td><td>WMA 2025 표</td></tr>
<tr><td>연령등급</td><td><b>{ex_pct:.1f}%</b></td><td>{fmt_time(ex_std)} ÷ {fmt_time(ex_finish)}</td></tr>
<tr><td>등급</td><td><b>{ex_tier}</b></td><td>{ex_bound}% 이상 구간</td></tr>
</table>
</div>

<h2>100%는 세계기록 수준입니다</h2>
<p>기준기록이 실제 세계기록과 같은 숫자예요. 표가 최신이라는 뜻이기도 합니다.</p>
<div class="table-scroll">
<table class="tier-data-table">
<tr><th>거리</th><th>남성</th><th>여성</th></tr>
{oc_rows}
</table>
</div>
<p>WMA는 이 비율을 이렇게 읽습니다 — 90% 이상 World Class, 80% 이상 National,
70% 이상 Regional, 60% 이상 Local Class. 동호인 대부분은 60% 아래에 모여 있어서,
calrank는 그 아래 구간을 더 촘촘히 나눴습니다.</p>

<h2>일곱 구간을 나눈 자리</h2>
<p>여기는 calrank가 정했습니다. 숨길 이유가 없으니 그대로 적어 둡니다.
오른쪽 두 칸은 40세 기준으로 그 등급을 받는 가장 느린 10km 기록이에요.</p>
<div class="table-scroll">
<table class="tier-data-table">
<tr><th>등급</th><th>연령등급</th><th>40세 남성</th><th>40세 여성</th></tr>
{tier_rows}
</table>
</div>

<h2>다른 데이터로 맞춰 본 결과</h2>
<p>해외 러닝 데이터베이스(Running Level)가 내놓은 백분위를 같은 방식으로 환산해 봤습니다.
출처가 다른 두 자료가 비슷한 자리를 가리키면, 기준이 한쪽으로 치우치지 않았다는 뜻이 됩니다.</p>
<div class="table-scroll">
<table class="tier-data-table">
<tr><th>Running Level 백분위</th><th>연령등급으로 환산하면</th></tr>
<tr><td>상위 5%</td><td>약 72%</td></tr>
<tr><td>상위 20%</td><td>약 64%</td></tr>
<tr><td>상위 50% (중앙값)</td><td>약 57%</td></tr>
<tr><td>상위 80%</td><td>약 49%</td></tr>
<tr><td>상위 95%</td><td>약 41%</td></tr>
</table>
</div>

<h2>한 번의 기록이 말해 주는 폭</h2>
<p>등급을 소수점 한 자리까지 적어 두면 그만큼 정확해 보입니다. 하지만 같은 사람이
같은 몸 상태로 뛰어도 대회마다 기록은 흔들립니다. 컨디션, 코스, 날씨, 그날의 페이스
배분이 다 다르니까요.</p>
<p>그 흔들림이 얼마나 되는지는 이미 측정돼 있습니다. 같은 주자가 여러 대회에서 낸
기록을 모아 분석한 연구가 거리별 변동계수를 내놓았습니다.</p>
<div class="table-scroll">
<table class="tier-data-table">
<tr><th>거리</th><th>대회 간 기록 변동계수</th></tr>
<tr><td>도로 경주 · 크로스컨트리</td><td>1.2~1.9%</td></tr>
<tr><td>하프마라톤</td><td>2.7~4.2%</td></tr>
<tr><td>풀코스</td><td>2.6%</td></tr>
</table>
</div>
<p>위 값은 빠른 네 분위 주자 기준입니다. 같은 연구가 <strong>느린 주자는 빠른 주자보다
1.0~2.3배 더 흔들린다</strong>고 보고했으니, 동호인의 실제 폭은 이보다 넓을 수 있습니다.
calrank는 지어낸 숫자를 쓰지 않으려고 논문에 적힌 값을 그대로 쓰고, 넓어질 수 있다는
사실은 화면에 글로 적어 둡니다.</p>
<p>등급표 화면에서 '이 기록 하나로 어디까지 말할 수 있나'를 열면 이 폭이 등급 구간 위에
그려집니다. 쓸모는 여기에 있습니다 — 내 등급이 구간 한가운데에 있으면 다음 대회에서도
웬만해선 그대로이고, 경계에 걸쳐 있으면 바뀔 수 있다는 뜻입니다.</p>
<details class="gr-srcbox">
<summary>출처</summary>
<p>Hopkins WG, Hewson DJ. Variability of competitive performance of distance runners.
<em>Medicine &amp; Science in Sports &amp; Exercise</em>. 2001;33(9):1588-92.
<a href="https://pubmed.ncbi.nlm.nih.gov/11528349/" target="_blank" rel="noopener">PubMed 11528349</a></p>
</details>

<h2>직접 확인해 보시려면</h2>
<p>연령등급은 calrank만 쓰는 셈법이 아닙니다. 'age grading calculator'로 검색해 나오는
어느 계산기에 넣어도 같은 숫자가 나와요. 나이·성별·거리·기록만 넣으면 됩니다.
혹시 값이 다르면 그쪽이 2020년이나 2015년판 표를 쓰고 있을 가능성이 큽니다.</p>

<h2>이건 아닙니다</h2>
<p>공인 기록이 아닙니다. 대한육상연맹을 비롯한 어떤 기관이 발급하는 공식 등급도 아니고요.
대회 입상 기준이나 의학적 체력 평가와도 무관합니다. 코스 난이도·날씨·고도·GPS 오차에 따라
같은 사람도 기록이 몇 분씩 달라지니, 숫자 한 자리에 너무 무게를 두지 않으셔도 됩니다.</p>
<p>바꿔 말하면 이 등급이 보증하는 건 하나뿐이에요 —
<b>출처가 분명한 공개 표와 공개된 계산식으로 만들었고, 같은 결과를 누구나 재현할 수 있다는 것.</b></p>

<p class="gr-more"><a href="level.html">내 기록으로 바로 계산해 보기</a> ·
<a href="grade.html">거리별 전체 등급표</a> ·
<a href="cert.html">기록증 사진으로 확인하기</a></p>
</main>
{FOOTER}
</body>
</html>
"""
    return slug, head_block(title, desc, slug, [page_ld, crumb_ld]) + body


def build_hub():
    slug = "grade.html"
    title = "러닝 기록 등급표 — 거리별·나이별·성별 전체 정리 | calrank"
    # 같은 등급이라도 나이·성별에 따라 기록이 달라진다는 점을 숫자로 먼저 보인다.
    hub_m = fmt_time(boundary_seconds(45, 40, "male", 10.0))
    hub_f = fmt_time(boundary_seconds(45, 65, "female", 10.0))
    desc = (f"40세 남성 10km {hub_m}, 65세 여성 {hub_f} — 둘 다 같은 '꾸준한 러너' 등급입니다. "
            f"5km·10km·하프·풀코스 완주 기록을 나이와 성별까지 반영해 정리했습니다.")

    cards = []
    for d in DISTANCES:
        items = "".join(
            f'<a href="{slug_for(d["key"], g["key"])}">{d["search"]} · {g["label"]}</a>'
            for g in GENDERS
        )
        cards.append(f'<h2 class="gr-h2">{d["label"]}</h2>\n<div class="gr-switch">{items}</div>')

    # 연령대별 페이지는 여기서만 링크된다. 사이트맵에만 있고 링크가 없으면
    # 검색엔진이 "발견은 했지만 크롤링하지 않음" 으로 묶어 둔다.
    for dec in DECADES:
        items = "".join(
            f'<a href="{age_slug_for(d["key"], dec)}">{run_name(d)}</a>' for d in DISTANCES
        )
        cards.append(f'<h2 class="gr-h2">{dec}대 기록 등급표</h2>\n'
                     f'<div class="gr-switch">{items}</div>')

    cards_html = "\n".join(cards)

    # 허브에는 가장 수요가 큰 10km 남녀 40세 기준 요약표를 직접 싣는다.
    summary_rows = []
    for d in DISTANCES:
        for g in GENDERS:
            t = fmt_time(boundary_seconds(45, 40, g["key"], d["km"]))
            u = fmt_time(boundary_seconds(59, 40, g["key"], d["km"]))
            summary_rows.append(
                f'<tr><th>{d["label"]} {g["label"]}</th><td>{u}</td><td>{t}</td></tr>'
            )
    summary = (
        '<div class="gr-tablebox"><table class="gr-table">\n'
        "<thead><tr><th>구분</th><th>매우 좋은 편</th><th>꾸준한 러너</th></tr></thead>\n"
        "<tbody>\n" + "\n".join(summary_rows) + "\n</tbody></table></div>"
    )

    page_ld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": title, "description": desc, "url": f"{BASE}/{slug}", "inLanguage": "ko-KR",
    }, ensure_ascii=False)
    crumb_ld = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": f"{BASE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "기록 등급표"},
        ],
    }, ensure_ascii=False)

    body = f'''
<main class="gr-wrap">
<h1 class="gr-title">러닝 기록 등급표</h1>
<p class="gr-lead">같은 1시간이라도 25세 남성이 뛴 10km와 62세 여성이 뛴 10km는 전혀 다른 의미를 가집니다.
그래서 절대 기록만 늘어놓은 표는 실제로 내 수준을 알려 주지 못합니다. calrank의 등급표는 나이와 성별 차이를
먼저 보정한 뒤 같은 조건의 동호인 사이에서 내 기록이 어디쯤인지 보여 줍니다. 거리와 성별을 고르면
20대부터 75세까지 연령별 기준 기록이 표로 나옵니다.</p>

{cards_html}

<h2 class="gr-h2">한눈에 보는 40세 기준</h2>
<p class="gr-p">가장 많이 찾는 40세 기준으로, 각 거리에서 '매우 좋은 편'과 '꾸준한 러너'에 들어가려면
어느 정도 기록이 필요한지 추려 봤습니다. 다른 나이는 각 등급표에서 확인하세요.</p>
{summary}

<h2 class="gr-h2">등급은 어떻게 계산했나</h2>
<p class="gr-p">{METHOD}</p>

<div class="gr-cta">
<p>표를 찾아보는 대신 내 기록을 바로 넣어 보고 싶다면 계산기가 더 빠릅니다.</p>
<a href="level.html">내 기록으로 등급 계산하기 →</a>
</div>

<div class="gr-links">
<a href="myrank.html">내 기록 저장하고 랭킹에서 비교하기</a><br>
<a href="index.html">다가오는 대회 일정 보기</a>
</div>
</main>
{FOOTER}
</body>
</html>
'''
    return slug, head_block(title, desc, slug, [page_ld, crumb_ld]) + body



# ──────────────────────────────────────────────────────────────
# 연령대별 페이지
#
# 네이버 검색어에 "50대 10km마라톤 기록" 이 이미 들어오고 있다(클릭 5, 노출 72).
# 거리·성별 표는 나이가 세로축이라 "50대" 로 검색한 사람이 자기 줄을 찾아야 한다.
# 연령대를 제목으로 못박은 페이지를 따로 둔다. 아쿠아슬론 페이지가 통한 것과
# 같은 이치다 — 좁고 구체적인 말에는 경쟁자가 거의 없다.
#
# 표는 한 살 단위다. 기존 거리별 표가 5년 단위라 "53세" 인 사람은 어림잡아야 했다.
# ──────────────────────────────────────────────────────────────

DECADES = [20, 30, 40, 50, 60, 70]


def run_name(dist):
    """연령대 페이지에서 쓸 이름. 반드시 "마라톤" 으로 끝나게 한다.

    노리는 검색어가 "50대 10km마라톤 기록" 이라 "마라톤" 이 빠지면 안 된다.
    끝을 "마라톤" 으로 통일해 두면 뒤에 붙는 조사도 '을' 하나로 맞는다
    ("10km을" 처럼 틀리는 일이 없다).
    """
    name = dist["search"]
    return name if name.endswith("마라톤") else f"{name} 마라톤"


def age_slug_for(dist_key, decade):
    return f"grade-{dist_key}-{decade}s.html"


def decade_ages(decade):
    # 표는 75세까지만 세운다. WMA 기준표는 100세까지 있지만, 그 위는 표본이
    # 얇아 한 줄씩 늘려 봐야 읽는 사람에게 도움이 되지 않는다. 계산기는 받는다.
    return [a for a in range(decade, decade + 10) if a <= 75]


def build_age_table(dist, gender, decade):
    km, gk = dist["km"], gender["key"]
    head_cells = "".join(f"<th>{label}</th>" for _, label in TABLE_TIERS)
    rows = []
    for age in decade_ages(decade):
        cells = "".join(
            f"<td>{fmt_time(boundary_seconds(bound, age, gk, km))}</td>"
            for bound, _ in TABLE_TIERS
        )
        rows.append(f"<tr><th>{age}세</th>{cells}<td>{LAST_TIER_LABEL}</td></tr>")
    return (
        '<div class="gr-tablebox"><table class="gr-table">\n'
        f"<thead><tr><th>나이</th>{head_cells}<th>그 이상</th></tr></thead>\n<tbody>\n"
        + "\n".join(rows) + "\n</tbody>\n</table></div>\n"
        '<p class="gr-swipe">표를 좌우로 밀면 나머지 등급이 보입니다. 나이 칸은 고정됩니다.</p>'
    )


def build_age_switch(cur_dist, cur_decade):
    dec = "".join(
        '<a href="{}"{}>{}대</a>'.format(
            age_slug_for(cur_dist, d), ON if d == cur_decade else "", d)
        for d in DECADES
    )
    dists = "".join(
        '<a href="{}"{}>{}</a>'.format(
            age_slug_for(d["key"], cur_decade), ON if d["key"] == cur_dist else "", d["label"])
        for d in DISTANCES
    )
    return f'<div class="gr-switch">{dec}</div>\n<div class="gr-switch">{dists}</div>'


def build_age_page(dist, decade):
    dk = dist["key"]
    slug = age_slug_for(dk, decade)
    ages = decade_ages(decade)
    rname = run_name(dist)
    title = f"{decade}대 {rname} 기록 — 남녀 나이별 등급표 | calrank"
    h1 = f"{decade}대 {rname} 기록 등급표 — 남녀 한 살 단위"

    # 본문과 소개에 쓸 실제 수치. 연령대 가운데 나이의 '꾸준한 러너' 경계.
    mid = ages[len(ages) // 2]
    ref_m = fmt_time(boundary_seconds(45, mid, "male", dist["km"]))
    ref_f = fmt_time(boundary_seconds(45, mid, "female", dist["km"]))

    # 검색 결과에서 보이는 두 줄이다. 범위를 설명하는 대신 숫자를 먼저 보여
    # 준다. 클릭할지 말지는 "내 기록이 이 안쪽인가"로 갈리기 때문이다.
    desc = (
        f"{mid}세 기준 {ref_m}(남성) · {ref_f}(여성) 안에 들어오면 '꾸준한 러너'입니다. "
        f"{decade}대 {rname} 기록을 한 살 단위 표에서 확인하고 내 기록을 바로 대입해 보세요."
    )

    lead = (
        f"{decade}대에 {rname}을 뛰고 나면 \"이 정도면 괜찮은 건가\" 싶어집니다. "
        f"같은 기록이라도 20대와 {decade}대의 의미가 다르기 때문에, 또래 기준으로 봐야 "
        f"내 위치가 보입니다. {mid}세 기준으로 {ref_m}(남성) · {ref_f}(여성) 안에 "
        f"들어오면 '꾸준한 러너' 구간입니다."
    )

    faqs = [
        (f"{decade}대 {rname} 기록은 보통 어느 정도인가요?",
         "이 표는 참가자 평균이 아니라 나이·성별을 보정한 등급 경계입니다. "
         f"{mid}세 남성이라면 {ref_m}, 여성이라면 {ref_f} 가 '꾸준한 러너' 구간에 들어가는 "
         "기준선입니다. 실제 대회 참가자 분포와는 다를 수 있습니다."),
        ("나이가 들면 기록이 얼마나 떨어지나요?",
         "WMA 표를 보면 10km 기준기록이 20대에서 가장 빠르고, 50세는 그보다 약 12%, 70세는 약 35% "
         "정도로 잡습니다. 한 살 단위로 경계가 조금씩 움직이는 이유가 이것입니다."),
        ("표에 없는 거리는 어떻게 보나요?",
         "계산기에 기록을 넣으면 5km·하프·풀코스까지 같은 잣대로 비교해 줍니다. "
         "결과를 이미지로 저장할 수도 있습니다."),
    ]
    faq_html = "\n".join(
        f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faqs)
    faq_ld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs],
    }, ensure_ascii=False)
    page_ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebPage",
        "name": title, "description": desc, "url": f"{BASE}/{slug}", "inLanguage": "ko-KR",
        "isPartOf": {"@type": "WebSite", "name": "calrank", "url": f"{BASE}/"},
    }, ensure_ascii=False)
    crumb_ld = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": f"{BASE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "기록 등급표", "item": f"{BASE}/grade.html"},
            {"@type": "ListItem", "position": 3, "name": h1},
        ],
    }, ensure_ascii=False)

    tables = "\n".join(
        f'<h2 class="gr-h2">{decade}대 {g["label"]} {dist["search"]} 등급표</h2>\n'
        + build_age_table(dist, g, decade)
        for g in GENDERS
    )
    links = "<br>".join(
        [f'<a href="{slug_for(dk, g["key"])}">{rname} {g["label"]} 전체 나이 등급표</a>'
         for g in GENDERS]
        + [f'<a href="{age_slug_for(d["key"], decade)}">{decade}대 {run_name(d)} 등급표</a>'
           for d in DISTANCES if d["key"] != dk]
    )

    body = f"""
<main class="gr-wrap">
<h1 class="gr-title">{h1}</h1>
<p class="gr-lead">{lead}</p>
{build_age_switch(dk, decade)}
{tables}
<p class="gr-note">{HOW_TO_READ}</p>

<div class="gr-cta">
<p>표에서 찾는 대신 기록을 넣으면 등급과 다음 등급까지 남은 시간이 바로 나옵니다. 결과는 이미지로 저장해 공유할 수 있습니다.</p>
<a href="level.html">내 기록으로 등급 계산하기 →</a>
</div>

<h2 class="gr-h2">등급은 어떻게 계산했나</h2>
<p class="gr-p">{METHOD}</p>

<h2 class="gr-h2">자주 묻는 질문</h2>
<div class="gr-faq">
{faq_html}
</div>

<div class="gr-links">
{links}<br>
<a href="grade.html">전체 등급표 한눈에 보기</a><br>
<a href="index.html">다가오는 대회 일정 보기</a>
</div>
</main>
{FOOTER}
</body>
</html>
"""
    return slug, head_block(title, desc, slug, [page_ld, faq_ld, crumb_ld]) + body


def update_sitemap(slugs):
    path = ROOT / "sitemap.xml"
    if not path.exists():
        print("[grade pages] sitemap.xml 없음 — 건너뜁니다.")
        return 0
    xml = path.read_text(encoding="utf-8")
    marker = "</urlset>"
    added = ""
    count = 0
    for slug in slugs:
        loc = f"{BASE}/{slug}"
        if f"<loc>{loc}</loc>" in xml:
            continue
        added += (
            "  <url>\n"
            f"    <loc>{loc}</loc>\n"
            "    <changefreq>monthly</changefreq>\n"
            "    <priority>0.7</priority>\n"
            "  </url>\n"
        )
        count += 1
    if added and marker in xml:
        path.write_text(xml.replace(marker, added + marker), encoding="utf-8")
    return count


def main():
    verify_models()

    slugs = []
    for d in DISTANCES:
        for g in GENDERS:
            slug, html = build_page(d, g)
            (ROOT / slug).write_text(html, encoding="utf-8")
            slugs.append(slug)

    for d in DISTANCES:
        for dec in DECADES:
            slug, html = build_age_page(d, dec)
            (ROOT / slug).write_text(html, encoding="utf-8")
            slugs.append(slug)

    hub_slug, hub_html = build_hub()
    (ROOT / hub_slug).write_text(hub_html, encoding="utf-8")
    slugs.append(hub_slug)

    m_slug, m_html = build_method_page()
    (ROOT / m_slug).write_text(m_html, encoding="utf-8")
    slugs.append(m_slug)

    # 기록증 업로드 페이지는 손으로 관리하지만 사이트맵에는 여기서 함께 넣는다
    if (ROOT / "cert.html").exists():
        slugs.append("cert.html")

    added = update_sitemap(slugs)
    print(f"[grade pages] {len(slugs)}개 페이지 생성, 사이트맵 추가 {added}개")


if __name__ == "__main__":
    main()

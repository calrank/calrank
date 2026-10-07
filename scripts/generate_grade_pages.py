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

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# level.js와 동일한 모델 (아래 verify_against_level_js()가 매 실행마다 대조)
# ---------------------------------------------------------------------------
AGE_ANCHORS = [
    (20, 0.90), (30, 0.93), (40, 0.96), (50, 1.00),
    (60, 1.10), (70, 1.25), (80, 1.45),
]
GENDER_FACTOR = {"male": 1.00, "female": 1.11}
RIEGEL = 1.06

# 오름차순(빠른 순): bound = 해당 등급의 '느린 쪽' 경계 (초/km, 10km 환산 기준)
TIER_BOUNDS = [
    (240, "상당한 러너"),
    (270, "러닝 상급자"),
    (300, "매우 좋은 편"),
    (348, "상당히 좋은 편"),
    (390, "평균 이상"),
    (450, "보통"),
    (540, "초보/기초체력"),
]
# 마지막 구간(540)은 그 이상도 같은 등급이라 표에서는 열로 세우지 않고
# "그 이상" 칸으로 합친다.
TABLE_TIERS = TIER_BOUNDS[:-1]
LAST_TIER_LABEL = TIER_BOUNDS[-1][1]

AGES = [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75]

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
def age_factor(age: float) -> float:
    if age <= AGE_ANCHORS[0][0]:
        return AGE_ANCHORS[0][1]
    if age >= AGE_ANCHORS[-1][0]:
        return AGE_ANCHORS[-1][1]
    for i in range(len(AGE_ANCHORS) - 1):
        a0, f0 = AGE_ANCHORS[i]
        a1, f1 = AGE_ANCHORS[i + 1]
        if a0 <= age <= a1:
            ratio = (age - a0) / (a1 - a0)
            return f0 + (f1 - f0) * ratio
    raise ValueError(age)


def normalized_pace(finish_sec: float, age: int, gender: str, km: float) -> float:
    """level.js analyze()와 연산 순서까지 동일하게 맞춘 환산 페이스."""
    equiv10k_time = finish_sec * (10.0 / km) ** RIEGEL
    equiv10k_pace = equiv10k_time / 10.0
    return equiv10k_pace / age_factor(age) / GENDER_FACTOR[gender]


def boundary_seconds(bound: int, age: int, gender: str, km: float) -> int:
    """환산 페이스가 bound 이하가 되는 가장 느린(큰) 완주 초를 정수로 구한다.

    해석적으로 구한 값은 부동소수점 오차 때문에 계산기와 1초 차이로 등급이
    갈릴 수 있어, 실제 판정 함수로 양쪽을 한 번 더 조여 준다.
    """
    s = math.floor(bound * age_factor(age) * GENDER_FACTOR[gender] * 10.0 * (km / 10.0) ** RIEGEL)
    while s > 0 and normalized_pace(s, age, gender, km) > bound:
        s -= 1
    while normalized_pace(s + 1, age, gender, km) <= bound:
        s += 1
    return s


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
def verify_against_level_js() -> None:
    path = ROOT / "level.js"
    if not path.exists():
        sys.exit("[grade pages] level.js를 찾을 수 없어 중단합니다.")
    src = path.read_text(encoding="utf-8")

    anchors = [(int(a), float(f)) for a, f in re.findall(r"\[\s*(\d+)\s*,\s*(\d*\.?\d+)\s*\]", src)[:len(AGE_ANCHORS)]]
    if anchors != AGE_ANCHORS:
        sys.exit(f"[grade pages] AGE_ANCHORS 불일치: level.js={anchors} / 스크립트={AGE_ANCHORS}")

    gm = re.search(r"GENDER_FACTOR\s*=\s*\{\s*male:\s*([\d.]+)\s*,\s*female:\s*([\d.]+)", src)
    if not gm or (float(gm.group(1)), float(gm.group(2))) != (GENDER_FACTOR["male"], GENDER_FACTOR["female"]):
        sys.exit("[grade pages] GENDER_FACTOR 불일치 — level.js를 확인하세요.")

    rm = re.search(r"Math\.pow\(\s*d2Km\s*/\s*d1Km\s*,\s*([\d.]+)\s*\)", src)
    if not rm or float(rm.group(1)) != RIEGEL:
        sys.exit("[grade pages] Riegel 지수 불일치 — level.js를 확인하세요.")

    bounds = re.findall(r"\[\s*(\d+)\s*,\s*\"([^\"]+)\"\s*,", src)
    parsed = [(int(b), label) for b, label in bounds]
    if parsed != TIER_BOUNDS:
        sys.exit(f"[grade pages] TIER_BOUNDS 불일치: level.js={parsed}")

    verify_against_grade_model()
    print("[grade pages] level.js 상수 대조 통과")


def verify_against_grade_model() -> None:
    """grade-model.js(계산기·기록증 페이지가 공유하는 모델)도 같은 상수인지 본다.

    같은 기록에 서로 다른 등급이 나오는 것이 이 프로젝트에서 실제로 났던
    문제라, 모델 사본이 생길 때마다 여기서 함께 대조한다."""
    path = ROOT / "grade-model.js"
    if not path.exists():
        return
    src = path.read_text(encoding="utf-8")

    anchors = [(int(a), float(f)) for a, f in
               re.findall(r"\[\s*(\d+)\s*,\s*(\d*\.?\d+)\s*\]", src)[:len(AGE_ANCHORS)]]
    if anchors != AGE_ANCHORS:
        sys.exit(f"[grade pages] grade-model.js AGE_ANCHORS 불일치: {anchors}")

    gm = re.search(r"GENDER_FACTOR\s*=\s*\{\s*male:\s*([\d.]+)\s*,\s*female:\s*([\d.]+)", src)
    if not gm or (float(gm.group(1)), float(gm.group(2))) != (GENDER_FACTOR["male"], GENDER_FACTOR["female"]):
        sys.exit("[grade pages] grade-model.js GENDER_FACTOR 불일치")

    rm = re.search(r"RIEGEL\s*=\s*([\d.]+)", src)
    if not rm or float(rm.group(1)) != RIEGEL:
        sys.exit("[grade pages] grade-model.js Riegel 지수 불일치")

    bounds = [(int(b), lab) for b, lab in re.findall(r"\[\s*(\d+)\s*,\s*\"([^\"]+)\"\s*\]", src)]
    if bounds != TIER_BOUNDS:
        sys.exit(f"[grade pages] grade-model.js TIER_BOUNDS 불일치: {bounds}")

    print("[grade pages] grade-model.js 상수 대조 통과")


# ---------------------------------------------------------------------------
# 본문 카피 (거리별로 결이 다르게)
# ---------------------------------------------------------------------------
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
        "아래 표는 Riegel 환산으로 거리 차이를 보정하고 나이·성별까지 반영해, "
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
    "등급 구분은 거리마다 따로 두지 않고 10km 환산 페이스 하나로 통일했습니다. "
    "서로 다른 거리의 기록을 같은 잣대로 비교하기 위해 러닝에서 널리 쓰이는 "
    "Riegel 환산식(지수 1.06)을 사용했고, 여기에 연령대별 기량 감소와 성별 차이를 "
    "보정 계수로 반영했습니다. 50세를 기준(1.00)으로 두고 젊을수록 더 엄격한 기준이, "
    "나이가 많을수록 완화된 기준이 적용되는 구조입니다."
)


def faq_items(dist, gender):
    d, g = dist["label"], gender["label"]
    return [
        (
            f"{dist['search']} 기록이 몇 분이면 잘 뛰는 편인가요?",
            f"나이에 따라 기준이 꽤 달라집니다. 같은 기록이라도 20대와 60대의 평가가 다르기 때문에, "
            f"위 표에서 본인 나이대 줄을 먼저 찾은 뒤 기록이 어느 칸에 들어가는지 보시는 게 정확합니다. "
            f"{g} 기준으로 '평균 이상' 칸 안쪽이면 또래 동호인 평균보다 좋은 편이라고 볼 수 있습니다.",
        ),
        (
            "나이를 왜 보정하나요?",
            "같은 훈련을 해도 심폐 능력과 회복력은 연령에 따라 차이가 납니다. 보정 없이 절대 기록만 "
            "비교하면 나이가 많은 러너는 아무리 잘 달려도 늘 아래쪽에 머물게 되죠. "
            "그래서 50세를 기준점으로 두고 연령별 계수를 적용해, '같은 조건이라면 어느 정도인가'를 "
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
NAV = """<header class="site-header">
<div class="wrap header-inner">
<a href="index.html" class="wordmark">CALRANK</a>
<nav class="main-nav">
<a href="index.html" class="nav-link">캘린더</a>
<a href="ranking.html" class="nav-link">대회랭킹</a>
<a href="news.html" class="nav-link">종목뉴스</a>
<a href="column.html" class="nav-link">칼럼</a>
<a href="grade.html" class="nav-link">등급표</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>"""

FOOTER = """<footer class="site-footer">
<div class="wrap">
<p>등급 기준은 일반적으로 통용되는 동호인 페이스 구간을 참고한 자체 지표이며, 공식 통계나 의학적 판단이 아닙니다.</p>
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
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/favicon.svg">
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
    desc = (
        f"{dist['label']} 완주 기록이 어느 수준인지 나이별로 정리한 {gender['label']} 등급표입니다. "
        f"20대부터 75세까지 연령별 기준 기록을 표로 확인하고, 계산기로 내 기록을 바로 대입해 보세요."
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

    # 표 아래에 쓸 실제 수치 한 줄 (40세 기준 '평균 이상' 경계)
    ref_age = 40
    ref = fmt_time(boundary_seconds(390, ref_age, gk, dist["km"]))
    ref_line = (
        f"예를 들어 {ref_age}세 {gender['label']}이 {dist['label']}을 {ref} 안에 들어왔다면 "
        f"'평균 이상' 구간에 들어갑니다."
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


def build_hub():
    slug = "grade.html"
    title = "러닝 기록 등급표 — 거리별·나이별·성별 전체 정리 | calrank"
    desc = ("5km·10km·하프·풀코스 완주 기록이 어느 수준인지 나이와 성별까지 반영해 정리한 "
            "러닝 기록 등급표입니다. 거리와 성별을 골라 바로 확인하세요.")

    cards = []
    for d in DISTANCES:
        items = "".join(
            f'<a href="{slug_for(d["key"], g["key"])}">{d["search"]} · {g["label"]}</a>'
            for g in GENDERS
        )
        cards.append(f'<h2 class="gr-h2">{d["label"]}</h2>\n<div class="gr-switch">{items}</div>')
    cards_html = "\n".join(cards)

    # 허브에는 가장 수요가 큰 10km 남녀 40세 기준 요약표를 직접 싣는다.
    summary_rows = []
    for d in DISTANCES:
        for g in GENDERS:
            t = fmt_time(boundary_seconds(390, 40, g["key"], d["km"]))
            u = fmt_time(boundary_seconds(300, 40, g["key"], d["km"]))
            summary_rows.append(
                f'<tr><th>{d["label"]} {g["label"]}</th><td>{u}</td><td>{t}</td></tr>'
            )
    summary = (
        '<div class="gr-tablebox"><table class="gr-table">\n'
        "<thead><tr><th>구분</th><th>매우 좋은 편</th><th>평균 이상</th></tr></thead>\n"
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
<p class="gr-p">가장 많이 찾는 40세 기준으로, 각 거리에서 '매우 좋은 편'과 '평균 이상'에 들어가려면
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
    verify_against_level_js()

    slugs = []
    for d in DISTANCES:
        for g in GENDERS:
            slug, html = build_page(d, g)
            (ROOT / slug).write_text(html, encoding="utf-8")
            slugs.append(slug)

    hub_slug, hub_html = build_hub()
    (ROOT / hub_slug).write_text(hub_html, encoding="utf-8")
    slugs.append(hub_slug)

    # 기록증 업로드 페이지는 손으로 관리하지만 사이트맵에는 여기서 함께 넣는다
    if (ROOT / "cert.html").exists():
        slugs.append("cert.html")

    added = update_sitemap(slugs)
    print(f"[grade pages] {len(slugs)}개 페이지 생성, 사이트맵 추가 {added}개")


if __name__ == "__main__":
    main()

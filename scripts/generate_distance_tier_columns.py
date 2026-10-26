"""거리별 '내 기록은 어느 수준일까' 칼럼을 만든다.

column-10km-age-gender-tier.html 한 장이 네이버 노출의 약 75%를 만들고 있다
(162클릭 / 4,176노출). 같은 질문을 5km·하프·풀코스로도 던지는 사람이 있는데
그 페이지가 없었다. 10km 페이지와 같은 출처(Running Level)·같은 구조로
세 거리를 추가한다.

10km 페이지는 이미 잘 돌고 있으므로 다시 만들지 않는다. 다른 거리로 가는
링크만 끼워 넣는다.

표의 숫자는 지어내지 않는다. Running Level 공개 데이터를 그대로 옮겼고,
10km 값을 이미 올라가 있는 페이지와 대조해 일치를 확인했다.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_nav import site_header  # noqa: E402
from distance_tier_data import DECADES, TIER_TABLES, DIST_COPY  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app"
TIER_NAMES = ["비기너", "노비스", "인터미디엇", "어드밴스드", "엘리트"]

# 10km 은 이미 있는 페이지를 쓴다. 링크 묶음에는 함께 넣는다.
SERIES = [
    ("5km", "5km", "column-5km-age-gender-tier.html"),
    ("10km", "10km", "column-10km-age-gender-tier.html"),
    ("half", "하프마라톤", "column-half-age-gender-tier.html"),
    ("full", "풀코스", "column-full-age-gender-tier.html"),
]


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


DIST_KM = {"5km": 5.0, "10km": 10.0, "half": 21.0975, "full": 42.195}
GRADE_SLUG = {"5km": "5km", "10km": "10km", "half": "half", "full": "full"}


def _sec(t: str) -> int:
    """'1:23:45' 또는 '48:15' 를 초로."""
    p = [int(x) for x in t.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def _mmss(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def _hms(sec: float) -> str:
    sec = int(round(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# 목표 기록별로 몇 분에 어느 지점을 지나야 하는지. 러너가 실제로 팔에 적어 가는 표다.
# 숫자는 전부 산수라 지어낼 여지가 없다.
SPLIT_TARGETS = {
    "5km":  [("20분", 1200), ("22분", 1320), ("25분", 1500), ("27분", 1620),
             ("30분", 1800), ("35분", 2100)],
    "10km": [("40분", 2400), ("45분", 2700), ("50분", 3000), ("55분", 3300),
             ("60분", 3600), ("70분", 4200)],
    "half": [("1시간 30분", 5400), ("1시간 40분", 6000), ("1시간 50분", 6600),
             ("2시간", 7200), ("2시간 15분", 8100), ("2시간 30분", 9000)],
    "full": [("서브3", 10800), ("3시간 30분", 12600), ("서브4", 14400),
             ("4시간 30분", 16200), ("5시간", 18000), ("5시간 30분", 19800)],
}
# 구간을 나누는 지점(km). 짧은 거리는 촘촘하게, 긴 거리는 5km 단위로.
SPLIT_MARKS = {
    "5km": [1, 2, 3, 4, 5],
    "10km": [2, 4, 6, 8, 10],
    "half": [5, 10, 15, 20, 21.0975],
    "full": [5, 10, 15, 20, 21.0975, 25, 30, 35, 40, 42.195],
}


def split_table(dist: str) -> str:
    km = DIST_KM[dist]
    marks = SPLIT_MARKS[dist]
    head = "<tr><th>목표</th>" + "".join(
        f"<th>{'하프' if abs(m-21.0975)<0.01 else ('완주' if abs(m-km)<0.01 else f'{m:g}km')}</th>"
        for m in marks) + "</tr>"
    rows = []
    for label, total in SPLIT_TARGETS[dist]:
        cells = "".join(f"<td>{_hms(total * m / km)}</td>" for m in marks)
        rows.append(f"<tr><td>{label}</td>{cells}</tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            + head + "\n" + "\n".join(rows) + "\n</table>\n</div>")


# Riegel(1981) 환산. T2 = T1 x (D2/D1)^1.06
RIEGEL_B = 1.06
# 이 거리 기록으로 나머지 세 거리를 가늠한다. 방향을 하나로 두는 쪽이 읽기 쉽다.
RIEGEL_SAMPLES = {
    "5km":  [1080, 1200, 1380, 1500, 1680, 1800],
    "10km": [2400, 2700, 3000, 3300, 3600, 4200],
    "half": [5400, 6000, 6600, 7200, 8100, 9000],
    "full": [10800, 12600, 14400, 16200, 18000, 19800],
}
RIEGEL_LIMIT = 230 * 60          # Riegel 이 밝힌 적용 상한(230분)
# 10km 페이지는 손으로 쓴 것이라 DIST_COPY 에 없다. 이름만 따로 둔다.
DIST_NAME = {"5km": "5km", "10km": "10km", "half": "하프마라톤", "full": "풀코스"}


def riegel_table(dist: str) -> str:
    from_km = DIST_KM[dist]
    others = [(k, DIST_NAME[k], DIST_KM[k]) for k in ("5km", "10km", "half", "full")
              if k != dist]
    head = (f"<tr><th>{DIST_NAME[dist]} 기록</th>"
            + "".join(f"<th>{lab}</th>" for _, lab, _ in others) + "</tr>")
    rows = []
    for t in RIEGEL_SAMPLES[dist]:
        cells = ""
        for _, _, to_km in others:
            pred = t * (to_km / from_km) ** RIEGEL_B
            # 범위를 넘은 값은 표시해 둔다. 숨기는 것보다 적어 두는 쪽이 정직하다.
            mark = "*" if pred > RIEGEL_LIMIT else ""
            cells += f"<td>{_hms(pred)}{mark}</td>"
        rows.append(f"<tr><td>{_hms(t)}</td>{cells}</tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            + head + "\n" + "\n".join(rows) + "\n</table>\n</div>")


def median_table(dist: str) -> str:
    """'평균 기록'을 찾는 사람이 가장 많다. 중앙값(인터미디엇 열)을 페이스와 함께 뽑는다.
    산술평균이 아니라 중앙값을 쓰는 이유는 러닝 기록이 느린 쪽으로 꼬리가 길어서다."""
    km = DIST_KM[dist]
    rows = []
    for i, dec in enumerate(DECADES):
        m = TIER_TABLES[(dist, "male")][i][2]      # 인터미디엇 = 상위 50%
        f = TIER_TABLES[(dist, "female")][i][2]
        rows.append(f"<tr><td>{dec}</td><td>{m}</td><td>{_mmss(_sec(m)/km)}</td>"
                    f"<td>{f}</td><td>{_mmss(_sec(f)/km)}</td></tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            "<tr><th>나이대</th><th>남성 중앙값</th><th>남성 페이스</th>"
            "<th>여성 중앙값</th><th>여성 페이스</th></tr>\n"
            + "\n".join(rows) + "\n</table>\n</div>")


def pace_table(dist: str) -> str:
    """시계에 페이스만 찍혀 있는 경우. 완주 시간으로 바꿔 줘야 표에서 찾을 수 있다."""
    km = DIST_KM[dist]
    step = 15 if dist in ("5km", "10km") else 15
    lo, hi = (240, 450) if dist in ("5km", "10km") else (270, 510)
    rows = []
    for p in range(lo, hi + 1, step):
        rows.append(f"<tr><td>{_mmss(p)}/km</td><td>{_hms(p*km)}</td></tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            f"<tr><th>평균 페이스</th><th>{DIST_COPY[dist]['label']} 완주 시간</th></tr>\n"
            + "\n".join(rows) + "\n</table>\n</div>")


def decade_links(dist: str) -> str:
    key = GRADE_SLUG[dist]
    items = " · ".join(
        f'<a href="grade-{key}-{d}s.html" style="color:var(--accent-ink);">{d}대</a>'
        for d in (20, 30, 40, 50, 60, 70))
    return f'<p style="font-size:14px;line-height:2;">{items}</p>'


def tier_table(dist: str, gender: str) -> str:
    head = ("<tr><th>나이대</th>"
            + "".join(f'<th{" class=\"tc-elite\"" if n == "엘리트" else ""}>{n}</th>'
                      for n in TIER_NAMES)
            + "</tr>")
    rows = []
    for i, dec in enumerate(DECADES):
        vals = TIER_TABLES[(dist, gender)][i]
        cells = "".join(
            f'<td{" class=\"tc-elite\"" if k == 4 else ""}>{v}</td>'
            for k, v in enumerate(vals))
        rows.append(f"<tr><td>{dec}</td>{cells}</tr>")
    return ('<div class="table-scroll">\n<table class="tier-data-table">\n'
            + head + "\n" + "\n".join(rows) + "\n</table>\n</div>")


def series_links(current: str) -> str:
    """거리끼리 서로 닿게 한다. 같은 질문을 다른 거리로 하는 사람이 많다."""
    items = []
    for key, name, slug in SERIES:
        if key == current:
            items.append(f'<strong style="color:var(--ink,#fff);">{name}</strong>')
        else:
            items.append(f'<a href="{slug}" style="color:var(--accent,#FF3D1A);">{name}</a>')
    return ('<p style="font-size:13.5px;line-height:1.9;color:var(--ink-soft,#9A9A9A);'
            'margin:28px 0 0;padding-top:18px;border-top:1px solid var(--border,#2A2A2A);">'
            '다른 거리의 등급표 · ' + " · ".join(items) + "</p>")


def build(dist: str) -> tuple[str, str, str, str]:
    c = DIST_COPY[dist]
    slug = f"column-{c['slug']}-age-gender-tier.html"
    title = f"{c['title']} | calrank"
    desc = c["desc"]
    tags = "".join(
        f'<a href="{href}" class="column-tag">{t}</a>\n'
        for href, t in [
            ("index.html?sport=marathon", f"#{c['nav_name'].replace(' ', '')}"),
            ("column.html", "#러닝등급표"), ("column.html", "#나이별기록"),
            ("column.html", "#20대러닝"), ("column.html", "#30대러닝"),
            ("column.html", "#40대러닝"), ("column.html", "#50대러닝"),
            ("column.html", "#60대러닝"),
            ("column.html", f"#남자{c['label']}기록"),
            ("column.html", f"#여자{c['label']}기록"),
            ("myrank.html", "#내랭크"),
        ])
    why = "\n".join(f"<p>{esc(p)}</p>" for p in c["why"])

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:url" content="{SITE}/{slug}">
<meta property="og:locale" content="ko_KR">
<link rel="canonical" href="{SITE}/{slug}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="style.css">
<style>
  .column-wrap {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
  .column-meta {{ font-size: 13px; color: var(--ink-faint, #8E8E8E); margin-bottom: 12px; }}
  .column-title {{ font-family: var(--font-display); font-size: clamp(24px, 3.8vw, 36px); line-height: 1.3; margin-bottom: 20px; }}
  .column-body {{ font-size: 16px; line-height: 1.9; color: #E8E4E1; }}
  .column-body h2 {{ font-size: 20px; margin: 36px 0 12px; color: #fff; }}
  .column-body p {{ margin-bottom: 16px; }}
  .column-tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 24px; }}
  .column-tag {{ font-size: 12px; padding: 5px 12px; border: 1px solid var(--border, #2A2A2A); border-radius: 999px; color: #B8B0AC; text-decoration: none; }}
  .column-tag:hover {{ border-color: var(--accent); color: #fff; }}
  .source-box {{ background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 10px; padding: 18px 20px; margin: 20px 0 28px; font-size: 13px; line-height: 1.8; color: #B8B0AC; }}
  .source-box strong {{ color: #fff; }}
  .tier-data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 16px 0 28px; }}
  .tier-data-table th, .tier-data-table td {{ padding: 8px 6px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.08); }}
  .tier-data-table th {{ color: #fff; font-weight: 700; background: rgba(255,255,255,0.03); }}
  .tier-data-table td:first-child, .tier-data-table th:first-child {{ text-align: left; color: #fff; font-weight: 600; }}
  .tier-data-table .tc-elite {{ color: #c9a6ff; font-weight: 700; }}
  .table-scroll {{ overflow-x: auto; }}
  .column-cta {{ margin-top: 32px; padding: 22px; background: var(--surface, #141414); border-radius: 10px; text-align: center; }}
  @media (max-width: 680px) {{
    .column-wrap {{ padding: 32px 14px 70px; }}
    .column-body {{ font-size: 15.5px; line-height: 1.85; }}
    .column-body h2 {{ font-size: 18px; margin: 30px 0 10px; }}
    .tier-data-table {{ font-size: 12.5px; }}
    .tier-data-table th, .tier-data-table td {{ padding: 7px 5px; }}
    /* 가로로 미는 표에서 나이대 칸은 붙잡아 둔다. 안 그러면 어느 줄인지 잃는다. */
    /* 고정 칸이 좁으면 "3시간 30분" 이 네 줄로 접혀 행이 길어진다. 줄바꿈을 막는다. */
    .tier-data-table td:first-child, .tier-data-table th:first-child {{
      position: sticky; left: 0; background: var(--surface); z-index: 2;
      white-space: nowrap; padding-right: 10px;
      box-shadow: 1px 0 0 var(--border); }}
    .table-scroll {{ margin: 0 -14px; padding: 0 14px; }}
  }}
  .column-cta a {{ display: inline-block; margin-top: 10px; background: var(--accent); color: #fff; font-weight: 700; padding: 12px 26px; border-radius: 6px; text-decoration: none; }}
</style>
</head>
<body>

{site_header("column")}

<main class="column-wrap">
<p class="column-meta">📊 데이터 분석 · 러닝 가이드</p>
<h1 class="column-title">{esc(c['h1'])}</h1>

<div class="column-tags">
{tags}</div>

<div class="column-body">
<p>{esc(c['lead'])}</p>

<a href="level.html" class="cert-cta" style="margin:18px 0 22px;">
<span class="cc-ico">🧮</span>
<span class="cc-txt"><b>표에서 찾기 전에 — 기록을 넣으면 바로 알려드립니다</b><span>완주 시간과 나이만 넣으면 내 등급, 다음 등급까지 남은 시간, 다른 거리 환산 기록까지 나옵니다. 결과는 이미지로 저장해 공유할 수 있습니다. 로그인 없이 바로.</span></span>
<span class="cc-go">계산하기 →</span>
</a>

<div class="source-box">
<strong>📌 이 칼럼의 출처</strong><br>
· <strong>누가</strong>: Running Level(Strength Level 산하 러닝 데이터 분석 플랫폼)<br>
· <strong>언제</strong>: 2024년 집계 데이터<br>
· <strong>어디서</strong>: runninglevel.com 공개 데이터베이스<br>
· <strong>무엇을</strong>: 대규모 실제 {esc(c['label'])} 레이스 완주기록을 나이·성별로 나눈 5단계(비기너~엘리트) 백분위 등급 기준<br>
· <strong>어떻게</strong>: 상위 5%/20%/50%/80%/95% 컷오프 라인을 나이·성별 구간별로 산출<br>
· <strong>왜</strong>: 개인이 절대 기록이 아닌 나이·성별 대비 상대적 위치를 객관적으로 확인할 수 있도록<br><br>
· 보강 자료: Lepers, R., Burfoot, A. &amp; Stapley, P. J. (2021). <em>Sub 3-Hour Marathon Runners for Five Consecutive Decades Demonstrate a Reduced Age-Related Decline in Performance</em>. Frontiers in Physiology, 12:649282. (서브3를 50년간 유지한 러너 40명을 추적한 연구다. 73%가 25~34세에 개인 최고기록을 냈고, 60세 전까지 10년당 7% 미만으로 감소를 묶었다. 대상이 특수하게 잘 훈련된 집단이라 일반 동호인에게 그대로 적용하기는 어렵다)
</div>

<h2>등급은 이렇게 나뉩니다</h2>
<p>Running Level의 5단계 정의는 다음과 같습니다. 각 등급 "시간"은 그 등급에 속하기 위한 최소 기준선(컷오프)입니다.</p>
<div class="table-scroll">
<table class="tier-data-table">
<tr><th>등급</th><th>정의</th></tr>
<tr><td>비기너</td><td>전체 러너 중 상위 95%(하위권) — 러닝을 시작한 지 1개월 이상</td></tr>
<tr><td>노비스</td><td>상위 80% — 6개월 이상 꾸준히 러닝</td></tr>
<tr><td>인터미디엇</td><td>상위 50%(중앙값) — 2년 이상 꾸준히 러닝</td></tr>
<tr><td>어드밴스드</td><td>상위 20% — 5년 이상 러닝</td></tr>
<tr><td class="tc-elite">엘리트</td><td class="tc-elite">상위 5% — 5년 이상 경쟁력 있는 수준을 목표로 훈련</td></tr>
</table>
</div>

<h2>남성 {esc(c['label'])} 기록 등급표 (나이대별)</h2>
{tier_table(dist, "male")}

<h2>여성 {esc(c['label'])} 기록 등급표 (나이대별)</h2>
{tier_table(dist, "female")}
<p style="font-size:13px; color:var(--ink-faint,#8E8E8E);">※ 10대는 아직 성장기라 성인 기준 등급을 그대로 적용하기는 조심스럽습니다. 참고용으로만 봐주세요. 데이터는 5세 단위로 제공되어, 각 나이대의 대표 구간 값을 사용했습니다.</p>
<p style="font-size:13px; color:var(--ink-faint,#8E8E8E);">※ {esc(c['note'])}</p>

<h2>{esc(c['label'])} 평균 기록은 얼마일까 — 나이대별 중앙값</h2>
<p>"평균"을 찾는 분이 많은데, 러닝 기록은 느린 쪽 꼬리가 길어서 산술 평균이 실제 체감과 어긋납니다.
그래서 <strong>중앙값</strong>(딱 절반이 이 안에 들어오는 기록)을 씁니다. 위 표의 인터미디엇 열이
바로 상위 50% 지점이며, 아래는 그 값만 페이스와 함께 뽑은 것입니다.</p>
{median_table(dist)}

<h2>페이스만 알 때 — {esc(c['label'])} 완주 시간 환산</h2>
<p>시계에 찍힌 평균 페이스만 기억난다면, 먼저 완주 시간으로 바꾼 뒤 위 등급표에서 찾으세요.
{esc(c['label'])}는 페이스에 {DIST_KM[dist]:g}을 곱하면 완주 시간이 됩니다.</p>
{pace_table(dist)}

<h2>목표 기록별 구간 통과 시간 — {esc(c['label'])}</h2>
<p>등급을 확인했다면 다음은 "그 기록으로 달리려면 어느 지점을 몇 분에 지나야 하는가"입니다.
아래는 목표 기록을 일정한 페이스로 나눈 통과 시간입니다. 대회 당일 시계와 맞춰 보기 좋게
구간마다 적어 두었습니다.</p>
{split_table(dist)}
<p style="font-size:13px; color:var(--ink-faint);">※ 일정 페이스를 가정한 산술 값입니다.
실제로는 오르막·급수대·초반 혼잡 때문에 구간마다 달라집니다. 특히 초반 5km는 사람에 밀려
계획보다 느려지는 경우가 많으니, 그걸 만회하려고 무리하게 당기지 않는 편이 낫습니다.</p>

<h2>{esc(c['label'])} 기록으로 다른 거리 가늠하기</h2>
<p>"{esc(c['label'])}는 뛰어봤는데 다른 거리는 어느 정도 나올까" — 거리를 바꿔 예측할 때
가장 널리 쓰이는 것이 Riegel 공식입니다. Peter Riegel이
<em>American Scientist</em>(1981, 69권 3호 285-290쪽)에 실은 것으로,
<strong>예상 시간 = 기준 기록 × (거리비)<sup>1.06</sup></strong> 형태입니다.
지수가 1보다 큰 이유는 거리가 늘면 페이스가 떨어지기 때문이고, 단순히 거리를 곱하는 것보다
현실에 가깝습니다.</p>
{riegel_table(dist)}
<p style="font-size:13px; color:var(--ink-faint); line-height:1.8;">
※ 표에서 <strong>*</strong> 가 붙은 값은 Riegel 본인이 밝힌 적용 범위
(<strong>3분 30초~230분</strong>, 즉 3시간 50분)를 넘어선 예측입니다. 그 구간에서는 공식이
실제보다 빠른 값을 내놓는 것으로 알려져 있으니 참고만 하세요.<br>
※ 두 거리를 <strong>비슷한 정도로 훈련했을 때</strong>를 전제합니다. 하프까지만 뛰던 사람이
풀코스를 처음 나가면 예상보다 느린 것이 보통이고, 그건 공식이 틀린 게 아니라 전제가 다른 것입니다.</p>

<h2>내 연령대만 자세히 보기</h2>
<p>위 표는 10년 단위입니다. 한 살 단위로 경계가 어떻게 움직이는지 보려면 아래에서 연령대를 고르세요.
각 페이지에 남녀 기준이 한 살씩 나뉘어 있습니다.</p>
{decade_links(dist)}

<h2>기록은 왜 나이 들수록 떨어질까</h2>
<p>지구력은 나이가 들면서 실제로 떨어집니다. Tanaka와 Seals가 <em>Journal of Physiology</em>
(2008;586(1):55-63)에 정리한 바로는, 지구력 종목의 기량이 대체로 35세 전후까지 유지되다가
그 뒤 완만히, 60세를 넘기면서 뚜렷하게 떨어집니다. 최대산소섭취량과 심박출량이 줄기 때문입니다.</p>
<p>잘 훈련된 러너는 그 기울기를 늦출 수 있습니다. Lepers 등(2021)이 서브3 마라톤을 50년간
유지한 러너 40명을 추적했더니, 73%가 25~34세에 개인 최고기록을 냈고 60세 전까지 감소를
10년당 7% 미만으로 묶었습니다. 다만 이건 아주 특수하게 선별된 집단이라, 일반 동호인의
기울기는 이보다 가파를 수 있습니다.</p>
<p>위 표에서도 20~30대 기록이 거의 같고 40대부터 서서히 벌어지는 모습이 보입니다.
등급표가 나이마다 기준을 달리 두는 이유가 여기 있습니다.</p>

<h2>이 등급은 어떻게 나왔나 — 계산 과정</h2>
<p>러닝 등급표는 많지만, 숫자가 어디서 나왔는지 확인할 수 있는 곳은 드뭅니다. 체감이나
커뮤니티 의견으로 구간을 나누면 보여 줄 계산 과정이 없기 때문입니다. calrank는 두 기준을
나란히 두고 출처와 계산식을 전부 공개합니다.</p>
<p><strong>기준 ① 위 표 — Running Level 5단계.</strong> 해외 공개 데이터베이스의 실제 레이스
기록 백분위입니다. 상위 95%·80%·50%·20%·5% 지점을 그대로 가져왔고 가공하지 않았습니다.</p>
<p><strong>기준 ② calrank 7단계 — WMA 연령 기준표.</strong> 세계마스터즈육상연맹이 2025년에
낸 도로 종목 연령 기준표(퍼블릭 도메인, CC0)를 씁니다. 그 나이·성별의 기준기록을 내 기록으로
나눈 값이 연령등급 %이고, 그 %를 일곱 칸으로 나눈 자리만 calrank가 정했습니다.
계산식과 경계값은 <a href="grade-method.html" style="color:var(--accent-ink);">등급 기준과 근거</a>에
전부 적어 두었습니다.</p>
<p>두 기준은 출처가 달라 같은 기록이라도 결과가 다를 수 있습니다. 둘 다 보시는 편이 정확합니다.</p>

<div style="margin:30px 0 34px;">
<p style="font-size:13.5px; line-height:1.8; color:var(--ink-soft,#9A9A9A); margin:0 0 14px;">
위 표는 <strong style="color:var(--ink,#fff);">Running Level</strong>(해외 공개 데이터) 기준 5단계입니다.
calrank는 나이·성별 보정 방식이 다른 <strong style="color:var(--ink,#fff);">자체 7단계 등급</strong>도 함께 제공합니다 —
같은 기록이라도 두 기준의 결과가 다를 수 있으니, 둘 다 보시는 편이 정확합니다.
</p>

<a href="level.html" class="cert-cta" style="margin-top:0;">
<span class="cc-ico">🧮</span>
<span class="cc-txt"><b>기록을 직접 넣어 계산하기</b><span>WMA 연령 기준표로 5km·하프·풀코스까지 같은 잣대로 비교합니다.</span></span>
<span class="cc-go">계산하기 →</span>
</a>

<a href="cert.html" class="cert-cta">
<span class="cc-ico">📷</span>
<span class="cc-txt"><b>기록증 사진 한 장으로 바로 확인</b><span>완주 시간을 읽어 내 등급과 다음 목표까지 남은 시간을 알려드립니다. 로그인도 타이핑도 필요 없습니다.</span></span>
<span class="cc-go">바로 확인 →</span>
</a>

<a href="grade.html" class="cert-cta">
<span class="cc-ico">📊</span>
<span class="cc-txt"><b>calrank 자체 등급표 — 5km · 10km · 하프 · 풀</b><span>거리별·나이별·성별로 내 기록이 어느 칸인지 표에서 바로 찾을 수 있습니다.</span></span>
<span class="cc-go">등급표 →</span>
</a>
</div>

<h2>{esc(c['why_h2'])}</h2>
{why}

{series_links(dist)}

<div class="column-cta">
<p>기록증 사진 한 장이면 등급이 바로 나옵니다. 가입도, 타이핑도 필요 없습니다.</p>
<a href="cert.html">사진으로 내 등급 확인하기 →</a>
</div>
</div>
</main>

<footer class="site-footer">
<div class="wrap">
<p>칼랭크(CALRANK)는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 이 칼럼의 등급표는 외부 공개 데이터(Running Level, 2024)를 바탕으로 하며, 실제 신체 조건·훈련 상태에 따라 개인차가 있을 수 있습니다.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>

</body>
</html>
"""
    return slug, html, c["h1"], desc


def link_10km_page() -> bool:
    """이미 있는 10km 페이지에 다른 거리로 가는 링크를 끼운다.

    이 페이지는 유입이 가장 많으므로 통째로 다시 만들지 않는다.
    링크 묶음만 넣고, 이미 있으면 최신 내용으로 갈아 끼운다.
    """
    path = ROOT / "column-10km-age-gender-tier.html"
    if not path.exists():
        print("[tier columns] 10km 페이지 없음 — 링크 건너뜀")
        return False
    html = path.read_text(encoding="utf-8")
    block = series_links("10km")
    marker = '<div class="column-cta">'
    existing = re.search(r'<p style="font-size:13\.5px;line-height:1\.9;[^>]*>다른 거리의 등급표.*?</p>\n', html, re.S)
    if existing:
        new = html[:existing.start()] + block + "\n\n" + html[existing.end():]
    elif marker in html:
        new = html.replace(marker, block + "\n\n" + marker, 1)
    else:
        print("[tier columns] 10km 페이지에 넣을 자리를 못 찾음")
        return False
    if new != html:
        path.write_text(new, encoding="utf-8")
        print("[tier columns] 10km 페이지에 거리 링크 반영")
        return True
    return False


def update_column_list(cards) -> int:
    path = ROOT / "column.html"
    if not path.exists():
        return 0
    html = path.read_text(encoding="utf-8")
    marker = '<div style="margin-top:24px;" id="columnCardsContainer">\n\n'
    if marker not in html:
        print("[tier columns] column.html 에 카드 자리를 못 찾음")
        return 0
    added = 0
    for slug, title, desc in cards:
        if f'href="{slug}"' in html:
            continue
        card = (f'<a href="{slug}" class="column-card">\n'
                f'<p class="column-card-meta">📊 데이터 분석 · 러닝 가이드</p>\n'
                f'<p class="column-card-title">{esc(title)}</p>\n'
                f'<p class="column-card-desc">{esc(desc)}</p>\n'
                f'</a>\n\n')
        html = html.replace(marker, marker + card, 1)
        added += 1
    if added:
        path.write_text(html, encoding="utf-8")
    return added


def update_sitemap(slugs) -> int:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return 0
    xml = path.read_text(encoding="utf-8")
    marker = "</urlset>"
    added, count = "", 0
    for slug in slugs:
        loc = f"{SITE}/{slug}"
        if f"<loc>{loc}</loc>" in xml:
            continue
        added += ("  <url>\n"
                  f"    <loc>{loc}</loc>\n"
                  "    <changefreq>monthly</changefreq>\n"
                  "    <priority>0.8</priority>\n"
                  "  </url>\n")
        count += 1
    if added and marker in xml:
        path.write_text(xml.replace(marker, added + marker), encoding="utf-8")
    return count


def main() -> None:
    slugs, cards = [], []
    for dist in ("5km", "half", "full"):
        slug, html, title, desc = build(dist)
        path = ROOT / slug
        if not path.exists() or path.read_text(encoding="utf-8") != html:
            path.write_text(html, encoding="utf-8")
        slugs.append(slug)
        cards.append((slug, title, desc))
        print(f"[tier columns] {slug} ({len(html) // 1024}KB)")
    link_10km_page()
    n_card = update_column_list(cards)
    n_map = update_sitemap(slugs)
    print(f"[tier columns] 칼럼 목록 카드 {n_card}개 · sitemap {n_map}개 추가")


if __name__ == "__main__":
    main()

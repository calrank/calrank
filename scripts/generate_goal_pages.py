"""목표 완주 시간 페이지를 만든다.

"서브4", "하프 2시간", "10km 50분" 은 러너가 실제로 치는 검색어인데
받을 페이지가 없었다. 목표마다 한 장씩 만들어

  · 필요한 페이스(분/km)와 평균 속도
  · 구간 통과 시간표 (풀·하프는 5km마다, 10km·5km는 1km마다)
  · 그 기록이 또래에서 어느 등급인지 (나이대·성별)
  · 같은 체력이라면 다른 거리는 몇 분인지 (WMA 기준표 환산)

를 담는다. 등급 판정은 이미 쓰고 있는 Running Level 공개 데이터를 그대로
쓰므로 거리별 등급표 칼럼과 어긋나지 않는다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_nav import site_header  # noqa: E402
from distance_tier_data import DECADES, TIER_TABLES  # noqa: E402
from goal_data import DISTANCES, GOALS, DIST_INTRO  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://calrank.vercel.app"
TIER_NAMES = ["비기너", "노비스", "인터미디엇", "어드밴스드", "엘리트"]
# 10대는 성장기라 성인 기준을 그대로 대지 않는다.
SHOW_DECADES = list(range(1, 7))          # 20대 ~ 70대

COLUMN_OF = {"5km": "column-5km-age-gender-tier.html",
             "10km": "column-10km-age-gender-tier.html",
             "half": "column-half-age-gender-tier.html",
             "full": "column-full-age-gender-tier.html"}


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def to_sec(t: str) -> int:
    p = [int(x) for x in t.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def clock(sec: float) -> str:
    s = int(round(sec))
    h, m, r = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{r:02d}" if h else f"{m}:{r:02d}"


def pace_str(sec_per_km: float) -> str:
    s = int(round(sec_per_km))
    return f"{s // 60}:{s % 60:02d}"


# 거리 환산도 등급과 같은 WMA 2025 기준표를 쓴다. 전에는 Riegel 경험식이었는데,
# 계산기가 WMA로 넘어가면서 같은 기록에 다른 환산값이 나오게 됐다.
# WMA 비율은 나이에 따라 조금씩 달라지므로, 이 페이지는 나이를 묻지 않는 대신
# 가운데 나이(40세)를 기준으로 삼는다. 하프 기준 나이별 차이는 1분 안쪽이다.
EQUIV_REF_AGE = 40
_EQUIV_KEY = {5.0: "5km", 10.0: "10km", 21.0975: "half", 42.195: "full"}


def _key(km: float) -> str | None:
    for value, key in _EQUIV_KEY.items():
        if abs(km - value) < 0.05:
            return key
    return None


import wma_standards as wma  # noqa: E402


def riegel(t1: float, d1: float, d2: float) -> float:
    """이름은 그대로 두되 속은 WMA 기준표 비율이다. 표 밖 거리는 단순 비례."""
    a, b = _key(d1), _key(d2)
    if not a or not b:
        return t1 * (d2 / d1)
    return t1 * (wma.standard("male", b, EQUIV_REF_AGE)
                 / wma.standard("male", a, EQUIV_REF_AGE))


def tier_for(dist: str, gender: str, dec_i: int, goal: int) -> str:
    """컷오프는 '그 등급에 들기 위한 최소 기준선'이다. 빠른 쪽부터 본다."""
    row = [to_sec(x) for x in TIER_TABLES[(dist, gender)][dec_i]]
    if goal <= row[4]:
        return "엘리트"
    for k in (3, 2, 1, 0):
        if goal <= row[k]:
            return TIER_NAMES[k]
    return "비기너 미만"


def split_marks(dist_km: float, step: float) -> list[float]:
    marks, x = [], step
    while x < dist_km - 0.05:
        marks.append(round(x, 4))
        x += step
    # 하프는 반환점 개념이 없지만 풀코스에는 중간 지점을 넣어 둔다
    if dist_km > 42:
        marks.append(21.0975)
        marks = sorted(set(marks))
    marks.append(dist_km)
    return marks


CSS = """
  .g-wrap{max-width:760px;margin:0 auto;padding:44px 20px 80px;}
  .g-eyebrow{font-size:13px;color:var(--ink-faint,#8E8E8E);margin-bottom:10px;}
  .g-title{font-family:var(--font-display);font-size:clamp(23px,3.6vw,34px);line-height:1.3;margin:0 0 18px;}
  .g-body{font-size:16px;line-height:1.9;color:#E8E4E1;}
  .g-body h2{font-size:20px;margin:36px 0 12px;color:#fff;}
  .g-body p{margin-bottom:16px;}
  .g-key{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0 28px;}
  .g-key div{border:1px solid var(--border,#2A2A2A);border-radius:10px;padding:16px 18px;}
  .g-key span{display:block;font-size:12.5px;color:var(--ink-faint,#8E8E8E);margin-bottom:6px;}
  .g-key b{font-size:26px;font-family:var(--font-display);color:var(--accent,#FF3D1A);}
  .g-key b small{font-size:13px;color:var(--ink-soft,#9A9A9A);font-weight:400;margin-left:3px;}
  .g-table{width:100%;border-collapse:collapse;font-size:13.5px;margin:14px 0 10px;}
  .g-table th,.g-table td{padding:9px 6px;text-align:center;border-bottom:1px solid rgba(255,255,255,.08);}
  .g-table th{color:#fff;font-weight:700;background:rgba(255,255,255,.03);}
  .g-table td:first-child,.g-table th:first-child{text-align:left;color:#fff;font-weight:600;}
  .g-table tr:last-child td{color:var(--accent,#FF3D1A);font-weight:700;}
  .g-scroll{overflow-x:auto;}
  .g-tier td.t-엘리트{color:#c9a6ff;font-weight:700;}
  .g-tier tr:last-child td{color:inherit;font-weight:inherit;}
  .g-note{font-size:13px;color:var(--ink-faint,#8E8E8E);line-height:1.8;}
  .g-others{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0;}
  .g-others a{font-size:13px;padding:7px 14px;border:1px solid var(--border,#2A2A2A);
    border-radius:999px;color:#B8B0AC;text-decoration:none;}
  .g-others a:hover{border-color:var(--accent);color:#fff;}
  .g-others a.cur{background:var(--accent,#FF3D1A);border-color:var(--accent,#FF3D1A);color:#fff;font-weight:700;}
"""


def split_table(dist_km: float, step: float, goal: int) -> str:
    marks = split_marks(dist_km, step)
    rows = []
    for m in marks:
        label = "완주" if abs(m - dist_km) < 0.001 else (
            "하프 지점" if abs(m - 21.0975) < 0.001 and dist_km > 42 else f"{m:g}km")
        rows.append(f"<tr><td>{label}</td><td>{clock(goal * m / dist_km)}</td></tr>")
    return ('<div class="g-scroll">\n<table class="g-table">\n'
            "<tr><th>지점</th><th>통과 시간</th></tr>\n"
            + "\n".join(rows) + "\n</table>\n</div>")


def tier_table(dist: str, goal: int) -> str:
    rows = []
    for i in SHOW_DECADES:
        m = tier_for(dist, "male", i, goal)
        f = tier_for(dist, "female", i, goal)
        rows.append(f'<tr><td>{DECADES[i]}</td>'
                    f'<td class="t-{m}">{m}</td><td class="t-{f}">{f}</td></tr>')
    return ('<div class="g-scroll">\n<table class="g-table g-tier">\n'
            "<tr><th>나이대</th><th>남성</th><th>여성</th></tr>\n"
            + "\n".join(rows) + "\n</table>\n</div>")


def equivalents(dist_km: float, goal: int) -> str:
    rows = []
    for key, (km, _, name) in DISTANCES.items():
        if abs(km - dist_km) < 0.05:
            continue
        rows.append(f"<tr><td>{name}</td><td>{clock(riegel(goal, dist_km, km))}</td></tr>")
    return ('<div class="g-scroll">\n<table class="g-table">\n'
            "<tr><th>거리</th><th>같은 체력이라면</th></tr>\n"
            + "\n".join(rows) + "\n</table>\n</div>")


def tier_sentence(dist: str, goal: int) -> str:
    """표만 두면 읽히지 않는다. 가장 벌어지는 두 칸을 문장으로 짚는다."""
    m20 = tier_for(dist, "male", 1, goal)
    f60 = tier_for(dist, "female", 5, goal)
    if m20 == f60:
        return (f"20대 남성과 60대 여성 모두 \"{m20}\" 구간에 들어갑니다. "
                "같은 기록이라도 또래 안에서 보면 의미가 달라지는데, "
                "이 기록은 두 집단에서 비슷한 위치에 있습니다.")
    return (f"같은 기록이 20대 남성에게는 \"{m20}\", 60대 여성에게는 \"{f60}\"입니다. "
            "절대 시간 하나로 수준을 말할 수 없는 이유가 여기 있습니다.")


def goal_links(cur_slug: str, dist: str) -> str:
    """같은 거리의 다른 목표로 건너갈 수 있게 한다.
    '서브4'를 찾다가 '어렵겠는데' 싶으면 바로 서브4.5를 보게."""
    items = []
    for d, sec_, frag, name, _ in GOALS:
        if d != dist:
            continue
        slug = f"goal-{d}-{frag}.html"
        cls = ' class="cur"' if slug == cur_slug else ""
        items.append(f'<a href="{slug}"{cls}>{name}</a>')
    return '<div class="g-others">\n' + "\n".join(items) + "\n</div>"


def build(dist: str, goal: int, frag: str, name: str, alias: str):
    dist_km, step, dist_name = DISTANCES[dist]
    slug = f"goal-{dist}-{frag}.html"
    pace = pace_str(goal / dist_km)
    speed = f"{dist_km / (goal / 3600):.1f}"
    is_full = dist == "full"

    head = f"{dist_name} {name}" if not is_full else f"마라톤 {name}"
    title = (f"마라톤 {name} 페이스 — {alias} 완주 구간 기록표와 등급 | calrank"
             if is_full else
             f"{dist_name} {alias} 페이스 — 구간 기록표와 또래 등급 | calrank")
    desc = (f"{dist_name} {alias} 완주에 필요한 페이스는 {pace}/km입니다. "
            f"{'5km' if step == 5 else '1km'}마다 몇 분에 지나야 하는지, "
            f"그리고 이 기록이 나이대·성별로 어느 등급인지 함께 정리했습니다.")

    m20 = tier_for(dist, "male", 1, goal)
    f60 = tier_for(dist, "female", 5, goal)

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
<style>{CSS}</style>
</head>
<body>

{site_header("grade")}

<main class="g-wrap">
<p class="g-eyebrow">🎯 목표 기록 · {esc(dist_name)}</p>
<h1 class="g-title">{esc(head)} — 필요 페이스와 구간 기록표</h1>

<div class="g-body">
<p>{esc(dist_name)} {esc(alias)} 완주에 필요한 페이스는 <strong>{pace}/km</strong>입니다.
{esc(DIST_INTRO[dist])}</p>

<div class="g-key">
<div><span>목표 기록</span><b>{clock(goal)}</b></div>
<div><span>필요 페이스</span><b>{pace}<small>/km</small></b></div>
<div><span>평균 속도</span><b>{speed}<small>km/h</small></b></div>
</div>

<a href="level.html" class="cert-cta" style="margin:4px 0 26px;">
<span class="cc-ico">🧮</span>
<span class="cc-txt"><b>지금 내 기록은 어느 등급일까</b><span>완주 시간과 나이를 넣으면 내 등급, 다음 등급까지 남은 시간, 다른 거리 환산 기록이 나옵니다. 로그인 없이 바로.</span></span>
<span class="cc-go">계산하기 →</span>
</a>

<h2>구간 통과 시간표</h2>
<p>아래 시간에 맞춰 지나가면 {esc(alias)}에 완주합니다. 일정한 페이스를 가정한 값입니다.</p>
{split_table(dist_km, step, goal)}
<p class="g-note">※ 실제 레이스에서는 오르막·급수대·혼잡 구간 때문에 구간마다 편차가 생깁니다.
초반 구간을 표보다 빠르게 통과하고 있다면 속도를 줄이는 편이 안전합니다.</p>

<h2>{esc(alias)}는 또래에서 어느 수준일까</h2>
<p>{esc(tier_sentence(dist, goal))}</p>
{tier_table(dist, goal)}
<p class="g-note">Running Level(runninglevel.com) 공개 데이터의 5단계 기준입니다.
비기너는 상위 95%, 노비스 80%, 인터미디엇 50%, 어드밴스드 20%, 엘리트 5% 컷오프를 뜻합니다.
10대는 성장기라 성인 기준을 그대로 적용하기 어려워 뺐습니다.
거리별 전체 표는 <a href="{COLUMN_OF[dist]}" style="color:var(--accent,#FF3D1A);">{esc(dist_name)} 나이대별 등급표</a>에서 볼 수 있습니다.</p>

<h2>같은 체력이라면 다른 거리는</h2>
<p>WMA 연령 기준표의 거리별 비율로 바꾼 값입니다. {esc(alias)}로 {esc(dist_name)}를 뛸 수 있다면
다른 거리는 대략 이 정도가 나옵니다.</p>
{equivalents(dist_km, goal)}
<p class="g-note">※ 환산식은 훈련 경향을 반영하지 못합니다. 장거리 훈련을 많이 했다면
긴 거리가 환산값보다 빠르고, 스피드 훈련 위주라면 짧은 거리가 더 빠릅니다.</p>

<h2>{esc(dist_name)}의 다른 목표</h2>
{goal_links(slug, dist)}

<div style="margin:34px 0 0;">
<a href="cert.html" class="cert-cta">
<span class="cc-ico">📷</span>
<span class="cc-txt"><b>기록증 사진 한 장으로 내 위치 확인</b><span>완주 시간을 읽어 내 등급과 다음 목표까지 남은 시간을 알려드립니다. 로그인도 타이핑도 필요 없습니다.</span></span>
<span class="cc-go">바로 확인 →</span>
</a>
<a href="grade.html" class="cert-cta">
<span class="cc-ico">📊</span>
<span class="cc-txt"><b>거리별·나이별 등급표 전체</b><span>5km · 10km · 하프 · 풀코스를 나이와 성별로 나눈 표에서 내 칸을 바로 찾을 수 있습니다.</span></span>
<span class="cc-go">등급표 →</span>
</a>
</div>
</div>
</main>

<footer class="site-footer">
<div class="wrap">
<p>페이스와 구간 시간은 일정한 속도를 가정해 계산한 값입니다. 등급 기준은 외부 공개 데이터(Running Level, 2024)를 바탕으로 하며, 실제 신체 조건·훈련 상태에 따라 개인차가 있을 수 있습니다.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>

</body>
</html>
"""
    return slug, html, title, desc, pace, m20, f60


def build_hub(rows) -> tuple[str, str]:
    """거리별로 묶은 목표 목록. 각 줄에 필요 페이스를 적어 목차 자체가 쓸모 있게."""
    blocks = []
    for key in ("full", "half", "10km", "5km"):
        _, _, dist_name = DISTANCES[key]
        items = []
        for slug, name, alias, pace, m20, f60 in rows:
            if not slug.startswith(f"goal-{key}-"):
                continue
            items.append(
                f'<tr><td><a href="{slug}" style="color:inherit;text-decoration:none;">'
                f"<b>{esc(name)}</b></a></td>"
                f"<td>{pace}/km</td><td>{esc(m20)}</td><td>{esc(f60)}</td></tr>")
        blocks.append(
            f"<h2>{esc(dist_name)}</h2>\n"
            '<div class="g-scroll">\n<table class="g-table g-tier">\n'
            "<tr><th>목표</th><th>필요 페이스</th><th>20대 남성</th><th>60대 여성</th></tr>\n"
            + "\n".join(items) + "\n</table>\n</div>")
    body = "\n".join(blocks)
    desc = ("서브3·서브4부터 하프 2시간, 10km 50분까지 목표 기록별로 필요한 페이스와 "
            "구간 통과 시간을 정리했습니다. 같은 기록이 나이대·성별로 어느 등급인지도 "
            "함께 볼 수 있습니다.")
    title = "러닝 목표 기록별 페이스표 — 서브3·서브4·하프 2시간·10km 50분 | calrank"
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:url" content="{SITE}/goals.html">
<meta property="og:locale" content="ko_KR">
<link rel="canonical" href="{SITE}/goals.html">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="style.css">
<style>{CSS}</style>
</head>
<body>

{site_header("grade")}

<main class="g-wrap">
<p class="g-eyebrow">🎯 목표 기록</p>
<h1 class="g-title">목표 기록별 페이스표</h1>

<div class="g-body">
<p>{esc(desc)} 목표를 누르면 구간마다 몇 분에 지나야 하는지 볼 수 있습니다.</p>
<p class="g-note">표의 '20대 남성'·'60대 여성' 칸은 그 목표 기록이 각 집단에서 어느 등급에
해당하는지 보여줍니다. 같은 기록이라도 또래에 따라 의미가 크게 달라집니다.</p>

{body}

<div style="margin:34px 0 0;">
<a href="level.html" class="cert-cta">
<span class="cc-ico">🧮</span>
<span class="cc-txt"><b>내 기록은 지금 어디쯤일까</b><span>완주 시간과 나이를 넣으면 등급과 다음 목표까지 남은 시간이 나옵니다.</span></span>
<span class="cc-go">계산하기 →</span>
</a>
<a href="grade.html" class="cert-cta">
<span class="cc-ico">📊</span>
<span class="cc-txt"><b>거리별·나이별 등급표 전체</b><span>5km · 10km · 하프 · 풀코스를 나이와 성별로 나눈 표.</span></span>
<span class="cc-go">등급표 →</span>
</a>
</div>
</div>
</main>

<footer class="site-footer">
<div class="wrap">
<p>페이스와 구간 시간은 일정한 속도를 가정해 계산한 값입니다. 등급 기준은 외부 공개 데이터(Running Level, 2024)를 바탕으로 합니다.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>

</body>
</html>
"""
    return html, desc


def update_sitemap(slugs) -> int:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return 0
    xml = path.read_text(encoding="utf-8")
    marker, added, count = "</urlset>", "", 0
    for slug in slugs:
        loc = f"{SITE}/{slug}"
        if f"<loc>{loc}</loc>" in xml:
            continue
        added += ("  <url>\n"
                  f"    <loc>{loc}</loc>\n"
                  "    <changefreq>monthly</changefreq>\n"
                  "    <priority>0.7</priority>\n"
                  "  </url>\n")
        count += 1
    if added and marker in xml:
        path.write_text(xml.replace(marker, added + marker), encoding="utf-8")
    return count


def link_from_grade() -> bool:
    """등급표 허브에서 목표 페이지로 가는 길을 낸다."""
    path = ROOT / "grade.html"
    if not path.exists():
        return False
    html = path.read_text(encoding="utf-8")
    if 'href="goals.html"' in html:
        return False
    block = ('<a href="goals.html" class="cert-cta">\n'
             '<span class="cc-ico">🎯</span>\n'
             '<span class="cc-txt"><b>목표 기록별 페이스표 — 서브4 · 하프 2시간 · 10km 50분</b>'
             '<span>목표마다 필요한 페이스와 구간 통과 시간, 그리고 그 기록이 또래에서 '
             '어느 등급인지 정리했습니다.</span></span>\n'
             '<span class="cc-go">보러 가기 →</span>\n'
             "</a>\n")
    marker = "</main>"
    if marker not in html:
        return False
    path.write_text(html.replace(marker, block + marker, 1), encoding="utf-8")
    return True


def main() -> None:
    rows, slugs = [], []
    for dist, goal, frag, name, alias in GOALS:
        slug, html, title, desc, pace, m20, f60 = build(dist, goal, frag, name, alias)
        p = ROOT / slug
        if not p.exists() or p.read_text(encoding="utf-8") != html:
            p.write_text(html, encoding="utf-8")
        rows.append((slug, name, alias, pace, m20, f60))
        slugs.append(slug)
    hub, _ = build_hub(rows)
    hp = ROOT / "goals.html"
    if not hp.exists() or hp.read_text(encoding="utf-8") != hub:
        hp.write_text(hub, encoding="utf-8")
    slugs.append("goals.html")
    linked = link_from_grade()
    n = update_sitemap(slugs)
    print(f"[goal pages] 목표 {len(rows)}개 + 허브 1개 · sitemap {n}개 추가 "
          f"· 등급표 연결 {'O' if linked else '-'}")


if __name__ == "__main__":
    main()

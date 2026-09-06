"""
calrank 거리별 랜딩페이지 자동 생성 스크립트

"10km 마라톤 대회", "하프마라톤 대회 일정" 같은 검색은 러너들이 실제로
자주 쓰는 검색어다. events.json의 실제 distances 필드를 정규화해서
종목 x 거리 조합별로 데이터가 충분한(3개 이상) 것만 정적 페이지로 만든다.
지역별 랜딩페이지(generate_landing_pages.py)와 같은 패턴이며, evergreen
허브 페이지라 실행할 때마다 최신 데이터로 전체 재생성한다.

사용 예시:
  python scripts/generate_distance_landing_pages.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SPORT_LABEL = {
    "marathon": "마라톤", "cycling": "자전거", "trail": "트레일러닝",
    "triathlon": "철인3종", "inline": "인라인",
}
MIN_EVENTS = 5


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    p = ROOT / path
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# 다양하게 표기된 거리 문자열을 검색어와 일치하는 대표 카테고리로 정규화한다.
def normalize_distance(raw):
    s = raw.strip()
    if s in ("풀", "풀코스") or "42.1" in s or "42km" in s:
        return "풀코스"
    if s == "하프" or "21.1" in s or s == "21km":
        return "하프"
    if s == "5km":
        return "5km"
    if s == "10km":
        return "10km"
    if s == "100km" or "울트라" in s:
        return "울트라"
    return None


DIST_SLUG = {"5km": "5km", "10km": "10km", "하프": "half", "풀코스": "full", "울트라": "ultra"}


def slugify(sport, dist_label):
    d = DIST_SLUG.get(dist_label, dist_label)
    return f"landing-dist-{sport}-{d}.html"


def build_page(sport, dist_label, events):
    sport_label = SPORT_LABEL[sport]
    events_sorted = sorted(events, key=lambda e: e.get("date") or "9999")
    total = len(events_sorted)
    title = f"{dist_label} {sport_label} 대회 일정 — {total}개 총정리"
    desc = f"calrank에 등록된 {dist_label} {sport_label} 대회 {total}개를 날짜순으로 정리했습니다."

    rows = "\n".join(
        f'<a href="event.html?id={e.get("id","")}" class="landing-row">'
        f'<span class="landing-date">{(e.get("date") or "")[:10]}</span>'
        f'<span class="landing-name">{e.get("name","")}</span>'
        f'<span class="landing-region">{e.get("region") or ""}</span>'
        f'</a>'
        for e in events_sorted[:60]
    )
    slug = slugify(sport, dist_label)

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — calrank</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://calrank.vercel.app/og-image.png">
<meta property="og:url" content="https://calrank.vercel.app/{slug}">
<meta property="og:locale" content="ko_KR">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="style.css">
<style>
  .landing-wrap {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
  .landing-title {{ font-family: var(--font-display); font-size: clamp(24px, 3.6vw, 34px); line-height: 1.3; margin-bottom: 12px; }}
  .landing-sub {{ font-size: 15px; color: #B8B0AC; margin-bottom: 24px; }}
  .landing-list {{ display: flex; flex-direction: column; gap: 2px; margin-top: 24px; }}
  .landing-row {{ display: flex; gap: 14px; padding: 12px 14px; background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 6px; text-decoration: none; color: #E8E4E1; font-size: 14px; align-items: center; }}
  .landing-row:hover {{ border-color: var(--accent); }}
  .landing-date {{ color: var(--accent); font-weight: 700; flex-shrink: 0; width: 80px; }}
  .landing-name {{ flex: 1; }}
  .landing-region {{ color: var(--ink-faint, #6A6A6A); font-size: 12px; flex-shrink: 0; }}
  .landing-cta {{ margin-top: 32px; padding: 20px; background: var(--surface, #141414); border-radius: 10px; text-align: center; }}
  .landing-cta a {{ display: inline-block; margin-top: 10px; background: var(--accent); color: #fff; font-weight: 700; padding: 12px 24px; border-radius: 6px; text-decoration: none; }}
</style>
</head>
<body>
<header class="site-header">
<div class="wrap header-inner">
<a href="index.html" class="wordmark">CALRANK</a>
<nav class="main-nav">
<a href="index.html" class="nav-link">캘린더</a>
<a href="regions.html" class="nav-link">지역별</a>
<a href="news.html" class="nav-link">종목뉴스</a>
<a href="column.html" class="nav-link">칼럼</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>
<main class="landing-wrap">
<h1 class="landing-title">{title}</h1>
<p class="landing-sub">{desc}</p>
<div class="landing-list">
{rows}
</div>
<div class="landing-cta">
<p>다른 거리·지역 조건으로도 찾아보고 싶다면?</p>
<a href="index.html?sport={sport}">캘린더에서 필터링해서 보기 →</a>
</div>
<p style="margin-top:16px;"><a href="distances.html" style="color:var(--ink-soft); font-size:13px;">← 거리별 대회 전체 보기</a> · <a href="regions.html" style="color:var(--ink-soft); font-size:13px;">지역별로 보기 →</a></p>
</main>
<footer class="site-footer">
<div class="wrap">
<p>calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해주세요.</p>
</div>
</footer>
</body>
</html>
'''


def update_sitemap(slugs):
    path = ROOT / "sitemap.xml"
    xml = path.read_text(encoding="utf-8")
    marker = "</urlset>"
    added = ""
    for slug in slugs:
        entry = (
            f"  <url>\n"
            f"    <loc>https://calrank.vercel.app/{slug}</loc>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.6</priority>\n"
            f"  </url>\n"
        )
        if entry not in xml:
            added += entry
    if added and marker in xml:
        xml = xml.replace(marker, added + marker)
        path.write_text(xml, encoding="utf-8")


def build_index(pages):
    # 종목별로 묶어서 허브 페이지를 구성하고, regions.html과 서로 오가도록 연결한다.
    by_sport = {}
    for sport, dist_label, slug, total in pages:
        by_sport.setdefault(sport, []).append((dist_label, slug, total))

    sections = []
    for sport in sorted(by_sport.keys()):
        items = "\n".join(
            f'<a href="{slug}" class="landing-index-item">{SPORT_LABEL[sport]} {dist_label} <span>{total}개</span></a>'
            for dist_label, slug, total in sorted(by_sport[sport], key=lambda x: -x[2])
        )
        sections.append(f'<h2>{SPORT_LABEL[sport]}</h2>\n<div class="landing-index-grid">{items}</div>')

    body = "\n".join(sections)

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>거리별 대회 일정 — calrank</title>
<meta name="description" content="5km, 10km, 하프, 풀코스, 울트라 등 거리별 동호인 스포츠 대회 일정을 한눈에 확인하세요.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="style.css">
<style>
  .landing-wrap {{ max-width: 900px; margin: 0 auto; padding: 48px 20px 80px; }}
  .landing-wrap h2 {{ margin-top: 32px; font-size: 18px; }}
  .landing-index-grid {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
  .landing-index-item {{ font-size: 13px; padding: 8px 14px; border: 1px solid var(--border, #2A2A2A); border-radius: 999px; color: #E8E4E1; text-decoration: none; }}
  .landing-index-item span {{ color: var(--accent); margin-left: 4px; }}
  .landing-index-item:hover {{ border-color: var(--accent); }}
  .cross-link {{ display: inline-block; margin-top: 16px; font-size: 13px; color: var(--ink-soft); text-decoration: none; border-bottom: 1px dashed var(--ink-faint); }}
</style>
</head>
<body>
<header class="site-header">
<div class="wrap header-inner">
<a href="index.html" class="wordmark">CALRANK</a>
<nav class="main-nav">
<a href="index.html" class="nav-link">캘린더</a>
<a href="regions.html" class="nav-link">지역별</a>
<a href="news.html" class="nav-link">종목뉴스</a>
<a href="column.html" class="nav-link">칼럼</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>
<main class="landing-wrap">
<h1>거리별 대회 일정</h1>
<p>원하는 거리를 선택해서 해당 대회 목록을 바로 확인하세요.</p>
<a href="regions.html" class="cross-link">지역별로 찾아보기 →</a>
{body}
</main>
<footer class="site-footer">
<div class="wrap">
<p>calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다.</p>
</div>
</footer>
</body>
</html>
'''


def main():
    events = load_json("events.json", [])

    combos = {}
    for e in events:
        sport = e.get("sport")
        if sport not in SPORT_LABEL:
            continue
        seen_for_event = set()
        for raw in (e.get("distances") or []):
            norm = normalize_distance(raw)
            if not norm or norm in seen_for_event:
                continue
            seen_for_event.add(norm)
            combos.setdefault((sport, norm), []).append(e)

    slugs = []
    pages = []
    count = 0
    for (sport, dist_label), evs in combos.items():
        if len(evs) < MIN_EVENTS:
            continue
        html = build_page(sport, dist_label, evs)
        slug = slugify(sport, dist_label)
        (ROOT / slug).write_text(html, encoding="utf-8")
        slugs.append(slug)
        pages.append((sport, dist_label, slug, len(evs)))
        count += 1

    index_html = build_index(pages)
    (ROOT / "distances.html").write_text(index_html, encoding="utf-8")
    slugs.append("distances.html")

    update_sitemap(slugs)
    print(f"Generated {count} distance landing pages + distances.html index.")


if __name__ == "__main__":
    main()

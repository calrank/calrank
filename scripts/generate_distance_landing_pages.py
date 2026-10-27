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
from datetime import date
from pathlib import Path
from urllib.parse import quote

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


def build_dist_stats(dist_label, sport_label, evs, upcoming):
    """그 거리 대회가 언제·어디서 열리는지. events.json 값만 쓴다."""
    import collections as _c
    if len(evs) < 4:
        return ""
    months = _c.Counter(int((e.get("date") or "0000-00")[5:7]) for e in evs
                        if (e.get("date") or "")[5:7].isdigit())
    months.pop(0, None)
    regions = _c.Counter(e.get("region") for e in evs if e.get("region"))
    out = [f'<h2 class="landing-h2">{dist_label} {sport_label} 대회, 이런 모습입니다</h2>',
           '<ul class="landing-facts">']
    if months:
        txt = " · ".join(f"{m}월 {n}개" for m, n in months.most_common(3))
        out.append(f'<li>가장 많이 열리는 달은 {txt} 입니다. 올해 {len(evs)}개 기준입니다.</li>')
    if regions:
        txt = " · ".join(f"{r} {n}개" for r, n in regions.most_common(4))
        out.append(f'<li>지역으로는 {txt} 순으로 많습니다.</li>')
    if upcoming:
        out.append(f'<li>다음 대회는 {(upcoming[0].get("date") or "")[:10]} '
                   f'{upcoming[0].get("name","")} 입니다.</li>')
    out.append('</ul>')
    out.append(f'<p class="landing-note">저희가 모은 {dist_label} {sport_label} 대회 '
               f'{len(evs)}개를 센 숫자입니다. 공개되지 않은 대회는 빠져 있을 수 있습니다.</p>')
    return "\n".join(out)


def build_page(sport, dist_label, events):
    sport_label = SPORT_LABEL[sport]
    events_sorted = sorted(events, key=lambda e: e.get("date") or "9999")
    total = len(events_sorted)
    title = f"{dist_label} {sport_label} 대회 일정 — {total}개 총정리"
    desc = f"calrank에 등록된 {dist_label} {sport_label} 대회 {total}개를 날짜순으로 정리했습니다."

    today_iso = date.today().isoformat()

    def _rows(items):
        return "\n".join(
            f'<a href="e/{quote(e.get("id",""))}.html" class="landing-row">'
            f'<span class="landing-date">{(e.get("date") or "")[:10]}</span>'
            f'<span class="landing-name">{e.get("name","")}</span>'
            f'<span class="landing-region">{e.get("region") or ""}</span>'
            f'</a>'
            for e in items
        )

    upcoming = [e for e in events_sorted if (e.get("date") or "") >= today_iso]
    done = [e for e in events_sorted if (e.get("date") or "") < today_iso]

    rows = ""
    if upcoming:
        rows += (f'<h2 class="landing-h2">다가오는 {dist_label} {sport_label} 대회 '
                 f'{len(upcoming)}개</h2>\n<div class="landing-list">\n'
                 + _rows(upcoming[:60]) + "\n</div>")
    if done:
        rows += (f'\n<h2 class="landing-h2">올해 치러진 {dist_label} {sport_label} 대회 '
                 f'{len(done)}개</h2>\n'
                 f'<p class="landing-note">이미 끝난 대회입니다. 다음 회차 시기를 가늠할 때 '
                 f'참고하세요.</p>\n<div class="landing-list">\n'
                 + _rows(list(reversed(done))[:60]) + "\n</div>")
    rows += build_dist_stats(dist_label, sport_label, events_sorted, upcoming)
    slug = slugify(sport, dist_label)
    canonical_url = f"https://calrank.vercel.app/{slug}"
    collection_ld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": title, "description": desc, "url": canonical_url,
    }, ensure_ascii=False)
    breadcrumb_ld = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": "https://calrank.vercel.app/index.html"},
            {"@type": "ListItem", "position": 2, "name": "거리별", "item": "https://calrank.vercel.app/distances.html"},
            {"@type": "ListItem", "position": 3, "name": title},
        ],
    }, ensure_ascii=False)

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
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0B0B0B">
<link rel="canonical" href="{canonical_url}">
<link rel="stylesheet" href="style.css">
<script type="application/ld+json">{collection_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
<style>
  .landing-wrap {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
  .landing-title {{ font-family: var(--font-display); font-size: clamp(24px, 3.6vw, 34px); line-height: 1.3; margin-bottom: 12px; }}
  .landing-sub {{ font-size: 15px; color: #B8B0AC; margin-bottom: 24px; }}
  .landing-list {{ display: flex; flex-direction: column; gap: 2px; margin-top: 24px; }}
  .landing-row {{ display: flex; gap: 14px; padding: 12px 14px; background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 6px; text-decoration: none; color: #E8E4E1; font-size: 14px; align-items: center; }}
  .landing-row:hover {{ border-color: var(--accent); }}
  .landing-date {{ color: var(--accent); font-weight: 700; flex-shrink: 0; width: 80px; }}
  .landing-name {{ flex: 1; }}
  .landing-region {{ color: var(--ink-faint, #8E8E8E); font-size: 12px; flex-shrink: 0; }}
  .landing-h2 {{ font-size: 17px; margin: 34px 0 10px; }}
  .landing-note {{ font-size: 12.5px; line-height: 1.75; color: var(--ink-faint); margin: 0 0 12px; }}
  .landing-facts {{ margin: 0 0 6px; padding-left: 18px; }}
  .landing-facts li {{ font-size: 13.5px; line-height: 1.9; color: var(--ink-soft); }}
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
{rows}
<div class="landing-cta">
<p>다른 거리·지역 조건으로도 찾아보고 싶다면?</p>
<a href="index.html?sport={sport}">캘린더에서 필터링해서 보기 →</a>
</div>
<p style="margin-top:16px;"><a href="distances.html" style="color:var(--ink-soft); font-size:13px;">← 거리별 대회 전체 보기</a> · <a href="regions.html" style="color:var(--ink-soft); font-size:13px;">지역별로 보기 →</a></p>
</main>
<footer class="site-footer">
<div class="wrap">
<p>칼랭크(CALRANK)는 달린 기록이 어느 등급인지 읽어 주고, 다음 출발선을 찾아 주는 곳입니다. 대회 일정은 주최측이 공개한 내용을 정리한 것입니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해주세요.</p>
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
    index_ld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "거리별 대회 일정", "url": "https://calrank.vercel.app/distances.html",
    }, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>거리별 대회 일정 — calrank</title>
<meta name="description" content="5km, 10km, 하프, 풀코스, 울트라 등 거리별 동호인 스포츠 대회 일정을 한눈에 확인하세요.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0B0B0B">
<link rel="canonical" href="https://calrank.vercel.app/distances.html">
<link rel="stylesheet" href="style.css">
<script type="application/ld+json">{index_ld}</script>
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
<p>칼랭크(CALRANK)는 달린 기록이 어느 등급인지 읽어 주고, 다음 출발선을 찾아 주는 곳입니다. 대회 일정은 주최측이 공개한 내용을 정리한 것입니다.</p>
</div>
</footer>
</body>
</html>
'''


def main():
    events = load_json("events.json", [])
    today_iso = date.today().isoformat()

    combos = {}
    for e in events:
        sport = e.get("sport")
        if sport not in SPORT_LABEL:
            continue
        # 지난 대회도 싣는다. 상세페이지가 지워진다는 전제가 지금은 안 맞는다
        # (592개 전부 남아 있다). 예정만 싣던 탓에 거리 랜딩 5장이 600자 아래였다.
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

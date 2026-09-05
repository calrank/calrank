"""
calrank 종목+지역 랜딩페이지 자동 생성 스크립트

events.json에서 "지역 x 종목" 조합별 실제 대회 수를 계산해, 데이터가
충분한(3개 이상) 조합마다 정적 랜딩페이지를 만든다. 실제 대회명·날짜를
그대로 나열하는 방식이라 할루시네이션 위험이 없고, "서울 마라톤 대회"
같은 실제 검색어에 대응하는 SEO 페이지 역할을 한다.

컬럼(시계열 발행물)과 달리 이 페이지들은 상시 갱신되는 허브 페이지라서,
실행할 때마다 조건을 만족하는 모든 조합을 다시 계산해 덮어쓴다.

사용 예시:
  python scripts/generate_landing_pages.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SPORT_LABEL = {
    "marathon": "마라톤", "cycling": "자전거", "trail": "트레일러닝",
    "triathlon": "철인3종", "inline": "인라인",
}
REGION_SLUG = {
    "서울": "seoul", "경기": "gyeonggi", "인천": "incheon", "부산": "busan",
    "대구": "daegu", "광주": "gwangju", "대전": "daejeon", "울산": "ulsan",
    "세종": "sejong", "강원": "gangwon", "충북": "chungbuk", "충남": "chungnam",
    "전북": "jeonbuk", "전남": "jeonnam", "경북": "gyeongbuk", "경남": "gyeongnam",
    "제주": "jeju",
}
MIN_EVENTS = 3
EXCLUDE_REGIONS = {"전국", "미표기", "온라인", None, ""}


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    p = ROOT / path
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(region, sport):
    r = REGION_SLUG.get(region, region)
    return f"landing-{r}-{sport}.html"


def build_page(region, sport, events):
    sport_label = SPORT_LABEL[sport]
    events_sorted = sorted(events, key=lambda e: e.get("date") or "9999")
    total = len(events_sorted)
    title = f"{region} {sport_label} 대회 일정 — {total}개 대회 총정리"
    desc = f"calrank에 등록된 {region} 지역 {sport_label} 대회 {total}개를 날짜순으로 정리했습니다."

    rows = "\n".join(
        f'<a href="event.html?id={e.get("id","")}" class="landing-row">'
        f'<span class="landing-date">{(e.get("date") or "")[:10]}</span>'
        f'<span class="landing-name">{e.get("name","")}</span>'
        f'</a>'
        for e in events_sorted[:40]
    )
    slug = slugify(region, sport)

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
  .landing-wrap {{ max-width: 720px; margin: 0 auto; padding: 48px 20px 80px; }}
  .landing-title {{ font-family: var(--font-display); font-size: clamp(24px, 3.6vw, 34px); line-height: 1.3; margin-bottom: 12px; }}
  .landing-sub {{ font-size: 15px; color: #B8B0AC; margin-bottom: 24px; }}
  .landing-list {{ display: flex; flex-direction: column; gap: 2px; margin-top: 24px; }}
  .landing-row {{ display: flex; gap: 16px; padding: 12px 14px; background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 6px; text-decoration: none; color: #E8E4E1; font-size: 14px; }}
  .landing-row:hover {{ border-color: var(--accent); }}
  .landing-date {{ color: var(--accent); font-weight: 700; flex-shrink: 0; width: 82px; }}
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
<a href="ranking.html" class="nav-link">대회랭킹</a>
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
<p>지도로 보거나 다른 조건으로 더 찾아보고 싶다면?</p>
<a href="index.html?region={region}&sport={sport}">캘린더에서 필터링해서 보기 →</a>
</div>
</main>
<footer class="site-footer">
<div class="wrap">
<p>calrank는 대회 주최측이 공개한 일정 정보를 정리해 제공합니다. 접수 조건 등 정확한 내용은 신청 페이지에서 다시 확인해주세요.</p>
<p class="footer-links"><a href="terms.html">이용약관</a> · <a href="privacy.html">개인정보처리방침</a> · <a href="contact.html">제휴·광고 문의</a></p>
</div>
</footer>
</body>
</html>
''', title, desc, slug


def build_index(pages):
    # 지역별로 묶어서 목록 페이지 구성
    by_region = {}
    for region, sport, slug, total in pages:
        by_region.setdefault(region, []).append((sport, slug, total))

    sections = []
    for region in sorted(by_region.keys()):
        items = "\n".join(
            f'<a href="{slug}" class="landing-index-item">{region} {SPORT_LABEL[sport]} <span>{total}개</span></a>'
            for sport, slug, total in sorted(by_region[region], key=lambda x: -x[2])
        )
        sections.append(f'<h2>{region}</h2>\n<div class="landing-index-grid">{items}</div>')

    body = "\n".join(sections)

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>지역별 대회 일정 — calrank</title>
<meta name="description" content="전국 지역별·종목별 동호인 스포츠 대회 일정을 한눈에 확인하세요.">
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
</style>
</head>
<body>
<header class="site-header">
<div class="wrap header-inner">
<a href="index.html" class="wordmark">CALRANK</a>
<nav class="main-nav">
<a href="index.html" class="nav-link">캘린더</a>
<a href="ranking.html" class="nav-link">대회랭킹</a>
<a href="news.html" class="nav-link">종목뉴스</a>
<a href="column.html" class="nav-link">칼럼</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>
<main class="landing-wrap">
<h1>지역별 대회 일정</h1>
<p>지역과 종목을 선택해서 해당 대회 목록을 바로 확인하세요.</p>
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


def main():
    events = load_json("events.json", [])

    combos = {}
    for e in events:
        region, sport = e.get("region"), e.get("sport")
        if not sport or region in EXCLUDE_REGIONS or sport not in SPORT_LABEL:
            continue
        combos.setdefault((region, sport), []).append(e)

    pages = []
    slugs = []
    for (region, sport), evs in combos.items():
        if len(evs) < MIN_EVENTS:
            continue
        html, title, desc, slug = build_page(region, sport, evs)
        (ROOT / slug).write_text(html, encoding="utf-8")
        pages.append((region, sport, slug, len(evs)))
        slugs.append(slug)

    index_html = build_index(pages)
    (ROOT / "regions.html").write_text(index_html, encoding="utf-8")
    slugs.append("regions.html")

    update_sitemap(slugs)
    print(f"Generated {len(pages)} landing pages + regions.html index.")


if __name__ == "__main__":
    main()

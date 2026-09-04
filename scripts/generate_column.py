"""
calrank 칼럼 자동 생성 스크립트 (순수 통계 기반, AI 미사용)

events.json에서 실제 대회 통계를 계산한 뒤, 여러 문장 템플릿 중 하나를
무작위로 골라 숫자를 끼워 넣습니다. 새로운 사실을 지어내지 않으므로
할루시네이션 위험이 없습니다.

사용 예시:
  python scripts/generate_column.py
"""
import json
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))

SPORT_LABEL = {
    "marathon": "마라톤",
    "cycling": "자전거",
    "trail": "트레일러닝",
    "triathlon": "철인3종",
    "inline": "인라인",
}
SPORT_ROTATION = ["marathon", "cycling", "trail", "triathlon", "inline"]
MIN_EVENTS_FOR_TOPIC = 3


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    p = ROOT / path
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(sport, month_label):
    return f"column-{month_label}-{sport}-auto.html"


def compute_stats(events, sport, month_label):
    subset = [e for e in events if e.get("sport") == sport and (e.get("date") or "").startswith(month_label)]
    if len(subset) < MIN_EVENTS_FOR_TOPIC:
        return None

    by_region = {}
    for e in subset:
        r = e.get("region") or "미표기"
        by_region[r] = by_region.get(r, 0) + 1
    top_regions = sorted(by_region.items(), key=lambda x: -x[1])[:5]

    by_distance = {}
    for e in subset:
        for d in (e.get("distances") or []):
            by_distance[d] = by_distance.get(d, 0) + 1
    top_distances = sorted(by_distance.items(), key=lambda x: -x[1])[:6]

    sample_names = [e.get("name") for e in subset[:6] if e.get("name")]

    y, m = month_label.split("-")
    month_kr = f"{y}년 {int(m)}월"

    return {
        "sport": sport,
        "sport_label": SPORT_LABEL[sport],
        "month_label": month_label,
        "month_kr": month_kr,
        "total": len(subset),
        "top_regions": top_regions,
        "top_distances": top_distances,
        "sample_names": sample_names,
    }


def pick_topic(events, state):
    idx = state.get("last_sport_index", -1)
    now_kst = datetime.now(KST)
    month_label = now_kst.strftime("%Y-%m")
    published = set(state.get("published", []))

    for attempt in range(len(SPORT_ROTATION)):
        idx = (idx + 1) % len(SPORT_ROTATION)
        sport = SPORT_ROTATION[idx]
        topic_key = f"{sport}-{month_label}"
        if topic_key in published:
            continue
        stats = compute_stats(events, sport, month_label)
        if stats is None:
            continue
        return idx, sport, month_label, topic_key, stats

    return None, None, None, None, None


def build_content(stats, rng):
    s = stats
    region_lines = ", ".join(f"{r}({c}개)" for r, c in s["top_regions"][:4])
    distance_lines = ", ".join(f"{d}({c}개)" for d, c in s["top_distances"][:5])
    sample_lines = ", ".join(s["sample_names"][:5])
    top_region_name, top_region_count = s["top_regions"][0]

    title_options = [
        f'{s["month_kr"]}, 전국 {s["sport_label"]} 대회 {s["total"]}개 — 지역별 완전정리',
        f'{s["month_kr"]} {s["sport_label"]} 대회 총정리 — {s["total"]}개 대회 한눈에',
        f'{s["month_kr"]}에 열리는 {s["sport_label"]} 대회 {s["total"]}곳',
    ]
    title = rng.choice(title_options)

    intro_options = [
        f'{s["sport_label"]}은 계절이 바뀔 때마다 대회 일정도 함께 바뀝니다. calrank에 등록된 실제 데이터를 기준으로, {s["month_kr"]} 한 달간 열리는 {s["sport_label"]} 대회를 지역별·거리별로 정리했습니다.',
        f'calrank가 보유한 실제 대회 데이터를 바탕으로, {s["month_kr"]} {s["sport_label"]} 대회 현황을 살펴봤습니다. 어디서, 어떤 거리로 대회가 열리는지 한눈에 확인해보세요.',
        f'{s["month_kr"]}에 {s["sport_label"]} 대회를 찾고 계신다면 참고하세요. calrank 데이터를 기준으로 이번 달 대회를 지역별·거리별로 직접 집계했습니다.',
    ]
    intro = rng.choice(intro_options)

    sec1_heading = rng.choice(["이번 달 대회 현황", f'{s["month_kr"]} {s["sport_label"]} 대회 규모', "총 몇 개나 열릴까"])
    sec1_body_options = [
        f'{s["month_kr"]} 한 달간 calrank에 등록된 {s["sport_label"]} 대회는 총 {s["total"]}개입니다.',
        f'이번 달 {s["sport_label"]} 대회는 전국에서 {s["total"]}개가 확인됩니다.',
        f'calrank 데이터 기준으로 {s["month_kr"]}에 {s["total"]}개의 {s["sport_label"]} 대회가 등록되어 있습니다.',
    ]
    sec1_body = rng.choice(sec1_body_options)
    if sample_lines:
        sec1_body += f' 대표적으로 {sample_lines} 등의 대회를 확인할 수 있습니다.'

    sec2_heading = rng.choice(["어느 지역에서 가장 많이 열릴까", "지역별 분포", f'{s["sport_label"]} 대회, 어디서 많이 열리나'])
    sec2_body_options = [
        f'지역별로 나눠보면 {top_region_name}이 {top_region_count}개로 가장 많고, 그 뒤를 {region_lines} 순으로 이어집니다.',
        f'{region_lines} 순으로 대회가 분포되어 있으며, 그중 {top_region_name} 지역이 {top_region_count}개로 가장 활발합니다.',
        f'전국 각지에서 열리지만, 특히 {top_region_name}({top_region_count}개) 지역에 대회가 몰려있는 경향을 보입니다.',
    ]
    sec2_body = rng.choice(sec2_body_options)

    sections = [
        {"heading": sec1_heading, "body": sec1_body},
        {"heading": sec2_heading, "body": sec2_body},
    ]

    if distance_lines:
        sec3_heading = rng.choice(["거리별로는 어떨까", "코스 거리 분포", "어떤 거리의 대회가 많을까"])
        sec3_body_options = [
            f'참가 거리 기준으로는 {distance_lines} 순으로 대회가 많습니다. 본인 체력 수준에 맞는 거리를 골라보세요.',
            f'거리별 분포는 {distance_lines} 순입니다. 처음이라면 짧은 거리부터 도전해보는 것을 추천합니다.',
        ]
        sections.append({"heading": sec3_heading, "body": rng.choice(sec3_body_options)})

    cta_options = [
        f'지금 바로 {s["month_kr"]} {s["sport_label"]} 대회를 지역·거리별로 필터링해서 찾아보세요.',
        f'{s["sport_label"]} 대회 접수 마감일까지 calrank에서 한눈에 확인하세요.',
    ]
    cta_text = rng.choice(cta_options)

    return {"title": title, "intro": intro, "sections": sections, "cta_text": cta_text}


def build_tags(stats):
    sport = stats["sport"]
    tags = [
        (f"index.html?sport={sport}", f"#{stats['sport_label']}"),
        (f"index.html?sport={sport}", "#" + stats["month_label"].replace("-", "월") + "대회"),
        ("column.html", "#대회분석"),
        ("column.html", "#러닝트렌드"),
        ("myrank.html", "#러닝기록관리"),
    ]
    for r, _ in stats["top_regions"][:4]:
        if r and r not in ("미표기", "전국"):
            tags.append((f"index.html?region={r}", f"#{r}{stats['sport_label']}"))
    seen = set()
    uniq = []
    for href, label in tags:
        if label in seen:
            continue
        seen.add(label)
        uniq.append((href, label))
    return uniq[:12]


def build_html(stats, content, slug):
    tags_html = "\n".join(
        f'<a href="{href}" class="column-tag">{label}</a>' for href, label in build_tags(stats)
    )
    sections_html = "\n".join(
        f'<h2>{sec["heading"]}</h2>\n<p>{sec["body"]}</p>' for sec in content["sections"]
    )
    region_boxes = "".join(
        f'<div class="stat-box"><b>{r}</b><span>{c}개</span></div>' for r, c in stats["top_regions"][:3]
    )
    stat_boxes = f'<div class="stat-grid"><div class="stat-box"><b>{stats["total"]}개</b><span>{stats["month_label"]} {stats["sport_label"]} 대회</span></div>{region_boxes}</div>'

    title = content["title"]
    desc = content["intro"][:120]
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — calrank</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
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
  .column-wrap {{ max-width: 720px; margin: 0 auto; padding: 48px 20px 80px; }}
  .column-meta {{ font-size: 13px; color: var(--ink-faint, #6A6A6A); margin-bottom: 12px; }}
  .column-title {{ font-family: var(--font-display); font-size: clamp(26px, 4vw, 38px); line-height: 1.3; margin-bottom: 24px; }}
  .column-body {{ font-size: 16px; line-height: 1.9; color: #E8E4E1; }}
  .column-body h2 {{ font-size: 21px; margin: 40px 0 14px; color: #fff; }}
  .column-body p {{ margin-bottom: 18px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin: 24px 0 32px; }}
  .stat-box {{ background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 8px; padding: 16px; text-align: center; }}
  .stat-box b {{ display: block; font-size: 22px; color: var(--accent); font-family: var(--font-display); margin-bottom: 4px; }}
  .stat-box span {{ font-size: 12px; color: var(--ink-faint, #6A6A6A); }}
  .column-cta {{ margin-top: 40px; padding: 24px; background: var(--surface, #141414); border-radius: 10px; text-align: center; }}
  .column-cta a {{ display: inline-block; margin-top: 12px; background: var(--accent); color: #fff; font-weight: 700; padding: 12px 28px; border-radius: 6px; text-decoration: none; }}
  .column-tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0 8px; }}
  .column-tag {{ font-size: 12px; padding: 5px 12px; border: 1px solid var(--border, #2A2A2A); border-radius: 999px; color: #B8B0AC; text-decoration: none; }}
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
<a href="column.html" class="nav-link active">칼럼</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>
<main class="column-wrap">
<p class="column-meta">📊 데이터 분석 · {stats["month_label"]}</p>
<h1 class="column-title">{title}</h1>
<div class="column-tags">
{tags_html}
</div>
<div class="column-body">
<p>{content["intro"]}</p>
{stat_boxes}
{sections_html}
<div class="column-cta">
<p>{content["cta_text"]}</p>
<a href="index.html?sport={stats["sport"]}">{stats["sport_label"]} 대회 전체 보기 →</a>
</div>
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
''', title, desc


def update_column_list(title, desc, slug, month_label):
    path = ROOT / "column.html"
    html = path.read_text(encoding="utf-8")
    card = (
        f'<a href="{slug}" class="column-card">\n'
        f'<p class="column-card-meta">📊 데이터 분석 · {month_label}</p>\n'
        f'<p class="column-card-title">{title}</p>\n'
        f'<p class="column-card-desc">{desc}</p>\n'
        f'</a>\n\n'
    )
    marker = '<div style="margin-top:32px;">\n\n'
    if marker in html:
        html = html.replace(marker, marker + card)
        path.write_text(html, encoding="utf-8")


def update_sitemap(slug):
    path = ROOT / "sitemap.xml"
    xml = path.read_text(encoding="utf-8")
    entry = (
        f"  <url>\n"
        f"    <loc>https://calrank.vercel.app/{slug}</loc>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.6</priority>\n"
        f"  </url>\n"
    )
    marker = "</urlset>"
    if marker in xml and entry not in xml:
        xml = xml.replace(marker, entry + marker)
        path.write_text(xml, encoding="utf-8")


def main():
    events = load_json("events.json", [])
    state = load_json("scripts/column_state.json", {"last_sport_index": -1, "published": []})

    idx, sport, month_label, topic_key, stats = pick_topic(events, state)
    if stats is None:
        print("No suitable topic found (insufficient data or all covered).")
        return

    rng = random.Random(topic_key)
    content = build_content(stats, rng)
    slug = slugify(sport, month_label)
    html, title, desc = build_html(stats, content, slug)

    (ROOT / slug).write_text(html, encoding="utf-8")
    update_column_list(title, desc, slug, month_label)
    update_sitemap(slug)

    state["last_sport_index"] = idx
    state.setdefault("published", []).append(topic_key)
    save_json("scripts/column_state.json", state)

    print(f"Generated: {slug}")


if __name__ == "__main__":
    main()

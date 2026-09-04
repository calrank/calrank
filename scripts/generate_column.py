"""
calrank 칼럼 자동 생성 스크립트

events.json에서 실제 대회 통계를 계산한 뒤, Claude API에게 "이 숫자만 사용해서"
자연스러운 칼럼 본문을 쓰도록 요청합니다. 할루시네이션 방지를 위해 프롬프트에서
제공된 통계 외의 사실(대회명, 수치)을 지어내지 말라고 명시적으로 지시합니다.

사용 예시:
  python scripts/generate_column.py
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

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

    return {
        "sport": sport,
        "sport_label": SPORT_LABEL[sport],
        "month_label": month_label,
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


def call_claude(stats):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    region_lines = ", ".join(f"{r}({c}개)" for r, c in stats["top_regions"])
    distance_lines = ", ".join(f"{d}({c}개)" for d, c in stats["top_distances"])
    sample_lines = ", ".join(stats["sample_names"])

    system_prompt = (
        "당신은 calrank(국내 동호인 스포츠 대회 캘린더 서비스)의 데이터 분석 칼럼니스트입니다. "
        "반드시 아래 제공된 통계 숫자와 대회명만 사용하세요. 제공되지 않은 수치, 지역, 대회명, "
        "일화를 절대 지어내지 마세요. 한국어로, 친근하지만 정보 전달 위주로 담백하게 쓰세요. "
        "반드시 아래 JSON 스키마로만 응답하세요(다른 텍스트 없이): "
        '{"title": "...", "intro": "...", "sections": [{"heading": "...", "body": "..."}], "cta_text": "..."}'
    )

    user_prompt = (
        f"종목: {stats['sport_label']}\n"
        f"대상 월: {stats['month_label']}\n"
        f"이번달 총 대회 수: {stats['total']}개\n"
        f"지역별 분포: {region_lines}\n"
        f"거리별 분포: {distance_lines}\n"
        f"실제 대회명 샘플: {sample_lines}\n\n"
        "위 데이터만 사용해서, 3~4개 섹션(h2 소제목 + 2~3문장 본문)으로 구성된 칼럼을 써주세요. "
        "intro는 1~2문장의 도입부, cta_text는 '지금 바로 OO 대회를 찾아보세요' 톤의 한 문장입니다."
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 1500,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


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


def build_html(stats, ai, slug):
    tags_html = "\n".join(
        f'<a href="{href}" class="column-tag">{label}</a>' for href, label in build_tags(stats)
    )
    sections_html = "\n".join(
        f'<h2>{s["heading"]}</h2>\n<p>{s["body"]}</p>' for s in ai["sections"]
    )
    stat_boxes = f'''
<div class="stat-grid">
<div class="stat-box"><b>{stats["total"]}개</b><span>{stats["month_label"]} {stats["sport_label"]} 대회</span></div>
{"".join(f'<div class="stat-box"><b>{r}</b><span>{c}개</span></div>' for r, c in stats["top_regions"][:3])}
</div>
'''
    title = ai["title"]
    desc = ai["intro"][:120]
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
<p>{ai["intro"]}</p>
{stat_boxes}
{sections_html}
<div class="column-cta">
<p>{ai["cta_text"]}</p>
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

    ai = call_claude(stats)
    slug = slugify(sport, month_label)
    html, title, desc = build_html(stats, ai, slug)

    (ROOT / slug).write_text(html, encoding="utf-8")
    update_column_list(title, desc, slug, month_label)
    update_sitemap(slug)

    state["last_sport_index"] = idx
    state.setdefault("published", []).append(topic_key)
    save_json("scripts/column_state.json", state)

    print(f"Generated: {slug}")


if __name__ == "__main__":
    main()

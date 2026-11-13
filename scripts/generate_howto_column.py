"""
calrank 종목별 노하우 칼럼 자동 생성 스크립트

scripts/tips_bank.json에 미리 조사·집필해둔 "고민 기반" 노하우 콘텐츠
(마라톤·트레일·자전거·철인3종, 실제 출처와 신뢰도 라벨 포함)에서
아직 발행하지 않은 (종목, 고민) 조합을 하나씩 순서대로 뽑아 칼럼으로
발행한다. AI 실시간 생성이 아니라 사전 집필 콘텐츠 뱅크를 로테이션하는
방식이라 별도 API 비용 없이 계속 새 글을 자동 발행할 수 있다.

모든 조합이 소진되면 처음부터 다시 순환하되, 이땐 "최신 정보로
업데이트했습니다" 안내와 함께 갱신일자만 새로 붙여 재발행한다(콘텐츠
신선도 유지).

사용 예시:
  python scripts/generate_howto_column.py
"""
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))

CONFIDENCE_STYLE = {
    "의학·전문가 확인": "conf-medical",
    "공식 자료": "conf-official",
    "언론 보도": "conf-press",
    "커뮤니티 경험담": "conf-community",
    "calrank 계산": "conf-press",
}


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    p = ROOT / path
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(sport, concern_id):
    return f"column-howto-{sport}-{concern_id}.html"


# 칼럼 끝에서 이어 보낼 페이지. (종목, concern id) 로 찾는다.
# 러닝화 편은 "뭘 사야 하나"로 끝나는데 살 데를 안 알려 주면 거기서 끊겼다.
NEXT_STOP = {
    ("marathon", "shoe-selection"): [
        ("gear-carbon-plate.html", "카본화는 기록을 얼마나 줄일까 — 속도별 근거 등급"),
        ("gear-wa-stack-height.html", "러닝화 밑창 두께 규정 — 대회에서 쓸 수 있는 신발인지"),
        ("gear-prices.html", "러닝화 어디서 사나")],
    ("trail", "beginner-gear"): [
        ("gear-utmb-kit.html", "UTMB 필수 장비 목록과 규정"),
        ("gear-utmb-jacket.html", "방수 재킷 규정 — 무엇을 기준으로 보나"),
        ("gear-trail-pack-weight.html", "배낭 무게가 기록에 주는 영향")],
    ("trail", "poles-technique"): [
        ("gear-trail-poles.html", "트레일 폴 효과와 근거 등급"),
        ("gear-trail-poles-by-gradient.html", "경사도별 트레일 폴 효과")],
    ("cycling", "granfondo-prep"): [
        ("gear-tyre-rolling.html", "타이어와 구름저항"),
        ("gear-aero-wheel.html", "에어로 휠 효과와 근거 등급")],
    ("triathlon", "open-water-fear"): [
        ("gear-wetsuit-by-temp.html", "수온별 웻슈트 착용 기준"),
        ("gear-wt-wetsuit-thickness.html", "웻슈트 두께 규정")],
}


def next_stop_html(sport, concern_id):
    hit = NEXT_STOP.get((sport, concern_id))
    if not hit:
        return ""
    items = "".join(f'<li><a href="{h}">{l}</a></li>' for h, l in hit)
    return ('<div class="column-next"><h2>장비가 궁금하다면</h2>'
            '<p>칼랭크 기어 판정은 규정을 연맹 문서에서, 효과를 논문에서 가져와 따로 정리합니다.</p>'
            f'<ul>{items}</ul></div>')


def live_extra(sport, concern):
    """검증을 마친 주제에는 그 시점의 대회 자료로 계산한 표를 붙인다(글을 다시 구울 때마다 갱신)."""
    if concern["id"] != "weather-heat":
        return ""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import generate_column as gc
        import generate_event_pages as gep
        events = load_json("events.json", [])
        gep.attach_climate(events)
        today = datetime.now(KST).date()
        end = today + timedelta(days=45)
        subset = [e for e in events if e.get("sport") == "marathon" and e.get("date")
                  and today.isoformat() <= e["date"][:10] <= end.isoformat()]
        st = {"sport": "marathon", "events": sorted(subset, key=lambda e: e["date"])}
        h = gc.climate_html(st)
        if not h:
            return ""
        return h.replace("<h2>대회 당일 기온과 기록 보정</h2>",
                         f'<h2>앞으로 45일, 마라톤 대회의 평년 기온 ({today.strftime("%m.%d")} 기준)</h2>', 1)
    except Exception:
        return ""


def update_sitemap(slug):
    path = ROOT / "sitemap.xml"
    xml = path.read_text(encoding="utf-8")
    if f"<loc>https://calrank.vercel.app/{slug}</loc>" in xml:
        return
    entry = (f"  <url>\n    <loc>https://calrank.vercel.app/{slug}</loc>\n"
             f"    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>\n")
    path.write_text(xml.replace("</urlset>", entry + "</urlset>"), encoding="utf-8")


def build_page(sport_label, sport, concern, cycle_count):
    title = f"{concern['title']} — {sport_label} 노하우"
    desc = (f"{concern['title']} {sport_label}에서 알려진 방법을 출처와 함께 정리했습니다. "
            "전문가 확인, 공식 자료, 언론 보도를 나눠 표시했습니다.")[:155]
    today = datetime.now(KST).strftime("%Y.%m.%d")

    tip_rows = "\n".join(
        f'''<div class="howto-tip">
      <p class="howto-tip-text">{t["text"]}</p>
      <p class="howto-tip-source"><span class="conf-badge {CONFIDENCE_STYLE.get(t["confidence"], "")}">{t["confidence"]}</span> 출처: {t["source"]}</p>
    </div>'''
        for t in concern["tips"]
    )

    refresh_note = (
        f'<p class="howto-refresh-note">📅 {today} 최신 정보로 다시 확인했습니다.</p>'
        if cycle_count > 0 else ""
    )

    slug = slugify(sport, concern["id"])
    robots = "" if concern.get("verified") else '<meta name="robots" content="noindex,follow">\n'
    extra_html = live_extra(sport, concern)
    next_stop = next_stop_html(sport, concern["id"])
    canonical_url = f"https://calrank.vercel.app/{slug}"
    date_iso = datetime.now(KST).strftime("%Y-%m-%d")
    article_ld = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "description": desc, "datePublished": date_iso,
        "author": {"@type": "Organization", "name": "calrank"},
        "publisher": {"@type": "Organization", "name": "calrank"},
        "mainEntityOfPage": canonical_url,
    }, ensure_ascii=False)
    breadcrumb_ld = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "calrank", "item": "https://calrank.vercel.app/index.html"},
            {"@type": "ListItem", "position": 2, "name": "칼럼", "item": "https://calrank.vercel.app/column.html"},
            {"@type": "ListItem", "position": 3, "name": title},
        ],
    }, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{robots}<title>{title} — calrank</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
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
<script type="application/ld+json">{article_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
<style>
  .column-wrap {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
  .column-meta {{ font-size: 14.5px; color: var(--ink-faint, #8E8E8E); margin-bottom: 12px; }}
  .column-title {{ font-family: var(--font-display); font-size: clamp(22px, 3.6vw, 32px); line-height: 1.35; margin-bottom: 20px; }}
  .howto-refresh-note {{ font-size: 13.5px; color: var(--accent); margin-bottom: 20px; }}
  .howto-tip {{ background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 10px; padding: 16px 18px; margin-bottom: 12px; }}
  .howto-tip-text {{ font-size: 15px; line-height: 1.8; color: var(--ink); margin-bottom: 10px; }}
  .howto-tip-source {{ font-size: 13.5px; color: var(--ink-faint, #8E8E8E); }}
  .conf-badge {{ display:inline-block; font-size:13.5px; padding:2px 8px; border-radius:999px; margin-right:6px; font-weight:700; }}
  .conf-medical {{ background:#E3EEF9; color:#154C79; }}
  .conf-official {{ background:#EDE6F7; color:#4B2E83; }}
  .conf-press {{ background:#ECE8E3; color:#4A4542; }}
  .conf-community {{ background:#FBEBD5; color:#7A4A00; }}
  .cv-table {{ width: 100%; border-collapse: collapse; }}
  .cv-table th, .cv-table td {{ padding: 8px 6px; border-top: 1px solid var(--line); text-align: left; font-weight: 400; }}
  .cv-table th {{ color: var(--ink-soft); }}
  .source-legend {{ font-size:13.5px; color:var(--ink-faint,#8E8E8E); margin:16px 0 28px; line-height:1.8; }}
  .column-cta {{ margin-top: 32px; padding: 22px; background: var(--surface, #141414); border-radius: 10px; text-align: center; }}
  .column-cta a {{ display: inline-block; margin-top: 10px; background: var(--accent-fill); color: var(--on-accent); font-weight: 700; padding: 12px 26px; border-radius: 6px; text-decoration: none; }}
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
<a href="column.html" class="nav-link active">칼럼</a>
<a href="myrank.html" class="nav-link">내 랭크</a>
<a href="contact.html" class="nav-contact-link">제휴문의</a>
</nav>
</div>
</header>

<main class="column-wrap">
<p class="column-meta">🎯 노하우 · {sport_label}</p>
<h1 class="column-title">{concern["title"]}</h1>
{refresh_note}
<p class="source-legend">
🔵 의학·전문가 확인 = 의사·물리치료사 등 전문가 코멘트나 임상 연구 · 🟣 공식 자료 = 협회·브랜드 공식 가이드 · ⚪ 언론 보도 = 뉴스·매체 기사 · 🟠 커뮤니티 경험담 = 동호인·블로거의 실제 경험 기반 조언(참고용)
</p>

{tip_rows}
{extra_html}

{next_stop}

<div class="column-cta">
<p>다음 대회를 고르는 중이라면, 캘린더에서 {sport_label} 대회를 지역과 거리별로 볼 수 있습니다.</p>
<a href="index.html?sport={sport}">{sport_label} 대회 캘린더 보기 →</a>
</div>
</main>

<footer class="site-footer">
<div class="wrap">
<p>이 글은 공개된 의학·공식·언론 자료를 종합 정리한 것으로, 개인의 건강 상태에 대한 진단이나 처방을 대신하지 않습니다. 통증이 지속되면 전문가의 진료를 받으세요.</p>
</div>
</footer>

</body>
</html>
'''


def update_column_list(title, desc, slug, sport_label):
    path = ROOT / "column.html"
    html = path.read_text(encoding="utf-8")
    card = f'''<a href="{slug}" class="column-card">
<p class="column-card-meta">🎯 노하우 · {sport_label}</p>
<p class="column-card-title">{title}</p>
<p class="column-card-desc">{desc}</p>
</a>

'''
    marker = '<div style="margin-top:24px;" id="columnCardsContainer">\n\n'
    if marker in html:
        html = html.replace(marker, marker + card)
        path.write_text(html, encoding="utf-8")


def update_sitemap(slug):
    path = ROOT / "sitemap.xml"
    xml = path.read_text(encoding="utf-8")
    marker = "</urlset>"
    entry = (
        f"  <url>\n"
        f"    <loc>https://calrank.vercel.app/{slug}</loc>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.6</priority>\n"
        f"  </url>\n"
    )
    if f"<loc>https://calrank.vercel.app/{slug}</loc>" not in xml and marker in xml:
        xml = xml.replace(marker, entry + marker)
        path.write_text(xml, encoding="utf-8")


def regenerate_published():
    """템플릿(head 구조)이 바뀐 뒤, 이미 발행된 모든 칼럼을 최신 템플릿으로
    다시 굽는다. 새 글을 발행하는 게 아니라 기존 slug의 파일 내용만
    갱신하므로 published 목록·sitemap·column.html 카드에는 손대지 않는다."""
    bank = load_json("scripts/tips_bank.json", {})
    state = load_json("scripts/howto_state.json", {"published": [], "cycle": 0})

    count = 0
    for entry in state["published"]:
        sport, concern_id = entry.split(":", 1)
        if sport not in bank:
            continue
        concern = next((c for c in bank[sport]["concerns"] if c["id"] == concern_id), None)
        if not concern or concern.get("retired"):
            continue
        sport_label = bank[sport]["label"]
        html = build_page(sport_label, sport, concern, state["cycle"])
        slug = slugify(sport, concern_id)
        (ROOT / slug).write_text(html, encoding="utf-8")
        count += 1
        print(f"Regenerated: {slug}")
    print(f"[regenerate] {count}/{len(state['published'])}개 칼럼을 최신 템플릿으로 다시 구웠습니다.")


def main():
    if "--regenerate-published" in sys.argv:
        regenerate_published()
        return

    bank = load_json("scripts/tips_bank.json", {})
    state = load_json("scripts/howto_state.json", {"published": [], "cycle": 0})

    # (종목, 고민) 조합을 전부 나열해 순서대로 순환한다.
    all_combos = []
    for sport, v in bank.items():
        for concern in v["concerns"]:
            # retired 항목은 새 가이드(guide-*.html)로 통합되어 리다이렉트된 주제다.
            # 다시 발행하면 같은 검색어를 두고 우리 글끼리 경쟁하게 되므로 건너뛴다.
            # 왜 내렸는지는 tips_bank.json 의 retired_to / retired_why 에 적어 두었다.
            if concern.get("retired"):
                continue
            # 근거를 원 논문·공식 문서까지 확인한 주제(verified)만 발행한다.
            # 나머지는 출처가 블로그·인터뷰 기사에 머물러 있어 확인이 끝날 때까지 보류.
            if not concern.get("verified"):
                continue
            all_combos.append((sport, concern["id"]))

    remaining = [c for c in all_combos if f"{c[0]}:{c[1]}" not in state["published"]]
    if not remaining:
        # 새로 낼 주제가 없으면 발행된 검증 글을 다시 굽는다(그 시점 대회 기온 표가 바뀐다).
        for sport, concern_id in all_combos:
            concern = next(c for c in bank[sport]["concerns"] if c["id"] == concern_id)
            slug = slugify(sport, concern_id)
            (ROOT / slug).write_text(build_page(bank[sport]["label"], sport, concern, state["cycle"]), encoding="utf-8")
            update_sitemap(slug)
            print(f"Refreshed: {slug}")
        return

    sport, concern_id = remaining[0]
    concern = next(c for c in bank[sport]["concerns"] if c["id"] == concern_id)
    sport_label = bank[sport]["label"]

    html = build_page(sport_label, sport, concern, state["cycle"])
    slug = slugify(sport, concern_id)
    (ROOT / slug).write_text(html, encoding="utf-8")

    update_column_list(concern["title"] + f" — {sport_label} 노하우", f"{concern['title']} {sport_label}에서 알려진 방법을 출처와 함께 정리했습니다.", slug, sport_label)
    update_sitemap(slug)

    state["published"].append(f"{sport}:{concern_id}")
    save_json("scripts/howto_state.json", state)

    print(f"Published howto column: {slug} (cycle {state['cycle']})")


if __name__ == "__main__":
    main()

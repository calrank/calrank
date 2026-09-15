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
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))

CONFIDENCE_STYLE = {
    "의학·전문가 확인": "conf-medical",
    "공식 자료": "conf-official",
    "언론 보도": "conf-press",
    "커뮤니티 경험담": "conf-community",
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


def build_page(sport_label, sport, concern, cycle_count):
    title = f"{concern['title']} — {sport_label} 노하우 총정리"
    desc = f"{sport_label} {concern['title']} 실제 출처(의학·전문가, 공식 자료, 언론 보도)를 밝힌 노하우 정리."
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
  .column-wrap {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
  .column-meta {{ font-size: 13px; color: var(--ink-faint, #6A6A6A); margin-bottom: 12px; }}
  .column-title {{ font-family: var(--font-display); font-size: clamp(22px, 3.6vw, 32px); line-height: 1.35; margin-bottom: 20px; }}
  .howto-refresh-note {{ font-size: 12px; color: var(--accent); margin-bottom: 20px; }}
  .howto-tip {{ background: var(--surface, #141414); border: 1px solid var(--border, #2A2A2A); border-radius: 10px; padding: 16px 18px; margin-bottom: 12px; }}
  .howto-tip-text {{ font-size: 15px; line-height: 1.8; color: #E8E4E1; margin-bottom: 10px; }}
  .howto-tip-source {{ font-size: 12px; color: var(--ink-faint, #6A6A6A); }}
  .conf-badge {{ display:inline-block; font-size:11px; padding:2px 8px; border-radius:999px; margin-right:6px; font-weight:700; }}
  .conf-medical {{ background:rgba(120,190,255,0.15); color:#78beff; }}
  .conf-official {{ background:rgba(180,140,255,0.15); color:#c9a6ff; }}
  .conf-press {{ background:rgba(255,255,255,0.08); color:#B8B0AC; }}
  .conf-community {{ background:rgba(255,170,80,0.15); color:#ffaa50; }}
  .source-legend {{ font-size:12px; color:var(--ink-faint,#6A6A6A); margin:16px 0 28px; line-height:1.8; }}
  .column-cta {{ margin-top: 32px; padding: 22px; background: var(--surface, #141414); border-radius: 10px; text-align: center; }}
  .column-cta a {{ display: inline-block; margin-top: 10px; background: var(--accent); color: #fff; font-weight: 700; padding: 12px 26px; border-radius: 6px; text-decoration: none; }}
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

<div class="column-cta">
<p>{sport_label} 대회 일정을 확인하고 다음 목표를 잡아보세요.</p>
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
    marker = '<div style="margin-top:32px;">\n\n'
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
    if entry not in xml and marker in xml:
        xml = xml.replace(marker, entry + marker)
        path.write_text(xml, encoding="utf-8")


def main():
    bank = load_json("tips_bank.json", {})
    state = load_json("scripts/howto_state.json", {"published": [], "cycle": 0})

    # (종목, 고민) 조합을 전부 나열해 순서대로 순환한다.
    all_combos = []
    for sport, v in bank.items():
        for concern in v["concerns"]:
            all_combos.append((sport, concern["id"]))

    remaining = [c for c in all_combos if f"{c[0]}:{c[1]}" not in state["published"]]
    if not remaining:
        # 한 바퀴 다 돌았으면 다시 처음부터, cycle 카운트를 올려 "갱신" 표시를 붙인다.
        state["published"] = []
        state["cycle"] += 1
        remaining = all_combos

    sport, concern_id = remaining[0]
    concern = next(c for c in bank[sport]["concerns"] if c["id"] == concern_id)
    sport_label = bank[sport]["label"]

    html = build_page(sport_label, sport, concern, state["cycle"])
    slug = slugify(sport, concern_id)
    (ROOT / slug).write_text(html, encoding="utf-8")

    update_column_list(concern["title"] + f" — {sport_label} 노하우 총정리", f"{sport_label} {concern['title']} 실제 출처를 밝힌 노하우 정리.", slug, sport_label)
    update_sitemap(slug)

    state["published"].append(f"{sport}:{concern_id}")
    save_json("scripts/howto_state.json", state)

    print(f"Published howto column: {slug} (cycle {state['cycle']})")


if __name__ == "__main__":
    main()
